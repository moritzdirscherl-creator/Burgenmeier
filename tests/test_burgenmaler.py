import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "burgenmaler", "scripts"))

import paint  # noqa: E402

EXAMPLE = os.path.join(ROOT, "burgenmeier", "examples", "beispiel_castle.json")


def test_finds_burgenmeier():
    d = paint.find_burgenmeier()
    assert os.path.isfile(os.path.join(d, "castle_lib.py"))


def test_schaubild_html(tmp_path):
    out = tmp_path / "s.html"
    paint.main([EXAMPLE, "-o", str(out)])
    html = out.read_text(encoding="utf-8")
    assert "__SCENE_JSON__" not in html and "__THREE_SCRIPT__" not in html
    assert "three.js/r128/three.min.js" in html
    data = json.loads(re.search(r'<script id="scene" type="application/json">(.*?)</script>', html, re.S).group(1))
    parts = [p for o in data["objects"] for p in o["parts"]]
    assert {"stone", "slate", "tile"} <= {p["m"] for p in parts}
    assert all(p["r"] != "roof" or p["m"] for p in parts if p["c"].startswith("#"))
    vec = data["vec"]
    assert vec["env"]["roads"] and vec["env"]["fields"] and vec["plateau"]
    assert vec["ditches"][0]["width"] > 0


def test_three_inline(tmp_path):
    fake = tmp_path / "three.min.js"
    fake.write_text("var THREE={};", encoding="utf-8")
    out = tmp_path / "s.html"
    paint.main([EXAMPLE, "-o", str(out), "--three", str(fake)])
    html = out.read_text(encoding="utf-8")
    assert "var THREE={};" in html and "cdnjs" not in html
