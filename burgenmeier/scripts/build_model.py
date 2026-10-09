#!/usr/bin/env python3
"""castle.json -> Low-Poly-3D-Modell (GLB, OBJ) und interaktiver Viewer (HTML).

Beispiele:
  python build_model.py castle.json --glb burg.glb --html burg_3d.html
  python build_model.py castle.json --obj burg.obj --no-env

GLB/glTF ist y-oben (x = Ost, y = oben, -z = Nord). Jedes Bauteil ist ein eigener
Knoten mit Name und `extras` (Quellen, Konfidenz), sodass Blender & Co. die
Befundlage mit übernehmen.
"""

import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import castle_lib as cl  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "templates", "viewer.html")


def _to_gl(p):
    return (p[0], p[2], -p[1])


def _hex_rgba(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [round(v ** 2.2, 4) for v in c] + [1.0]  # sRGB -> linear


def _flat_arrays(tris):
    pos, nor = [], []
    for tri in tris:
        g = [_to_gl(p) for p in tri]
        n = cl.face_normal(g)
        for p in g:
            pos.extend(p)
            nor.extend(n)
    return pos, nor


def write_glb(scene, path, include_env=True):
    gltf = {"asset": {"version": "2.0", "generator": "Burgenmeier"},
            "scene": 0, "scenes": [{"name": scene["meta"]["name"], "nodes": []}],
            "nodes": [], "meshes": [], "materials": [], "accessors": [], "bufferViews": [], "buffers": []}
    blob = bytearray()
    mat_index = {}

    def material(color, alpha=1.0, vertex_colors=False):
        key = (color, alpha, vertex_colors)
        if key not in mat_index:
            rgba = _hex_rgba(color) if color else [1, 1, 1, 1]
            rgba[3] = alpha
            m = {"name": color or "vertexcolor",
                 "pbrMetallicRoughness": {"baseColorFactor": rgba, "metallicFactor": 0.0, "roughnessFactor": 0.95}}
            if alpha < 1:
                m["alphaMode"] = "BLEND"
            gltf["materials"].append(m)
            mat_index[key] = len(gltf["materials"]) - 1
        return mat_index[key]

    def add_accessor(values, ncomp, with_minmax=False):
        nonlocal blob
        while len(blob) % 4:
            blob.append(0)
        off = len(blob)
        blob += struct.pack(f"<{len(values)}f", *values)
        gltf["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(values) * 4, "target": 34962})
        acc = {"bufferView": len(gltf["bufferViews"]) - 1, "componentType": 5126,
               "count": len(values) // ncomp, "type": {3: "VEC3", 4: "VEC4"}[ncomp]}
        if with_minmax:
            acc["min"] = [min(values[i::ncomp]) for i in range(ncomp)]
            acc["max"] = [max(values[i::ncomp]) for i in range(ncomp)]
        gltf["accessors"].append(acc)
        return len(gltf["accessors"]) - 1

    def add_node(name, prims, extras=None):
        if not prims:
            return
        gltf["meshes"].append({"name": name, "primitives": prims})
        node = {"name": name, "mesh": len(gltf["meshes"]) - 1}
        if extras:
            node["extras"] = extras
        gltf["nodes"].append(node)
        gltf["scenes"][0]["nodes"].append(len(gltf["nodes"]) - 1)

    def prim(tris, color, alpha=1.0):
        pos, nor = _flat_arrays(tris)
        if not pos:
            return None
        return {"attributes": {"POSITION": add_accessor(pos, 3, True), "NORMAL": add_accessor(nor, 3)},
                "material": material(color, alpha)}

    # Gelände mit Zellfarben
    pos, nor, col = [], [], []
    for tri, c in cl.terrain_triangles(scene["terrain"]):
        g = [_to_gl(p) for p in tri]
        n = cl.face_normal(g)
        rgba = _hex_rgba(c)
        for p in g:
            pos.extend(p)
            nor.extend(n)
            col.extend(rgba)
    add_node("Gelände", [{"attributes": {"POSITION": add_accessor(pos, 3, True), "NORMAL": add_accessor(nor, 3),
                                         "COLOR_0": add_accessor(col, 4)},
                          "material": material(None, 1.0, True)}])

    for o in scene["objects"]:
        if o["layer"] != "burg" and not include_env:
            continue
        prims = []
        for part in o["parts"]:
            p = prim(cl.part_triangles(part), part["color"], 0.85 if part["role"] == "water" else 1.0)
            if p:
                prims.append(p)
        add_node(o["name"], prims, {"id": o["id"], "type": o["type"], "layer": o["layer"],
                                    "confidence": o["confidence"], "sources": o["sources"],
                                    "note": o.get("note", ""), "phase": o.get("phase", "")})
    if include_env and scene["trees"]:
        prims = [prim(cl.part_triangles(p.to_dict()), p.color) for p in cl.tree_parts(scene["trees"])]
        add_node("Bäume", [p for p in prims if p], {"layer": "umgebung", "confidence": "annahme"})

    while len(blob) % 4:
        blob.append(0)
    gltf["buffers"].append({"byteLength": len(blob)})
    js = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    while len(js) % 4:
        js += b" "
    total = 12 + 8 + len(js) + 8 + len(blob)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A))
        f.write(js)
        f.write(struct.pack("<II", len(blob), 0x004E4942))
        f.write(blob)
    return path


def write_obj(scene, path, include_env=True):
    base = os.path.splitext(path)[0]
    mtl_path = base + ".mtl"
    mats = {}
    lines = [f"# {scene['meta']['name']} – Burgenmeier", f"mtllib {os.path.basename(mtl_path)}", "s off"]
    vcount = 0

    def emit(name, tris, color):
        nonlocal vcount
        mats.setdefault(color, f"m_{color.lstrip('#')}")
        lines.append(f"o {name.replace(' ', '_')}")
        lines.append(f"usemtl {mats[color]}")
        for tri in tris:
            for p in tri:
                g = _to_gl(p)
                lines.append(f"v {g[0]:.2f} {g[1]:.2f} {g[2]:.2f}")
            lines.append(f"f {vcount + 1} {vcount + 2} {vcount + 3}")
            vcount += 3

    by_color = {}
    for tri, c in cl.terrain_triangles(scene["terrain"]):
        by_color.setdefault(c, []).append(tri)
    for c, tris in by_color.items():
        emit(f"Gelände_{c.lstrip('#')}", tris, c)
    for o in scene["objects"]:
        if o["layer"] != "burg" and not include_env:
            continue
        for k, part in enumerate(o["parts"]):
            emit(f"{o['name']}_{k}", cl.part_triangles(part), part["color"])
    if include_env:
        for p in cl.tree_parts(scene["trees"]):
            emit("Bäume", cl.part_triangles(p.to_dict()), p.color)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(mtl_path, "w", encoding="utf-8") as f:
        for c, name in mats.items():
            r, g, b = [int(c.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            f.write(f"newmtl {name}\nKd {r:.3f} {g:.3f} {b:.3f}\nKa 0 0 0\nKs 0 0 0\nd 1\nillum 1\n\n")
    return path


def viewer_payload(scene):
    """Kompakte Szene für den Browser-Viewer (Objekte bereits trianguliert)."""
    objs = []
    for o in scene["objects"]:
        parts = []
        for part in o["parts"]:
            V = part["vertices"]
            idx = []
            for f in part["faces"]:
                pts = [V[i] for i in f]
                for a, b, c in cl.triangulate_face(pts):
                    idx += [f[a], f[b], f[c]]
            parts.append({"c": part["color"], "r": part["role"],
                          "p": [round(x, 2) for v in V for x in v], "i": idx})
        objs.append({k: o[k] for k in ("id", "name", "type", "layer", "confidence", "sources", "note")}
                    | {"phase": o.get("phase", ""), "parts": parts})
    t = scene["terrain"]
    return {"meta": scene["meta"], "terrain": {"extent": t["extent"], "res": t["res"],
                                               "h": [round(v, 1) for row in t["heights"] for v in row],
                                               "palette": t["palette"], "names": t["palette_names"],
                                               "cells": [c for row in t["cells"] for c in row]},
            "objects": objs, "trees": scene["trees"], "treeColors": scene["tree_colors"],
            "confColors": scene["confidence_colors"], "bbox": scene["castle_bbox"]}


def write_viewer(scene, path, template=TEMPLATE):
    with open(template, encoding="utf-8") as f:
        html = f.read()
    data = json.dumps(viewer_payload(scene), ensure_ascii=False, separators=(",", ":"))
    data = data.replace("</", "<\\/")
    html = html.replace("__SCENE_JSON__", data).replace("__TITLE__", scene["meta"]["name"])
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("castle")
    ap.add_argument("--glb", help="GLB-Datei schreiben")
    ap.add_argument("--obj", help="OBJ-Datei (+ .mtl) schreiben")
    ap.add_argument("--html", help="interaktiven 3D-Viewer (HTML) schreiben")
    ap.add_argument("--scene-json", help="berechnete Szene als JSON ablegen (Debug)")
    ap.add_argument("--no-env", action="store_true", help="nur die Burg exportieren")
    a = ap.parse_args(argv)
    if not (a.glb or a.obj or a.html or a.scene_json):
        stem = os.path.splitext(a.castle)[0]
        a.glb, a.html = stem + ".glb", stem + "_3d.html"
    scene = cl.build_scene(cl.load_castle(a.castle))
    if a.glb:
        print("GLB:", write_glb(scene, a.glb, not a.no_env))
    if a.obj:
        print("OBJ:", write_obj(scene, a.obj, not a.no_env))
    if a.html:
        print("Viewer:", write_viewer(scene, a.html))
    if a.scene_json:
        with open(a.scene_json, "w", encoding="utf-8") as f:
            json.dump(scene, f, ensure_ascii=False)
        print("Szene:", a.scene_json)
    n_tris = sum(len(cl.part_triangles(p)) for o in scene["objects"] for p in o["parts"] if o["layer"] == "burg")
    print(f"Burg: {n_tris} Dreiecke · Objekte: {len(scene['objects'])} · Bäume: {len(scene['trees'])}")


if __name__ == "__main__":
    main()
