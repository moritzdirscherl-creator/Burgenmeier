#!/usr/bin/env python3
"""Prüft castle.json auf Schemafehler und Plausibilität.

  python validate.py castle.json

Exit-Code 1 bei Fehlern; Warnungen weisen auf unplausible oder unbelegte Angaben hin.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import castle_lib as cl  # noqa: E402

PLAUSIBLE = {
    # Typ: (Feld, min, max) – grobe Spannweiten mitteleuropäischer Burgen
    "wall": [("height", 2, 25), ("thickness", 0.4, 6)],
    "tower": [("height", 5, 60), ("radius", 1.5, 15)],
    "building": [("height", 2.5, 30)],
    "gate": [("height", 4, 35)],
    "ditch": [("width", 2, 50), ("depth", 0.5, 30)],
    "bridge": [("width", 1, 10)],
}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _pts(v, minlen):
    return isinstance(v, list) and len(v) >= minlen and all(
        isinstance(p, (list, tuple)) and len(p) >= 2 and _num(p[0]) and _num(p[1]) for p in v)


def validate(castle):
    errors, warnings = [], []
    E, W = errors.append, warnings.append
    meta = castle.get("meta")
    if not isinstance(meta, dict) or not meta.get("name"):
        E("meta.name fehlt")
        meta = meta or {}
    if meta.get("date") is None:
        W("meta.date fehlt – auf welchen Zeitpunkt bezieht sich die Rekonstruktion?")
    src_ids = set()
    for s in meta.get("sources", []):
        if not s.get("id"):
            E(f"Quelle ohne id: {s}")
        elif s["id"] in src_ids:
            E(f"Quellen-id doppelt: {s['id']}")
        src_ids.add(s.get("id"))
        if s.get("type") not in ("plan", "illustration", "text", "research", "analogy", "excavation", "map", None):
            W(f"Quelle {s.get('id')}: unbekannter type '{s.get('type')}'")
    src_ids.add("OSM")

    site = castle.get("site")
    if not isinstance(site, dict):
        E("site fehlt")
        site = {}
    if not (_num(site.get("lat")) and _num(site.get("lon"))):
        W("site.lat/lon fehlen – Standort nicht recherchiert (Gelände bleibt prozedural, kein Geobezug)")
    ext = site.get("extent", 700)
    if not _num(ext) or not 100 <= ext <= 5000:
        E("site.extent muss zwischen 100 und 5000 m liegen")
        ext = 700
    res = site.get("resolution", 70)
    if not isinstance(res, int) or not 10 <= res <= 250:
        E("site.resolution muss eine ganze Zahl zwischen 10 und 250 sein")
    terr = site.get("terrain", {})
    if terr.get("heightmap"):
        p = terr["heightmap"]
        if not os.path.isabs(p):
            p = os.path.join(castle.get("_base_dir", "."), p)
        if not os.path.exists(p):
            E(f"Höhenmodell nicht gefunden: {terr['heightmap']}")
    elif terr.get("type") not in (None, "hilltop", "gipfel", "crag", "fels", "spur", "sporn", "slope", "hang",
                                  "lowland", "niederung", "island", "insel", "plain", "ebene"):
        E(f"site.terrain.type unbekannt: {terr.get('type')}")

    def check_evidence(obj, label):
        ev = obj.get("evidence")
        if not ev:
            W(f"{label}: keine evidence – wird als 'annahme' behandelt")
            return
        c = ev.get("confidence")
        if c not in cl.CONFIDENCE_LEVELS:
            E(f"{label}: confidence '{c}' ungültig ({', '.join(cl.CONFIDENCE_LEVELS)})")
        for s in ev.get("sources", []):
            if s not in src_ids:
                E(f"{label}: Quelle '{s}' nicht in meta.sources")
        if c in ("gesichert", "wahrscheinlich") and not ev.get("sources"):
            W(f"{label}: '{c}' ohne Quellenangabe")

    half = ext / 2
    ids = set()
    for k, el in enumerate(castle.get("elements", [])):
        t = el.get("type")
        lab = f"Element {el.get('id') or k} ({t})"
        if t not in cl.ELEMENT_TYPES:
            E(f"{lab}: unbekannter Typ (erlaubt: {', '.join(cl.ELEMENT_TYPES)})")
            continue
        if el.get("id"):
            if el["id"] in ids:
                E(f"{lab}: id doppelt")
            ids.add(el["id"])
        else:
            W(f"{lab}: keine id")
        d = cl.element_defaults(el)
        if t in ("wall", "ditch", "bridge"):
            if not _pts(d.get("path"), 2):
                E(f"{lab}: path braucht mindestens 2 Punkte [x, y]")
                continue
            pts = d["path"]
        else:
            if d.get("polygon") is not None:
                if not _pts(d["polygon"], 3):
                    E(f"{lab}: polygon braucht mindestens 3 Punkte")
                    continue
                if abs(cl.poly_area(d["polygon"])) < 1:
                    E(f"{lab}: polygon hat (fast) keine Fläche")
                pts = d["polygon"]
            elif _pts([d.get("center")], 1):
                pts = [d["center"]]
            else:
                E(f"{lab}: polygon oder center fehlt")
                continue
        if any(abs(p[0]) > half or abs(p[1]) > half for p in pts):
            E(f"{lab}: liegt außerhalb von site.extent (±{half:g} m)")
        for field, lo, hi in PLAUSIBLE.get(t, []):
            v = d.get(field)
            if v is None:
                continue
            if not _num(v):
                E(f"{lab}: {field} ist keine Zahl")
            elif not lo <= v <= hi:
                W(f"{lab}: {field} = {v} ist ungewöhnlich (typisch {lo}–{hi})")
        if t in ("tower", "building", "gate"):
            roof = d.get("roof")
            if roof not in cl.ROOF_TYPES:
                E(f"{lab}: roof '{roof}' unbekannt ({', '.join(cl.ROOF_TYPES)})")
        for key in ("material", "roof_material"):
            m = d.get(key)
            if m and not (m in cl.MATERIALS or str(m).startswith("#")):
                W(f"{lab}: {key} '{m}' unbekannt – Standardfarbe wird verwendet")
        check_evidence(el, lab)

    env = site.get("environment") or {}
    for key, need, minlen in (("forest", "polygon", 3), ("fields", "polygon", 3), ("water", "polygon", 3),
                              ("settlements", "polygon", 3), ("rivers", "path", 2), ("roads", "path", 2)):
        for k, item in enumerate(env.get(key, [])):
            lab = f"Umgebung {key}[{k}]"
            if not _pts(item.get(need), minlen):
                E(f"{lab}: {need} fehlt oder zu kurz")
            check_evidence(item, lab)
    if not castle.get("elements"):
        E("keine elements – nichts zu bauen")
    if not any(cl.element_defaults(e).get("type") == "wall" for e in castle.get("elements", [])):
        W("keine Mauer (wall) – ist das beabsichtigt?")
    if not errors:
        try:
            cl.build_scene(castle)
        except Exception as ex:  # Geometriefehler sichtbar machen
            E(f"Szene lässt sich nicht bauen: {ex}")
    return errors, warnings


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    castle = cl.load_castle(argv[0])
    errors, warnings = validate(castle)
    for w in warnings:
        print("WARNUNG:", w)
    for e in errors:
        print("FEHLER: ", e)
    print(f"{len(errors)} Fehler, {len(warnings)} Warnungen")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
