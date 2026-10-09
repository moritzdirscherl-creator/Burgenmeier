#!/usr/bin/env python3
"""Werkzeuge für Ruinenpläne: Pixel ablesen, in Meter umrechnen, Ergebnis kontrollieren.

  grid     plan.png -o plan_raster.png [--step 50]
           zeichnet ein beschriftetes Pixelraster über den Plan, damit sich
           Koordinaten von Ecken, Turmmitten usw. genau ablesen lassen.
  convert  kalibrierung.json [-o merkmale_m.json]
           rechnet abgelesene Pixelpunkte in lokale Meter (x Ost, y Nord) um.
  overlay  plan.png kalibrierung.json castle.json -o kontrolle.png
           zeichnet die Elemente aus castle.json zurück auf den Plan –
           so sieht man sofort, ob Maßstab, Nordrichtung und Lage stimmen.

kalibrierung.json:
{
  "image": "plan.png",
  "scale": {"p1": [120, 940], "p2": [520, 940], "meters": 50},   // Maßstabsleiste
  "north_deg": 12,          // Nordpfeil: Grad im Uhrzeigersinn von „Bild-oben“
  "origin_px": [610, 480],  // Pixel, der zum Ursprung (site.lat/lon) wird, meist Burgmitte
  "features": {"ringmauer": [[300, 200], [880, 210]], "bergfried_mitte": [[420, 470]]}
}
"""

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def px_per_m(cal):
    if "px_per_m" in cal:
        return float(cal["px_per_m"])
    s = cal["scale"]
    (x1, y1), (x2, y2) = s["p1"], s["p2"]
    return math.hypot(x2 - x1, y2 - y1) / float(s["meters"])


def px_to_m(cal, px, py):
    k = px_per_m(cal)
    th = math.radians(float(cal.get("north_deg", 0)))
    ox, oy = cal.get("origin_px", [0, 0])
    a, b = (px - ox) / k, -(py - oy) / k   # rechts, oben (Bild)
    return a * math.cos(th) - b * math.sin(th), a * math.sin(th) + b * math.cos(th)


def m_to_px(cal, x, y):
    k = px_per_m(cal)
    th = math.radians(float(cal.get("north_deg", 0)))
    ox, oy = cal.get("origin_px", [0, 0])
    a = x * math.cos(th) + y * math.sin(th)
    b = -x * math.sin(th) + y * math.cos(th)
    return ox + a * k, oy - b * k


def cmd_grid(a):
    from PIL import Image, ImageDraw
    img = Image.open(a.image).convert("RGB")
    W, H = img.size
    step = a.step or max(25, int(round(max(W, H) / 20 / 25)) * 25)
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for x in range(0, W, step):
        major = x % (step * 2) == 0
        d.line([(x, 0), (x, H)], fill=(220, 30, 30, 150 if major else 80), width=1)
        d.text((x + 2, 2), str(x), fill=(200, 0, 0, 255))
        d.text((x + 2, H - 12), str(x), fill=(200, 0, 0, 255))
    for y in range(0, H, step):
        major = y % (step * 2) == 0
        d.line([(0, y), (W, y)], fill=(30, 30, 220, 150 if major else 80), width=1)
        d.text((2, y + 2), str(y), fill=(0, 0, 200, 255))
        d.text((W - 34, y + 2), str(y), fill=(0, 0, 200, 255))
    out = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    dst = a.out or os.path.splitext(a.image)[0] + "_raster.png"
    out.save(dst)
    print(f"Raster ({step} px): {dst}  · Bildgröße {W}×{H} px")


def cmd_convert(a):
    cal = _load(a.calibration)
    res = {"px_per_m": round(px_per_m(cal), 4), "north_deg": cal.get("north_deg", 0), "features": {}}
    for name, pts in cal.get("features", {}).items():
        res["features"][name] = [[round(v, 2) for v in px_to_m(cal, p[0], p[1])] for p in pts]
    txt = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt)
        print("Meterkoordinaten:", a.out)
    else:
        print(txt)


def cmd_overlay(a):
    from PIL import Image, ImageDraw
    import castle_lib as cl
    cal = _load(a.calibration)
    castle = cl.load_castle(a.castle)
    img = Image.open(a.image).convert("RGBA")
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    k = px_per_m(cal)
    colors = {"gesichert": (47, 111, 78), "wahrscheinlich": (110, 150, 40), "analogie": (217, 140, 30),
              "annahme": (200, 60, 50)}
    for el in castle.get("elements", []):
        e = cl.element_defaults(el)
        c = colors[cl.confidence_of(e)]
        if e["type"] in ("wall", "ditch", "bridge"):
            pts = [m_to_px(cal, *p[:2]) for p in e["path"]]
            if e.get("closed"):
                pts.append(pts[0])
            w = float(e.get("thickness", e.get("width", 2)))
            d.line(pts, fill=c + (170 if e["type"] == "wall" else 90,), width=max(2, int(w * k)))
        else:
            poly = [m_to_px(cal, *p) for p in cl._footprint(e)]
            d.polygon(poly, outline=c + (255,), fill=c + (70,))
        lab = e.get("name") or e.get("id")
        if e["type"] in ("wall", "ditch", "bridge"):
            p = e["path"][0]
        else:
            p = cl.centroid(cl._footprint(e))
        x, y = m_to_px(cal, *p[:2])
        d.text((x + 4, y + 4), str(lab), fill=c + (255,))
    ox, oy = cal.get("origin_px", [0, 0])
    d.line([(ox - 8, oy), (ox + 8, oy)], fill=(0, 0, 0, 255), width=2)
    d.line([(ox, oy - 8), (ox, oy + 8)], fill=(0, 0, 0, 255), width=2)
    nx, ny = m_to_px(cal, 0, 30)
    d.line([(ox, oy), (nx, ny)], fill=(0, 0, 0, 255), width=2)
    d.text((nx + 3, ny - 12), "N", fill=(0, 0, 0, 255))
    out = Image.alpha_composite(img, ov).convert("RGB")
    out.save(a.out)
    print("Kontrollbild:", a.out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grid")
    g.add_argument("image")
    g.add_argument("--step", type=int)
    g.add_argument("-o", "--out")
    c = sub.add_parser("convert")
    c.add_argument("calibration")
    c.add_argument("-o", "--out")
    o = sub.add_parser("overlay")
    o.add_argument("image")
    o.add_argument("calibration")
    o.add_argument("castle")
    o.add_argument("-o", "--out", required=True)
    a = ap.parse_args(argv)
    {"grid": cmd_grid, "convert": cmd_convert, "overlay": cmd_overlay}[a.cmd](a)


if __name__ == "__main__":
    main()
