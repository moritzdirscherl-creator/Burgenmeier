#!/usr/bin/env python3
"""Grunddaten einer Burg aus Wikidata.

  python wikidata.py "Burg Eltz"                  Kandidaten + Details zum besten Treffer
  python wikidata.py Q565582                      Details zu einer bekannten Q-ID
  python wikidata.py "Burg Eltz" --dossier quellen.json
                                                  Fakten und Wikidata als Quelle ins Dossier übernehmen

Ausgegeben werden: Namen und Namensvarianten, Koordinaten, Höhe, Gründungsdatum, Denkmalstatus,
Verwaltungseinheit, Commons-Kategorie, Bild, Grundrissbild und Wikipedia-Artikel. Die Namensvarianten
sind wichtig für die weitere Quellensuche (alte Schreibweisen, lateinische Namen).
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net  # noqa: E402

API = "https://www.wikidata.org/w/api.php"
CASTLE_WORDS = ("burg", "castle", "ruine", "ruin", "schloss", "festung", "fortress", "motte", "wasserburg")

PROPS = {
    "P625": "koordinaten", "P2044": "hoehe", "P571": "gruendung", "P1435": "denkmalstatus",
    "P131": "liegt_in", "P373": "commons_kategorie", "P18": "bild", "P3311": "grundrissbild",
    "P17": "staat", "P31": "ist_ein",
}


def search(name, limit=7):
    res = net.get(API, {"action": "wbsearchentities", "search": name, "language": "de", "uselang": "de",
                        "format": "json", "limit": limit, "type": "item"})
    out = []
    for r in res.get("search", []):
        desc = r.get("description", "")
        out.append({"id": r["id"], "label": r.get("label", ""), "description": desc,
                    "burgartig": any(w in (desc + " " + r.get("label", "")).lower() for w in CASTLE_WORDS)})
    return out


def _labels(ids):
    if not ids:
        return {}
    res = net.get(API, {"action": "wbgetentities", "ids": "|".join(sorted(ids)[:50]), "props": "labels",
                        "languages": "de|en", "format": "json"})
    out = {}
    for i, e in res.get("entities", {}).items():
        lab = e.get("labels", {})
        out[i] = (lab.get("de") or lab.get("en") or {}).get("value", i)
    return out


def _time(v):
    t = v.get("time", "")
    prec = v.get("precision", 11)
    year = t[1:5].lstrip("0") if t.startswith("+") else t[:5]
    if prec <= 7:
        return f"{int(year) // 100 + 1}. Jh."
    if prec == 8:
        return f"{year}er"
    return year


def entity(qid):
    res = net.get(API, {"action": "wbgetentities", "ids": qid, "props": "claims|labels|descriptions|aliases|sitelinks",
                        "languages": "de|en|la|fr|it|cs|pl", "format": "json"})
    e = res["entities"][qid]
    claims = e.get("claims", {})
    f = {"wikidata": qid, "wikidata_url": f"https://www.wikidata.org/wiki/{qid}"}
    labels = e.get("labels", {})
    f["name"] = (labels.get("de") or labels.get("en") or {}).get("value", qid)
    f["beschreibung"] = (e.get("descriptions", {}).get("de") or e.get("descriptions", {}).get("en") or {}).get("value", "")
    variants = {l["value"] for l in labels.values()}
    for lst in e.get("aliases", {}).values():
        variants |= {a["value"] for a in lst}
    variants.discard(f["name"])
    f["namensvarianten"] = sorted(variants)
    items = set()

    def values(p):
        out = []
        for c in claims.get(p, []):
            dv = c.get("mainsnak", {}).get("datavalue")
            if dv:
                out.append(dv["value"])
        return out

    for p, key in PROPS.items():
        vs = values(p)
        if not vs:
            continue
        v = vs[0]
        if p == "P625":
            f["lat"], f["lon"] = round(v["latitude"], 6), round(v["longitude"], 6)
        elif p == "P2044":
            f["hoehe"] = float(v["amount"])
        elif p == "P571":
            f["gruendung"] = _time(v)
        elif p in ("P1435", "P131", "P17", "P31"):
            f[key] = [x["id"] for x in vs if isinstance(x, dict) and "id" in x]
            items |= set(f[key])
        else:  # Commons-Dateien und -Kategorie sind Zeichenketten
            f[key] = v
    names = _labels(items)
    for key in ("denkmalstatus", "liegt_in", "staat", "ist_ein"):
        if key in f:
            f[key] = [names.get(i, i) for i in f[key]]
    for key in ("bild", "grundrissbild"):
        if key in f:
            f[key + "_url"] = "https://commons.wikimedia.org/wiki/File:" + f[key].replace(" ", "_")
    if "commons_kategorie" in f:
        f["commons_kategorie_url"] = "https://commons.wikimedia.org/wiki/Category:" + f["commons_kategorie"].replace(" ", "_")
    links = e.get("sitelinks", {})
    f["wikipedia"] = {s[:-4]: f"https://{s[:-4]}.wikipedia.org/wiki/{v['title'].replace(' ', '_')}"
                      for s, v in links.items() if s.endswith("wiki") and s[:-4] in ("de", "en", "fr", "it", "cs", "pl", "nl")}
    return f


def to_dossier(facts, path):
    import dossier
    d = dossier.load(path) if os.path.exists(path) else dossier.new(facts["name"])
    b = d["burg"]
    for k in ("name", "wikidata", "lat", "lon", "hoehe", "gruendung", "namensvarianten", "commons_kategorie"):
        if facts.get(k) not in (None, "", []):
            if k == "namensvarianten":
                b[k] = sorted(set(b.get(k, [])) | set(facts[k]))
            elif not b.get(k):
                b[k] = facts[k]
    if facts.get("liegt_in"):
        b.setdefault("ort", ", ".join(facts["liegt_in"]))
    dossier.add_source(d, {"type": "research", "title": f"Wikidata {facts['wikidata']}: {facts['name']}",
                           "url": facts["wikidata_url"], "viewed": True, "reliability": "mittel",
                           "note": "Normdaten (Koordinaten, Datierung, Commons-Kategorie); Sekundärdaten, keine Primärquelle"})
    for lang, url in facts.get("wikipedia", {}).items():
        if lang in ("de", "en"):
            dossier.add_source(d, {"type": "research", "title": f"Wikipedia ({lang}): {facts['name']}", "url": url,
                                   "viewed": False, "reliability": "gering",
                                   "note": "Überblick; Literaturangaben dort als Wegweiser zu Primärquellen nutzen"})
    dossier.save(d, path)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name_oder_qid")
    ap.add_argument("--dossier", help="quellen.json, in das Fakten und Quelle übernommen werden")
    a = ap.parse_args(argv)
    q = a.name_oder_qid
    if q[:1] == "Q" and q[1:].isdigit():
        qid = q
    else:
        cands = search(q)
        print(json.dumps({"kandidaten": cands}, ensure_ascii=False, indent=1))
        best = next((c for c in cands if c["burgartig"]), cands[0] if cands else None)
        if not best:
            sys.exit("Kein Treffer – Schreibweise variieren oder Ort ergänzen.")
        qid = best["id"]
        print(f"→ Details zu {qid} ({best['label']}: {best['description']}). Falls falsch: mit Q-ID erneut aufrufen.")
    facts = entity(qid)
    print(json.dumps(facts, ensure_ascii=False, indent=1))
    if a.dossier:
        print("Dossier:", to_dossier(facts, a.dossier))


if __name__ == "__main__":
    main()
