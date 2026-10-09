#!/usr/bin/env python3
"""Standort- und Umgebungsrecherche für castle.json.

Unterbefehle:
  geocode "Burg Name"                 Koordinaten-Kandidaten (Wikidata, dann Nominatim)
  terrain castle.json -o hm.json      echtes Höhenmodell (AWS Terrain Tiles / Terrarium, ~5–10 m)
  osm castle.json -o osm.json         heutige Gewässer, Wald, Wege, Orte aus OpenStreetMap
                                      (als Rohmaterial für site.environment – muss auf das
                                      Zieldatum rückprojiziert werden!)
  local castle.json LAT LON           WGS84 -> lokale Meter (x Ost, y Nord) relativ zur Burg
  latlon castle.json X Y              lokale Meter -> WGS84

Alle Netzzugriffe sind optional: Ohne Netz arbeitet build_model/draw_view mit dem
prozeduralen Gelände aus site.terrain.
"""

import argparse
import io
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

UA = "Burgenmeier/1.0 (Burgrekonstruktion; https://github.com/)"
R_EARTH = 6378137.0


def _get(url, data=None, timeout=40, tries=4):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as ex:  # vorübergehende Fehler (404/429/5xx bei Kachelservern) erneut versuchen
            last = ex
            time.sleep(1.5 * (k + 1))
    raise last


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Koordinaten
# ---------------------------------------------------------------------------

def to_local(lat0, lon0, lat, lon):
    x = math.radians(lon - lon0) * R_EARTH * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * R_EARTH
    return x, y


def to_latlon(lat0, lon0, x, y):
    lat = lat0 + math.degrees(y / R_EARTH)
    lon = lon0 + math.degrees(x / (R_EARTH * math.cos(math.radians(lat0))))
    return lat, lon


def _site(castle):
    s = castle.get("site", {})
    if s.get("lat") is None or s.get("lon") is None:
        sys.exit("site.lat / site.lon fehlen in castle.json – zuerst den Standort recherchieren (geocode).")
    return float(s["lat"]), float(s["lon"]), float(s.get("extent", 700))


# ---------------------------------------------------------------------------
# Geokodierung
# ---------------------------------------------------------------------------

def geocode(name, limit=5):
    out = []
    try:
        q = urllib.parse.urlencode({"action": "wbsearchentities", "search": name, "language": "de",
                                    "format": "json", "limit": limit, "type": "item"})
        res = json.loads(_get("https://www.wikidata.org/w/api.php?" + q))
        ids = [r["id"] for r in res.get("search", [])]
        if ids:
            q = urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(ids), "props": "claims|labels|descriptions",
                                        "languages": "de|en", "format": "json"})
            ents = json.loads(_get("https://www.wikidata.org/w/api.php?" + q))["entities"]
            for i in ids:
                e = ents.get(i, {})
                c = e.get("claims", {}).get("P625")
                if not c:
                    continue
                v = c[0]["mainsnak"]["datavalue"]["value"]
                lab = (e.get("labels", {}).get("de") or e.get("labels", {}).get("en") or {}).get("value", i)
                desc = (e.get("descriptions", {}).get("de") or e.get("descriptions", {}).get("en") or {}).get("value", "")
                out.append({"name": lab, "description": desc, "lat": v["latitude"], "lon": v["longitude"],
                            "source": f"Wikidata {i}", "url": f"https://www.wikidata.org/wiki/{i}"})
    except Exception as ex:  # Netz/Format
        print(f"[Wikidata nicht erreichbar: {ex}]", file=sys.stderr)
    try:
        q = urllib.parse.urlencode({"q": name, "format": "json", "limit": limit, "accept-language": "de"})
        for r in json.loads(_get("https://nominatim.openstreetmap.org/search?" + q)):
            out.append({"name": r.get("display_name"), "description": f"{r.get('class')}/{r.get('type')}",
                        "lat": float(r["lat"]), "lon": float(r["lon"]), "source": "OSM Nominatim",
                        "url": f"https://www.openstreetmap.org/{r.get('osm_type')}/{r.get('osm_id')}"})
    except Exception as ex:
        print(f"[Nominatim nicht erreichbar: {ex}]", file=sys.stderr)
    return out


# ---------------------------------------------------------------------------
# Höhenmodell (Terrarium-Kacheln)
# ---------------------------------------------------------------------------

TERRARIUM = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"


