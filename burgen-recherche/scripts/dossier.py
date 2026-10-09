#!/usr/bin/env python3
"""Quellendossier (quellen.json) führen, prüfen und als Bericht oder castle.json-Gerüst ausgeben.

  init     "Burg Name" -o quellen.json
  add      quellen.json --type plan --title "…" [--author --year --url --file --license --note --viewed
           --reliability hoch|mittel|gering]
  befund   quellen.json Q3 --bauteil Bergfried --aussage "…" [--zitat "…"]
  ereignis quellen.json --jahr 1157 --text "Ersterwähnung" [--quelle Q3]
  luecke   quellen.json "kein Grundriss der Vorburg"
  setze    quellen.json lage=spur lat=50.2 lon=7.3 ort="Wierschem" zieldatum=1350
  check    quellen.json                 Vollständigkeit/Ehrlichkeit prüfen
  render   quellen.json -o dossier.md   lesbarer Bericht
  castle   quellen.json -o castle.json  Gerüst für den Skill „burgenmeier“ (meta + site, Quellen übernommen)

Quellentypen: plan, illustration, text, map, excavation, research, analogy.
`viewed` heißt: der Inhalt wurde tatsächlich gesehen/gelesen – nicht nur in Sekundärliteratur erwähnt.
"""

import argparse
import json
import os
import sys

TYPES = ["plan", "illustration", "text", "map", "excavation", "research", "analogy"]
TYPE_DE = {"plan": "Plan", "illustration": "Abbildung", "text": "Schriftquelle", "map": "Karte",
           "excavation": "Grabung/Bauforschung", "research": "Sekundärliteratur/Normdaten", "analogy": "Vergleichsbau"}
LAGEN = ["spur", "hilltop", "crag", "slope", "lowland", "island"]


