import copy
import json
import math
import os
import struct
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "burgenmeier")
sys.path.insert(0, os.path.join(SKILL, "scripts"))

import build_model  # noqa: E402
import castle_lib as cl  # noqa: E402
import draw_view  # noqa: E402
import geo  # noqa: E402
import plan  # noqa: E402
import report  # noqa: E402
import validate  # noqa: E402

EXAMPLE = os.path.join(SKILL, "examples", "beispiel_castle.json")


@pytest.fixture(scope="module")
def castle():
    return cl.load_castle(EXAMPLE)


@pytest.fixture(scope="module")
def scene(castle):
    return cl.build_scene(castle)


def test_example_validates(castle):
    errors, warnings = validate.validate(castle)
    assert errors == []
    assert warnings == []


def test_scene_contents(scene):
    ids = {o["id"] for o in scene["objects"]}
    assert {"ringmauer", "bergfried", "palas", "torhaus", "bruecke"} <= ids
    assert scene["trees"], "Wald sollte Bäume erzeugen"
    t = scene["terrain"]
    assert len(t["heights"]) == t["res"] + 1
    assert all(math.isfinite(v) for row in t["heights"] for v in row)
    assert abs(cl.Terrain(t["extent"], t["res"]).extent - t["extent"]) < 1e-9


def test_scene_is_deterministic(castle):
    a = json.dumps(cl.build_scene(castle), sort_keys=True)
    b = json.dumps(cl.build_scene(castle), sort_keys=True)
    assert a == b


def test_buildings_stand_on_terrain(castle):
    """Fundamente reichen unter das Gelände, nichts schwebt."""
    T = cl.build_terrain(castle)
    sc = cl.build_scene(castle)
    for o in sc["objects"]:
        if o["type"] not in ("tower", "building", "gate"):
            continue
        V = [v for p in o["parts"] for v in p["vertices"]]
        zmin = min(v[2] for v in V)
        cx = sum(v[0] for v in V) / len(V)
        cy = sum(v[1] for v in V) / len(V)
        assert zmin < T.sample(cx, cy), o["id"]


def test_low_poly_budget(scene):
    n = sum(len(cl.part_triangles(p)) for o in scene["objects"] if o["layer"] == "burg" for p in o["parts"])
    assert 200 < n < 20000


@pytest.mark.parametrize("ttype", ["spur", "hilltop", "crag", "slope", "lowland", "island"])
def test_terrain_types(castle, ttype):
    c = copy.deepcopy(castle)
    c["site"]["terrain"]["type"] = ttype
    sc = cl.build_scene(c)
    assert sc["objects"]


@pytest.mark.parametrize("roof", cl.ROOF_TYPES)
def test_roof_types(castle, roof):
    c = copy.deepcopy(castle)
    for el in c["elements"]:
        if el["type"] in ("tower", "building", "gate"):
            el["roof"] = roof
    errors, _ = validate.validate(c)
    assert errors == []


def test_triangulate_concave_area():
    poly = [(0, 0), (10, 0), (10, 10), (5, 4), (0, 10)]
    tris = cl.triangulate(poly)
    area = sum(abs(cl.poly_area([poly[a], poly[b], poly[c]])) for a, b, c in tris)
    assert len(tris) == 3
    assert area == pytest.approx(abs(cl.poly_area(poly)))


def test_face_winding_outward():
    part = cl.Part("#fff")
    cl.add_prism(part, cl.rect_poly((0, 0), [4, 2]), 0, 3)
    for f in part.f:
        n = cl.face_normal([part.v[i] for i in f])
        c = [sum(part.v[i][k] for i in f) / len(f) for k in range(3)]
        out = (c[0] * n[0] + c[1] * n[1] + (c[2] - 1.5) * n[2])
        assert out > 0


def test_glb_structure(scene, tmp_path):
    p = tmp_path / "b.glb"
    build_model.write_glb(scene, str(p))
    data = p.read_bytes()
    magic, version, total = struct.unpack("<III", data[:12])
    assert magic == 0x46546C67 and version == 2 and total == len(data)
    jlen, jtype = struct.unpack("<II", data[12:20])
    assert jtype == 0x4E4F534A
    gltf = json.loads(data[20:20 + jlen])
    blen, btype = struct.unpack("<II", data[20 + jlen:28 + jlen])
    assert btype == 0x004E4942 and blen == gltf["buffers"][0]["byteLength"]
    for bv in gltf["bufferViews"]:
        assert bv["byteOffset"] + bv["byteLength"] <= blen
        assert bv["byteOffset"] % 4 == 0
    names = [n["name"] for n in gltf["nodes"]]
    assert "Bergfried" in names and "Gelände" in names
    berg = gltf["nodes"][names.index("Bergfried")]
    assert berg["extras"]["confidence"] == "wahrscheinlich"