def _tile_xy(lat, lon, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def fetch_heightmap(lat0, lon0, extent, samples=129, zoom=None):
    from PIL import Image
    if zoom is None:
        # Pixelgröße ≈ extent / 400, max. Zoom 15
        m_per_px0 = 156543.03 * math.cos(math.radians(lat0))
        zoom = max(10, min(15, int(math.log2(m_per_px0 / max(extent / 400, 2)))))
    tiles = {}

    def px(tx, ty):
        key = (int(tx // 256), int(ty // 256))
        if key not in tiles:
            raw = _get(TERRARIUM.format(z=zoom, x=key[0], y=key[1]))
            tiles[key] = Image.open(io.BytesIO(raw)).convert("RGB").load()
        r, g, b = tiles[key][int(tx) % 256, int(ty) % 256]
        return r * 256 + g + b / 256 - 32768

    H = []
    half = extent / 2
    for j in range(samples):
        y = -half + extent * j / (samples - 1)
        row = []
        for i in range(samples):
            x = -half + extent * i / (samples - 1)
            lat, lon = to_latlon(lat0, lon0, x, y)
            fx, fy = _tile_xy(lat, lon, zoom)
            fx, fy = fx * 256, fy * 256
            ix, iy = math.floor(fx - 0.5), math.floor(fy - 0.5)
            tx, ty = fx - 0.5 - ix, fy - 0.5 - iy
            a = px(ix, iy) * (1 - tx) + px(ix + 1, iy) * tx
            b = px(ix, iy + 1) * (1 - tx) + px(ix + 1, iy + 1) * tx
            row.append(round(a * (1 - ty) + b * ty, 2))
        H.append(row)
    return {"extent": extent, "heights": H, "zoom": zoom, "lat": lat0, "lon": lon0,
            "note": "Zeilen von Süd nach Nord, Spalten von West nach Ost; Meter über NN",
            "source": "AWS Terrain Tiles (Terrarium), u. a. SRTM, EU-DEM, nationale DGM"}


# ---------------------------------------------------------------------------
# OpenStreetMap (Overpass)
# ---------------------------------------------------------------------------

OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]


def _simplify(pts, tol=3.0):
    if len(pts) < 3:
        return pts

    def perp(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1e-9
        return abs(dy * p[0] - dx * p[1] + b[0] * a[1] - b[1] * a[0]) / L

    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = perp(pts[i], pts[0], pts[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        return _simplify(pts[:idx + 1], tol)[:-1] + _simplify(pts[idx:], tol)
    return [pts[0], pts[-1]]


def fetch_osm(lat0, lon0, extent):
    half = extent / 2 * 1.05
    s, w = to_latlon(lat0, lon0, -half, -half)
    n, e = to_latlon(lat0, lon0, half, half)
    bbox = f"{s},{w},{n},{e}"
    q = f"""[out:json][timeout:60];
(
  way["waterway"~"river|stream|canal|ditch"]({bbox});
  way["natural"="water"]({bbox});
  rel["natural"="water"]({bbox});
  way["landuse"~"forest|farmland|meadow|vineyard|orchard|village_green"]({bbox});
  way["natural"="wood"]({bbox});
  rel["landuse"="forest"]({bbox});
  rel["natural"="wood"]({bbox});
  way["highway"~"track|path|unclassified|tertiary|secondary|primary|residential|bridleway"]({bbox});
  node["place"~"village|hamlet|town|isolated_dwelling"]({bbox});
  node["historic"]({bbox});
  way["historic"]({bbox});
);
out geom;"""
    last = None
    for url in OVERPASS:
        try:
            data = json.loads(_get(url, urllib.parse.urlencode({"data": q}).encode(), timeout=90))
            break
        except Exception as ex:
            last = ex
    else:
        raise RuntimeError(f"Overpass nicht erreichbar: {last}")

    def loc(geom):
        pts = [to_local(lat0, lon0, g["lat"], g["lon"]) for g in geom]
        return [[round(x, 1), round(y, 1)] for x, y in _simplify(pts)]

    ev = {"sources": ["OSM"], "confidence": "annahme", "note": "heutiger Zustand laut OpenStreetMap – auf Zieldatum prüfen"}
    env = {"rivers": [], "water": [], "forest": [], "fields": [], "roads": [], "hinweise": []}
    for el in data.get("elements", []):
        t = el.get("tags", {})
        geoms = []
        if el["type"] == "way" and "geometry" in el:
            geoms = [el["geometry"]]
        elif el["type"] == "relation":
            geoms = [m["geometry"] for m in el.get("members", []) if m.get("role") == "outer" and "geometry" in m]
        name = t.get("name", "")
        for g in geoms:
            pts = loc(g)
            if len(pts) < 2:
                continue
            if "waterway" in t:
                width = {"river": 14, "canal": 8, "stream": 4, "ditch": 2}.get(t["waterway"], 4)
                env["rivers"].append({"name": name or t["waterway"], "path": pts, "width": width, "depth": 1.5,
                                      "osm": t["waterway"], "evidence": ev})
            elif t.get("natural") == "water" and len(pts) >= 3:
                env["water"].append({"name": name or "Gewässer", "polygon": pts, "evidence": ev})
            elif (t.get("landuse") == "forest" or t.get("natural") == "wood") and len(pts) >= 3:
                env["forest"].append({"kind": {"broadleaved": "laub", "needleleaved": "nadel"}.get(t.get("leaf_type"), "misch"),
                                      "polygon": pts, "density": 0.55, "evidence": ev})
            elif t.get("landuse") in ("farmland", "meadow", "vineyard", "orchard", "village_green") and len(pts) >= 3:
                kind = {"farmland": "acker", "meadow": "wiese", "vineyard": "weinberg", "orchard": "garten",
                        "village_green": "wiese"}[t["landuse"]]
                env["fields"].append({"kind": kind, "polygon": pts, "evidence": ev})
            elif "highway" in t:
                width = {"primary": 7, "secondary": 6, "tertiary": 5}.get(t["highway"], 3.5)
                env["roads"].append({"name": name, "path": pts, "width": width, "osm": t["highway"], "evidence": ev})
            elif "historic" in t:
                env["hinweise"].append({"art": f"historic={t['historic']}", "name": name, "path": pts})
        if el["type"] == "node":
            x, y = to_local(lat0, lon0, el["lat"], el["lon"])
            art = f"place={t['place']}" if "place" in t else f"historic={t.get('historic')}"
            env["hinweise"].append({"art": art, "name": name, "position": [round(x, 1), round(y, 1)]})
    env["_quelle"] = "© OpenStreetMap-Mitwirkende (ODbL) – heutiger Zustand"
    return env


# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("geocode")
    g.add_argument("name")
    t = sub.add_parser("terrain")
    t.add_argument("castle")
    t.add_argument("-o", "--out", default=None)
    t.add_argument("--samples", type=int, default=129)
    t.add_argument("--zoom", type=int)
    o = sub.add_parser("osm")
    o.add_argument("castle")
    o.add_argument("-o", "--out", default=None)
    lc = sub.add_parser("local")
    lc.add_argument("castle")
    lc.add_argument("lat", type=float)
    lc.add_argument("lon", type=float)
    ll = sub.add_parser("latlon")
    ll.add_argument("castle")
    ll.add_argument("x", type=float)
    ll.add_argument("y", type=float)
    a = ap.parse_args(argv)

    if a.cmd == "geocode":
        print(json.dumps(geocode(a.name), ensure_ascii=False, indent=1))
        return
    castle = _load(a.castle)
    lat0, lon0, extent = _site(castle)
    base = os.path.dirname(os.path.abspath(a.castle))
    if a.cmd == "terrain":
        out = a.out or os.path.join(base, "heightmap.json")
        hm = fetch_heightmap(lat0, lon0, extent, a.samples, a.zoom)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(hm, f)
        hs = [v for r in hm["heights"] for v in r]
        print(f"Höhenmodell: {out} (Zoom {hm['zoom']}, {min(hs):.0f}–{max(hs):.0f} m ü. NN)")
        print(f'In castle.json eintragen: "terrain": {{"heightmap": "{os.path.relpath(out, base)}"}}')
    elif a.cmd == "osm":
        out = a.out or os.path.join(base, "osm_umgebung.json")
        env = fetch_osm(lat0, lon0, extent)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(env, f, ensure_ascii=False, indent=1)
        print(f"OSM-Umgebung: {out} · " + ", ".join(f"{k}: {len(v)}" for k, v in env.items() if isinstance(v, list)))
    elif a.cmd == "local":
        x, y = to_local(lat0, lon0, a.lat, a.lon)
        print(json.dumps([round(x, 1), round(y, 1)]))
    elif a.cmd == "latlon":
        print(json.dumps([round(v, 7) for v in to_latlon(lat0, lon0, a.x, a.y)]))


if __name__ == "__main__":
    main()
