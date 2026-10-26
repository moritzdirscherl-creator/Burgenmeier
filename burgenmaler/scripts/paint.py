#!/usr/bin/env python3
"""castle.json (Burgenmeier) -> verschönertes Schaubild als interaktive HTML-Seite.

Beispiele:
  python paint.py castle.json -o burg_schaubild.html
  python paint.py castle.json -o burg_schaubild.html --three three.min.js   # offline, three.js eingebettet

Die Geometrie stammt unverändert aus dem Burgenmeister (castle_lib). Der Burgenmaler
ergänzt nur die Darstellung: Texturen, Licht, Himmel, Bewuchs. Der Schalter
„Befundlage“ bleibt erhalten, damit „schön“ nicht mit „belegt“ verwechselt wird.

Den Burgenmeister findet das Skript über --burgenmeier, die Umgebungsvariable
BURGENMEIER_DIR oder einen Nachbarordner `burgenmeier/` neben diesem Skill.
"""

import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "templates", "schaubild.html")
THREE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"


def find_burgenmeier(explicit=None):
    """Pfad zu burgenmeier/scripts (enthält castle_lib.py und build_model.py)."""
    candidates = [explicit, os.environ.get("BURGENMEIER_DIR")]
    candidates += [os.path.join(HERE, "..", "..", "burgenmeier")]
    for pattern in ("/mnt/skills/*/burgenmeier", os.path.expanduser("~/.claude/skills/burgenmeier"),
                    "/mnt/user-data/**/burgenmeier"):
        candidates += sorted(glob.glob(pattern, recursive=True))
    for c in candidates:
        if not c:
            continue
        for d in (c, os.path.join(c, "scripts")):
            if os.path.isfile(os.path.join(d, "castle_lib.py")) and os.path.isfile(os.path.join(d, "build_model.py")):
                return os.path.abspath(d)
    raise SystemExit("Burgenmeister nicht gefunden. Pfad mit --burgenmeier oder BURGENMEIER_DIR angeben "
                     "(Ordner mit castle_lib.py).")


def load_modules(path):
    if path not in sys.path:
        sys.path.insert(0, path)
    import build_model  # noqa: E402
    import castle_lib  # noqa: E402
    return castle_lib, build_model


def vector_data(castle):
    """Umgebung, Burghof und Gräben als Vektoren, damit der Boden scharf gemalt werden kann."""
    site = (castle or {}).get("site") or {}
    env = site.get("environment") or {}
    keep = ("fields", "forest", "settlements", "roads", "rivers", "water")
    ditches = [{"path": [p[:2] for p in el["path"]], "width": float(el.get("width", 12)),
                "closed": bool(el.get("closed")), "water": bool(el.get("water"))}
               for el in (castle or {}).get("elements", []) if el.get("type") == "ditch" and el.get("path")]
    plateau = (site.get("plateau") or {}).get("polygon")
    return {"env": {k: env[k] for k in keep if env.get(k)}, "plateau": plateau, "ditches": ditches}


def payload(scene, castle_lib, build_model, castle=None):
    """Viewer-Daten des Burgenmeisters plus Werkstoffnamen je Teil (für die Texturwahl)
    und die Vektordaten der Umgebung (für die Bodenkarte)."""
    data = build_model.viewer_payload(scene)
    by_color = {v.lower(): k for k, v in castle_lib.MATERIALS.items()}
    for obj in data["objects"]:
        for part in obj["parts"]:
            part["m"] = by_color.get(part["c"].lower())
    data["vec"] = vector_data(castle)
    return data


def write_schaubild(scene, path, castle_lib, build_model, three_js=None, template=TEMPLATE, castle=None):
    with open(template, encoding="utf-8") as f:
        html = f.read()
    data = json.dumps(payload(scene, castle_lib, build_model, castle), ensure_ascii=False, separators=(",", ":"))
    data = data.replace("</", "<\\/")
    if three_js:
        with open(three_js, encoding="utf-8") as f:
            script = "<script>" + f.read().replace("</script", "<\\/script") + "</script>"
    else:
        script = f'<script src="{THREE_CDN}"></script>'
    html = (html.replace("__SCENE_JSON__", data)
                .replace("__TITLE__", scene["meta"]["name"])
                .replace("__THREE_SCRIPT__", script))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("castle", help="castle.json des Burgenmeisters")
    ap.add_argument("-o", "--out", help="HTML-Datei (Standard: <castle>_schaubild.html)")
    ap.add_argument("--three", help="lokale three.min.js (r128) einbetten statt CDN")
    ap.add_argument("--burgenmeier", help="Pfad zum Burgenmeister-Skill oder dessen scripts/")
    a = ap.parse_args(argv)
    cl, bm = load_modules(find_burgenmeier(a.burgenmeier))
    castle = cl.load_castle(a.castle)
    scene = cl.build_scene(castle)
    out = a.out or os.path.splitext(a.castle)[0] + "_schaubild.html"
    print("Schaubild:", write_schaubild(scene, out, cl, bm, a.three, castle=castle))


if __name__ == "__main__":
    main()
