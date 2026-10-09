#!/usr/bin/env python3
"""Quellen- und Plausibilitätsbericht (Markdown) aus castle.json.

  python report.py castle.json -o bericht.md

Listet jedes Bauteil und jedes Umgebungselement mit Befundstufe, Quellen und
Anmerkung, dazu eine Übersicht, wie viel der Rekonstruktion belegt ist.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import castle_lib as cl  # noqa: E402

LABEL = {"gesichert": "gesichert", "wahrscheinlich": "wahrscheinlich",
         "analogie": "nach Analogie", "annahme": "Annahme"}
TYPE_DE = {"wall": "Mauer", "tower": "Turm", "building": "Gebäude", "gate": "Tor", "ditch": "Graben",
           "bridge": "Brücke"}
ENV_DE = {"forest": "Wald", "fields": "Flur", "water": "Gewässer", "rivers": "Fluss/Bach",
          "roads": "Weg", "settlements": "Siedlung"}
SRC_DE = {"plan": "Plan", "illustration": "Abbildung", "text": "Schriftquelle", "research": "Recherche",
          "analogy": "Analogie", "excavation": "Grabung", "map": "Karte"}


def _cell(s):
    return str(s or "").replace("|", "\\|").replace("\n", " ")


def report(castle):
    meta = castle.get("meta", {})
    site = castle.get("site", {})
    srcs = {s["id"]: s for s in meta.get("sources", []) if s.get("id")}
    L = [f"# {meta.get('name', 'Burg')} – Quellen- und Befundbericht", ""]
    if meta.get("date"):
        L.append(f"**Rekonstruierter Zustand:** um {meta['date']}  ")
    if site.get("lat") is not None:
        L.append(f"**Standort:** {site['lat']:.5f}° N, {site['lon']:.5f}° O"
                 + (f", ca. {site['elevation']} m ü. NN" if site.get("elevation") else "") + "  ")
    terr = site.get("terrain", {})
    L.append("**Gelände:** " + ("Höhenmodell (" + terr["heightmap"] + ")" if terr.get("heightmap")
                                else f"prozedural ({terr.get('type', 'hilltop')}, Relief {terr.get('relief', 60)} m)"))
    if meta.get("description"):
        L += ["", meta["description"]]

    els = [cl.element_defaults(e) for e in castle.get("elements", [])]
    counts = {c: 0 for c in cl.CONFIDENCE_LEVELS}
    for e in els:
        counts[cl.confidence_of(e)] += 1
    total = len(els) or 1
    L += ["", "## Übersicht", "",
          "| Befundstufe | Bauteile | Anteil |", "|---|---:|---:|"]
    for c in cl.CONFIDENCE_LEVELS:
        L.append(f"| {LABEL[c]} | {counts[c]} | {counts[c] * 100 // total} % |")

    L += ["", "## Bauteile", "", "| Bauteil | Typ | Phase | Befund | Quellen | Anmerkung |", "|---|---|---|---|---|---|"]
    for e in els:
        ev = e.get("evidence") or {}
        L.append(f"| {_cell(e.get('name') or e.get('id'))} | {TYPE_DE.get(e['type'], e['type'])} | {_cell(e.get('phase'))} | "
                 f"{LABEL[cl.confidence_of(e)]} | {_cell(', '.join(ev.get('sources', [])) or '–')} | {_cell(ev.get('note'))} |")

    env = site.get("environment") or {}
    rows = []
    for key, de in ENV_DE.items():
        for item in env.get(key, []):
            ev = item.get("evidence") or {}
            rows.append(f"| {_cell(item.get('name') or item.get('kind') or de)} | {de} | {LABEL[cl.confidence_of(item)]} | "
                        f"{_cell(', '.join(ev.get('sources', [])) or '–')} | {_cell(ev.get('note'))} |")
    if rows:
        L += ["", "## Umgebung", "", "| Element | Art | Befund | Quellen | Anmerkung |", "|---|---|---|---|---|"] + rows

    L += ["", "## Quellen", ""]
    for sid, s in srcs.items():
        bits = [f"**{sid}**", SRC_DE.get(s.get("type"), s.get("type") or "")]
        title = s.get("title", "")
        if s.get("author"):
            title = f"{s['author']}: {title}"
        if s.get("year"):
            title += f" ({s['year']})"
        bits.append(title)
        line = " – ".join(b for b in bits if b)
        if s.get("url"):
            line += f" <{s['url']}>"
        if s.get("note"):
            line += f". {s['note']}"
        L.append(f"- {line}")
    L += ["", "## Befundstufen", "",
          "- **gesichert** – im Bestand, im Plan oder durch Grabung nachgewiesen",
          "- **wahrscheinlich** – durch Abbildung oder Schriftquelle gestützt, Detail ergänzt",
          "- **nach Analogie** – aus vergleichbaren Anlagen derselben Zeit und Region übertragen",
          "- **Annahme** – plausible Ergänzung ohne direkten Beleg", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("castle")
    ap.add_argument("-o", "--out")
    a = ap.parse_args(argv)
    md = report(cl.load_castle(a.castle))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(md)
        print("Bericht:", a.out)
    else:
        print(md)


if __name__ == "__main__":
    main()
