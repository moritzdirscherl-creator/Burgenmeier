#!/usr/bin/env python3
"""Pläne und historische Ansichten auf Wikimedia Commons finden und herunterladen.

  python commons.py search "Burg Eltz Grundriss"            Volltextsuche nach Dateien
  python commons.py category "Burg Eltz" [--depth 1]         Dateien einer Kategorie (+ Unterkategorien)
  python commons.py ... --download quellen/ --dossier quellen.json [--limit 20] [--width 2000]

Jede Datei wird mit Urheber, Datierung, Lizenz und Beschreibung erfasst. Der Typ (plan / illustration /
map / photo) wird aus Titel und Beschreibung geschätzt; prüfe ihn beim Ansehen der Bilder.
Fotos des heutigen Zustands kommen nur mit `--fotos` ins Dossier.
"""

import argparse
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net  # noqa: E402

API = "https://commons.wikimedia.org/w/api.php"

PLAN_WORDS = ("grundriss", "plan", "lageplan", "floor plan", "ground plan", "aufriss", "schnitt", "section",
              "bauaufnahme", "rekonstruktion", "reconstruction", "piper", "ebhardt", "kunstdenkm")
MAP_WORDS = ("karte", "map", "urkataster", "uraufnahme", "messtisch", "tranchot", "flurkarte", "landtafel")
ILLU_WORDS = ("merian", "kupferstich", "stich", "engraving", "vedute", "ansicht", "view", "lithograph",
              "lithografie", "gemälde", "painting", "zeichnung", "drawing", "aquarell", "holzschnitt", "woodcut",
              "dilich", "wening", "vischer", "meisner", "kieser", "topographia", "chronik", "chronicle")


def _plain(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return html.unescape(s).strip()


def guess_type(title, desc, year):
    t = (title + " " + desc).lower()
    if any(w in t for w in MAP_WORDS):
        return "map"
    if any(w in t for w in PLAN_WORDS):
        return "plan"
    if any(w in t for w in ILLU_WORDS):
        return "illustration"
    if year and year < 1900:
        return "illustration"
    return "photo"


def _year(s):
    m = re.search(r"\b(1[0-9]{3})\b", s or "")
    return int(m.group(1)) if m else None


def _info(pages, width):
    out = []
    for p in pages.values():
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})

        def m(k):
            return _plain(md.get(k, {}).get("value", ""))

        desc = m("ImageDescription")
        date = m("DateTimeOriginal") or m("DateTime")
        year = _year(date) or _year(desc) or _year(p.get("title", ""))
        title = p.get("title", "").replace("File:", "").replace("Datei:", "")
        out.append({
            "commons_titel": title,
            "title": m("ObjectName") or os.path.splitext(title)[0],
            "author": m("Artist"), "date": date, "year": year,
            "license": m("LicenseShortName"), "credit": m("Credit"),
            "beschreibung": desc[:600],
            "url": ii.get("descriptionurl") or "https://commons.wikimedia.org/wiki/" + p.get("title", "").replace(" ", "_"),
            "download": ii.get("thumburl") or ii.get("url"),
            "mime": ii.get("mime", ""),
            "type": guess_type(title, desc, year),
        })
    return out


IIPROPS = {"prop": "imageinfo", "iiprop": "url|extmetadata|mime|size",
           "iiextmetadatafilter": "ImageDescription|Artist|DateTimeOriginal|DateTime|LicenseShortName|Credit|ObjectName",
           "iiextmetadatalanguage": "de", "format": "json"}


def search(query, limit=20, width=2000):
    res = net.get(API, {"action": "query", "generator": "search", "gsrsearch": query, "gsrnamespace": 6,
                        "gsrlimit": limit, "iiurlwidth": width, **IIPROPS})
    return _info(res.get("query", {}).get("pages", {}), width)


def category(name, limit=50, width=2000, depth=0):
    name = name.replace("Category:", "").replace("Kategorie:", "")
    res = net.get(API, {"action": "query", "generator": "categorymembers", "gcmtitle": "Category:" + name,
                        "gcmtype": "file", "gcmlimit": limit, "iiurlwidth": width, **IIPROPS})
    files = _info(res.get("query", {}).get("pages", {}), width)
    if depth > 0:
        sub = net.get(API, {"action": "query", "list": "categorymembers", "cmtitle": "Category:" + name,
                            "cmtype": "subcat", "cmlimit": 50, "format": "json"})
        for c in sub.get("query", {}).get("categorymembers", []):
            if len(files) >= limit:
                break
            files += category(c["title"], limit - len(files), width, depth - 1)
    return files[:limit]


def download(files, folder):
    os.makedirs(folder, exist_ok=True)
    for f in files:
        if not f.get("download"):  # PDF/DjVu liefern über thumburl eine gerenderte Seite als Bild
            continue
        ext = os.path.splitext(f["download"].split("?")[0])[1] or ".jpg"
        base = re.sub(r"[^\w\-]+", "_", os.path.splitext(f["commons_titel"])[0])[:80]
        path = os.path.join(folder, base + ext)
        if not os.path.exists(path):
            with open(path, "wb") as fh:
                fh.write(net.get(f["download"], raw=True, timeout=90))
        f["file"] = path
    return files


def to_dossier(files, path, fotos=False):
    import dossier
    d = dossier.load(path) if os.path.exists(path) else dossier.new("Burg")
    n = 0
    for f in files:
        if f["type"] == "photo" and not fotos:
            continue
        note = f["beschreibung"][:300]
        if f["credit"] and f["credit"] not in note:
            note += f" · Nachweis: {f['credit'][:150]}"
        added = dossier.add_source(d, {
            "type": f["type"] if f["type"] != "photo" else "illustration",
            "title": f["title"], "author": f["author"], "year": f["year"], "url": f["url"],
            "file": f.get("file"), "license": f["license"], "viewed": False,
            "note": note.strip(), "herkunft": "Wikimedia Commons"})
        n += 1 if added else 0
    dossier.save(d, path)
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modus", choices=["search", "category"])
    ap.add_argument("begriff")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--width", type=int, default=2000, help="Breite der heruntergeladenen Fassung in Pixeln")
    ap.add_argument("--depth", type=int, default=0, help="Unterkategorien mit durchsuchen (category)")
    ap.add_argument("--download", help="Ordner für die Bilddateien")
    ap.add_argument("--dossier", help="quellen.json, in das die Treffer als Quellen übernommen werden")
    ap.add_argument("--fotos", action="store_true", help="auch heutige Fotos ins Dossier übernehmen")
    a = ap.parse_args(argv)
    files = search(a.begriff, a.limit, a.width) if a.modus == "search" else \
        category(a.begriff, a.limit, a.width, a.depth)
    if a.download:
        download(files, a.download)
    for f in files:
        print(f"[{f['type']:12}] {f['year'] or '?':>5}  {f['title'][:70]}  ({f['license'] or 'Lizenz?'})"
              + (f"  → {f['file']}" if f.get("file") else ""))
    print(f"{len(files)} Dateien")
    if a.dossier:
        print(f"{to_dossier(files, a.dossier, a.fotos)} neue Quellen im Dossier {a.dossier}")


if __name__ == "__main__":
    main()