def test_obj_export(scene, tmp_path):
    p = tmp_path / "b.obj"
    build_model.write_obj(scene, str(p), include_env=False)
    txt = p.read_text(encoding="utf-8")
    assert txt.count("\nf ") > 100
    assert (tmp_path / "b.mtl").exists()


def test_viewer_html(scene, tmp_path):
    p = tmp_path / "v.html"
    build_model.write_viewer(scene, str(p))
    html = p.read_text(encoding="utf-8")
    assert "__SCENE_JSON__" not in html and "__TITLE__" not in html
    start = html.index('type="application/json">') + len('type="application/json">')
    data = json.loads(html[start:html.index("</script>", start)])
    assert data["objects"] and data["terrain"]["cells"]


@pytest.mark.parametrize("view", list(draw_view.VIEWS))
def test_drawing_views(scene, view):
    P = draw_view.build_drawing(scene, view)
    svg = draw_view.to_svg(P)
    assert svg.startswith("<svg") and svg.count("<polygon") > 100


@pytest.mark.parametrize("style", ["feder", "farbe", "befund"])
def test_png_output(scene, style, tmp_path):
    from PIL import Image
    P = draw_view.build_drawing(scene, "vogelschau", style, width=800, height=560)
    p = tmp_path / "x.png"
    draw_view.to_png(P, str(p), scale=1)
    im = Image.open(p)
    assert im.size == (800, 560)
    assert sum(1 for v in im.convert("L").histogram() if v) > 20  # nicht leer


def test_validate_catches_errors(castle):
    c = copy.deepcopy(castle)
    c["elements"].append({"id": "x", "type": "spaceship"})
    c["elements"][1]["evidence"]["sources"] = ["GIBTSNICHT"]
    c["elements"][2]["roof"] = "kuppel"
    errors, _ = validate.validate(c)
    text = " ".join(errors)
    assert "spaceship" in text and "GIBTSNICHT" in text and "kuppel" in text


def test_report(castle):
    md = report.report(castle)
    assert "| Bergfried |" in md and "## Quellen" in md


def test_geo_roundtrip():
    lat0, lon0 = 50.2, 7.3
    x, y = geo.to_local(lat0, lon0, 50.201, 7.302)
    lat, lon = geo.to_latlon(lat0, lon0, x, y)
    assert lat == pytest.approx(50.201, abs=1e-9) and lon == pytest.approx(7.302, abs=1e-9)
    assert y == pytest.approx(111.3, abs=0.5)


def test_plan_calibration_roundtrip():
    cal = {"scale": {"p1": [0, 0], "p2": [400, 0], "meters": 50}, "north_deg": 23, "origin_px": [500, 300]}
    assert plan.px_per_m(cal) == pytest.approx(8)
    for x, y in [(0, 0), (12.5, -7), (-40, 33)]:
        px, py = plan.m_to_px(cal, x, y)
        assert plan.px_to_m(cal, px, py) == pytest.approx((x, y))
    # Norden zeigt 23° im Uhrzeigersinn von Bild-oben: ein Punkt nach Norden liegt rechts oberhalb
    px, py = plan.m_to_px(cal, 0, 10)
    assert px > 500 and py < 300


def test_heightmap_terrain(castle, tmp_path):
    n = 33
    hm = {"extent": 900, "heights": [[100 + 0.1 * i + 0.05 * j for i in range(n)] for j in range(n)]}
    (tmp_path / "hm.json").write_text(json.dumps(hm))
    c = copy.deepcopy(castle)
    c["_base_dir"] = str(tmp_path)
    c["site"]["terrain"] = {"heightmap": "hm.json"}
    T = cl.build_terrain(c)
    assert T.sample(0, 0) == pytest.approx(0, abs=1e-6) or T.plateau_poly is not None
    assert T.sample(300, 0) > T.sample(-300, 0)