def new(name):
    return {"burg": {"name": name, "namensvarianten": []}, "zeitleiste": [], "sources": [], "luecken": []}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(d, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def _next_id(d):
    n = [int(s["id"][1:]) for s in d["sources"] if s.get("id", "")[:1] == "Q" and s["id"][1:].isdigit()]
    return f"Q{max(n, default=0) + 1}"


def add_source(d, src):
    """Fügt eine Quelle hinzu; Dubletten (gleiche URL oder gleicher Titel+Jahr) werden zusammengeführt."""
    if src.get("type") not in TYPES:
        raise ValueError(f"unbekannter Quellentyp {src.get('type')} ({', '.join(TYPES)})")
    for s in d["sources"]:
        same_url = src.get("url") and s.get("url") == src.get("url")
        same_title = s.get("title") == src.get("title") and s.get("year") == src.get("year") and src.get("title")
        if same_url or same_title:
            for k, v in src.items():
                if v not in (None, "", []) and not s.get(k):
                    s[k] = v
            return None
    src = {k: v for k, v in src.items() if v not in (None, "")}
    src.setdefault("viewed", False)
    src.setdefault("befunde", [])
    src["id"] = src.get("id") or _next_id(d)
    d["sources"].append(src)
    return src["id"]


def check(d):
    """Gibt (Fehler, Hinweise) zurück."""
    errs, hints = [], []
    b = d.get("burg", {})
    if b.get("lat") is None or b.get("lon") is None:
        errs.append("Koordinaten fehlen (burg.lat/lon)")
    if b.get("lage") and b["lage"] not in LAGEN:
        errs.append(f"burg.lage '{b['lage']}' unbekannt ({', '.join(LAGEN)})")
    if not b.get("lage"):
        hints.append("Lagetyp (burg.lage) nicht gesetzt")
    if not b.get("zieldatum"):
        hints.append("Zieldatum der Rekonstruktion (burg.zieldatum) nicht festgelegt")
    ids = set()
    for s in d.get("sources", []):
        if s["id"] in ids:
            errs.append(f"Quellen-id doppelt: {s['id']}")
        ids.add(s["id"])
        if not (s.get("url") or s.get("file") or s.get("author") or s.get("signatur")):
            errs.append(f"{s['id']}: weder URL, Datei, Autor noch Signatur – Quelle nicht nachprüfbar")
        if s.get("befunde") and not s.get("viewed"):
            hints.append(f"{s['id']}: Befunde eingetragen, aber viewed=false – nur indirekt zitiert? Dann in note vermerken")
    for e in d.get("zeitleiste", []):
        if e.get("quelle") and e["quelle"] not in ids:
            errs.append(f"Zeitleiste {e.get('jahr')}: Quelle {e['quelle']} unbekannt")
    by_type = {t: [s for s in d.get("sources", []) if s.get("type") == t] for t in TYPES}
    if not by_type["plan"]:
        hints.append("kein Plan gefunden – Grundriss muss aus Luftbild/LiDAR/Beschreibung erschlossen werden")
    if not by_type["illustration"]:
        hints.append("keine historische Abbildung gefunden – Aufriss/Dächer nur nach Analogie")
    if not by_type["text"]:
        hints.append("keine Schriftquelle ausgewertet")
    if not by_type["map"]:
        hints.append("keine historische Karte – Umgebung nur nach Heuristik")
    return errs, hints


def render(d):
    b = d["burg"]
    L = [f"# Quellendossier: {b.get('name', 'Burg')}", ""]
    rows = [("Namensvarianten", ", ".join(b.get("namensvarianten", []))),
            ("Lage", f"{b['lat']:.5f}° N, {b['lon']:.5f}° O" if b.get("lat") is not None else ""),
            ("Höhe", f"{b['hoehe']:g} m ü. NN" if b.get("hoehe") is not None else ""),
            ("Ort", b.get("ort", "")), ("Lagetyp", b.get("lage", "")), ("Gründung/Ersterwähnung", b.get("gruendung", "")),
            ("Zustand heute", b.get("zustand", "")), ("Zieldatum Rekonstruktion", str(b.get("zieldatum", ""))),
            ("Wikidata", b.get("wikidata", "")), ("Commons-Kategorie", b.get("commons_kategorie", ""))]
    L += [f"- **{k}:** {v}" for k, v in rows if v]
    if d.get("zeitleiste"):
        L += ["", "## Zeitleiste", ""]
        for e in sorted(d["zeitleiste"], key=lambda e: str(e.get("jahr"))):
            L.append(f"- **{e.get('jahr')}** – {e.get('text')}" + (f" [{e['quelle']}]" if e.get("quelle") else ""))
    L += ["", "## Quellen", ""]
    for t in TYPES:
        srcs = [s for s in d["sources"] if s.get("type") == t]
        if not srcs:
            continue
        L += [f"### {TYPE_DE[t]}", ""]
        for s in srcs:
            head = f"**{s['id']}** {s.get('author') + ': ' if s.get('author') else ''}{s.get('title', '')}"
            if s.get("year"):
                head += f" ({s['year']})"
            flags = ["gesichtet" if s.get("viewed") else "nicht selbst gesichtet"]
            if s.get("reliability"):
                flags.append(f"Quellenwert {s['reliability']}")
            if s.get("license"):
                flags.append(f"Lizenz {s['license']}")
            L.append(f"- {head} – *{', '.join(flags)}*")
            if s.get("url"):
                L.append(f"  - <{s['url']}>")
            if s.get("file"):
                L.append(f"  - Datei: `{s['file']}`")
            if s.get("signatur"):
                L.append(f"  - Signatur/Fundstelle: {s['signatur']}")
            if s.get("note"):
                L.append(f"  - {s['note']}")
            for bf in s.get("befunde", []):
                z = f" – „{bf['zitat']}“" if bf.get("zitat") else ""
                L.append(f"  - ➜ *{bf['bauteil']}:* {bf['aussage']}{z}")
        L.append("")
    befunde = {}
    for s in d["sources"]:
        for bf in s.get("befunde", []):
            befunde.setdefault(bf["bauteil"], []).append((s["id"], bf["aussage"]))
    if befunde:
        L += ["## Befunde nach Bauteil", "", "| Bauteil | Aussagen (Quelle) |", "|---|---|"]
        for k, v in befunde.items():
            L.append(f"| {k} | " + "<br>".join(f"{a} [{i}]" for i, a in v).replace("|", "\\|") + " |")
        L.append("")
    errs, hints = check(d)
    gaps = d.get("luecken", []) + hints
    if gaps:
        L += ["## Lücken und offene Fragen", ""] + [f"- {g}" for g in gaps] + [""]
    if errs:
        L += ["## Prüfhinweise", ""] + [f"- ⚠ {e}" for e in errs] + [""]
    return "\n".join(L)


def to_castle(d, extent=None):
    b = d["burg"]
    srcs = []
    for s in d["sources"]:
        note = s.get("note", "")
        if not s.get("viewed"):
            note = ("nicht selbst gesichtet; " + note).strip("; ")
        e = {k: s[k] for k in ("id", "type", "title", "author", "year", "url") if s.get(k) not in (None, "")}
        e["note"] = note
        srcs.append(e)
    lage = b.get("lage") or "hilltop"
    castle = {
        "meta": {"name": b.get("name", "Burg"), "date": b.get("zieldatum"),
                 "description": b.get("zustand", ""), "sources": srcs},
        "site": {"lat": b.get("lat"), "lon": b.get("lon"), "elevation": b.get("hoehe"),
                 "extent": extent or (600 if lage in ("lowland", "island") else 800), "resolution": 80,
                 "terrain": {"type": lage, "relief": b.get("relief", 5 if lage in ("lowland", "island") else 60),
                             "direction": b.get("richtung", 90)},
                 "environment": {}},
        "elements": [],
    }
    return castle


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("name")
    p.add_argument("-o", "--out", default="quellen.json")
    p = sub.add_parser("add")
    p.add_argument("dossier")
    p.add_argument("--type", required=True, choices=TYPES)
    p.add_argument("--title", required=True)
    for k in ("author", "url", "file", "license", "note", "signatur", "reliability"):
        p.add_argument("--" + k)
    p.add_argument("--year", type=int)
    p.add_argument("--viewed", action="store_true")
    p = sub.add_parser("befund")
    p.add_argument("dossier")
    p.add_argument("quelle")
    p.add_argument("--bauteil", required=True)
    p.add_argument("--aussage", required=True)
    p.add_argument("--zitat")
    p = sub.add_parser("ereignis")
    p.add_argument("dossier")
    p.add_argument("--jahr", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--quelle")
    p = sub.add_parser("luecke")
    p.add_argument("dossier")
    p.add_argument("text")
    p = sub.add_parser("setze")
    p.add_argument("dossier")
    p.add_argument("paare", nargs="+", help="schluessel=wert")
    for name in ("check", "render", "castle"):
        p = sub.add_parser(name)
        p.add_argument("dossier")
        if name != "check":
            p.add_argument("-o", "--out")
    a = ap.parse_args(argv)

    if a.cmd == "init":
        save(new(a.name), a.out)
        print("Dossier angelegt:", a.out)
        return 0
    d = load(a.dossier)
    if a.cmd == "add":
        sid = add_source(d, {"type": a.type, "title": a.title, "author": a.author, "year": a.year, "url": a.url,
                             "file": a.file, "license": a.license, "note": a.note, "signatur": a.signatur,
                             "reliability": a.reliability, "viewed": a.viewed})
        save(d, a.dossier)
        print(f"Quelle {sid} hinzugefügt" if sid else "Quelle war schon erfasst – ergänzt")
    elif a.cmd == "befund":
        src = next((s for s in d["sources"] if s["id"] == a.quelle), None)
        if not src:
            sys.exit(f"Quelle {a.quelle} nicht im Dossier")
        src.setdefault("befunde", []).append({k: v for k, v in
                                              (("bauteil", a.bauteil), ("aussage", a.aussage), ("zitat", a.zitat)) if v})
        save(d, a.dossier)
        print(f"Befund zu {a.bauteil} bei {a.quelle} eingetragen")
    elif a.cmd == "ereignis":
        d["zeitleiste"].append({k: v for k, v in (("jahr", a.jahr), ("text", a.text), ("quelle", a.quelle)) if v})
        save(d, a.dossier)
    elif a.cmd == "luecke":
        d["luecken"].append(a.text)
        save(d, a.dossier)
    elif a.cmd == "setze":
        for pair in a.paare:
            k, _, v = pair.partition("=")
            if k in ("lat", "lon", "hoehe", "relief", "richtung"):
                v = float(v)
            elif k == "zieldatum" and v.isdigit():
                v = int(v)
            elif k == "namensvarianten":
                v = [x.strip() for x in v.split(",") if x.strip()]
            d["burg"][k] = v
        save(d, a.dossier)
    elif a.cmd == "check":
        errs, hints = check(d)
        for h in hints:
            print("HINWEIS:", h)
        for e in errs:
            print("FEHLER: ", e)
        print(f"{len(d['sources'])} Quellen ({sum(1 for s in d['sources'] if s.get('viewed'))} gesichtet), "
              f"{len(errs)} Fehler, {len(hints)} Hinweise")
        return 1 if errs else 0
    elif a.cmd == "render":
        md = render(d)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                f.write(md)
            print("Dossier:", a.out)
        else:
            print(md)
    elif a.cmd == "castle":
        out = a.out or "castle.json"
        if os.path.exists(out):
            sys.exit(f"{out} existiert schon – nicht überschrieben (anderen Namen wählen)")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(to_castle(d), f, ensure_ascii=False, indent=1)
        print(f"castle.json-Gerüst: {out} – jetzt elements und environment ergänzen (Skill burgenmeier)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
