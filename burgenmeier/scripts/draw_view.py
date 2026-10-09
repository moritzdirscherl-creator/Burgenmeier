#!/usr/bin/env python3
"""castle.json -> Zeichnung (SVG, optional PNG) aus einer gewählten Perspektive.

Beispiele:
  python draw_view.py castle.json --view vogelschau -o burg_vogelschau.svg
  python draw_view.py castle.json --view sued --style farbe -o burg_sued.svg --png burg_sued.png
  python draw_view.py castle.json --view grundriss -o burg_plan.svg
  python draw_view.py castle.json --azimuth 200 --elevation 25 --focus alles -o umgebung.svg

Ansichten: vogelschau, nord, ost, sued, west (= Blick VON dieser Seite), grundriss.
Stile: feder (Federzeichnung, Standard), farbe (kolorierte Ansicht), befund
(Färbung nach Quellenlage: gesichert/wahrscheinlich/analogie/annahme).
"""

import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import castle_lib as cl  # noqa: E402

VIEWS = {
    "vogelschau": {"azimuth": 150, "elevation": 32},
    "nord": {"azimuth": 0, "elevation": 9},
    "ost": {"azimuth": 90, "elevation": 9},
    "sued": {"azimuth": 180, "elevation": 9},
    "west": {"azimuth": 270, "elevation": 9},
    "grundriss": {"azimuth": 180, "elevation": 90, "ortho": True},
}

VIEW_TITLES = {
    "vogelschau": "Vogelschau", "nord": "Ansicht von Norden", "ost": "Ansicht von Osten",
    "sued": "Ansicht von Süden", "west": "Ansicht von Westen", "grundriss": "Grundriss",
}

PAPER = (243, 234, 214)
INK = (59, 42, 26)
LIGHT = None  # wird in main normiert


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb2hex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in c)


def mix(a, b, t):
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(3))


def norm(v):
    L = math.sqrt(sum(c * c for c in v)) or 1
    return tuple(c / L for c in v)


class Camera:
    def __init__(self, target, azimuth, elevation, distance, fov=35, ortho=False):
        A = math.radians(azimuth)
        E = math.radians(min(elevation, 89.9))
        d = (math.sin(A) * math.cos(E), math.cos(A) * math.cos(E), math.sin(E))
        self.pos = tuple(target[i] + d[i] * distance for i in range(3))
        self.fwd = tuple(-c for c in d)
        self.right = (-math.cos(A), math.sin(A), 0.0)
        r, f = self.right, self.fwd
        self.up = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
        self.f = 1 / math.tan(math.radians(fov) / 2)
        self.ortho = ortho
        self.dir_to_cam = d

    def project(self, p):
        v = (p[0] - self.pos[0], p[1] - self.pos[1], p[2] - self.pos[2])
        x = v[0] * self.right[0] + v[1] * self.right[1] + v[2] * self.right[2]
        y = v[0] * self.up[0] + v[1] * self.up[1] + v[2] * self.up[2]
        z = v[0] * self.fwd[0] + v[1] * self.fwd[1] + v[2] * self.fwd[2]
        if self.ortho:
            return x, y, z
        if z < 1.0:
            return None
        return x / z * self.f, y / z * self.f, z


def collect(scene, cam, style, show_env=True):
    """Erzeugt die Zeichenliste: (Tiefe, Bildschirmpunkte, Füllung, Strich, Strichart, Schraffur)."""
    items = []
    light = norm((-0.55, 0.6, 0.85))
    paper = PAPER
    feder = style == "feder"
    befund = style == "befund"
    dx = scene["terrain"]["dx"]

    def shade(base_rgb, n, kind):
        lam = max(0.0, n[0] * light[0] + n[1] * light[1] + n[2] * light[2])
        tone = 0.5 + 0.5 * lam
        if feder:
            desat = mix(base_rgb, (sum(base_rgb) / 3,) * 3, 0.55)
            c = mix(paper, desat, 0.5 if kind != "terrain" else 0.42)
            c = mix((70, 55, 40), c, 0.35 + 0.65 * tone)
        else:
            c = tuple(v * (0.45 + 0.55 * tone) for v in base_rgb)
        return c, lam

    def add_poly(pts3, color, kind, conf=None, layer="burg", stroke=True):
        n = cl.face_normal(pts3)
        proj = [cam.project(p) for p in pts3]
        if any(p is None for p in proj):
            return
        area = 0.0
        for i in range(len(proj)):
            x0, y0, _ = proj[i]
            x1, y1, _ = proj[(i + 1) % len(proj)]
            area += x0 * y1 - x1 * y0
        if area <= 0:
            return  # Rückseite
        depth = sum(p[2] for p in proj) / len(proj)
        if not cam.ortho and kind != "terrain":
            depth = depth  # Perspektive: Mittelwert reicht
        if kind == "terrain":
            depth += dx * 0.75
        base = hex2rgb(color)
        if befund and conf and layer == "burg" and kind not in ("water",):
            base = hex2rgb(cl.CONFIDENCE_COLORS[conf])
        fill, lam = shade(base, n, kind)
        dash = None
        if conf in ("analogie",):
            dash = "4 2.5"
        elif conf in ("annahme",):
            dash = "1.2 2"
        if conf in ("analogie", "annahme") and feder and layer == "burg":
            fill = mix(fill, paper, 0.35)
        hatch = None
        if feder:
            if kind == "terrain":
                slope = math.degrees(math.acos(max(-1, min(1, n[2]))))
                if slope > 32:
                    hatch = "h2" if slope > 45 else "h1"
            elif kind != "water" and lam < 0.25:
                hatch = "h1"
        if kind == "terrain":
            s_col, s_w = fill, 0.6
        elif kind == "water":
            s_col, s_w = (mix(fill, INK, 0.3) if feder else fill), 0.4
        else:
            s_col = INK if feder else mix(fill, (20, 15, 10), 0.6)
            s_w = 0.9 if layer == "burg" else 0.5
        items.append((depth, [(p[0], p[1]) for p in proj], fill, s_col, s_w, dash, hatch))

    for tri, col in cl.terrain_triangles(scene["terrain"]):
        add_poly(list(tri), col, "terrain")
    for o in scene["objects"]:
        if o["layer"] != "burg" and not show_env:
            continue
        for part in o["parts"]:
            V = part["vertices"]
            kind = "water" if part["role"] == "water" else o["type"]
            for f in part["faces"]:
                add_poly([V[i] for i in f], part["color"], kind, o["confidence"], o["layer"])
    if show_env:
        add_trees(items, scene, cam, feder, paper)
    items.sort(key=lambda it: -it[0])
    return items


def add_trees(items, scene, cam, feder, paper):
    """Bäume als gezeichnete Signaturen (Billboards) statt Polygonen."""
    rng = random.Random(11)
    for x, y, z, kind, s in scene["trees"]:
        base = cam.project((x, y, z))
        top = cam.project((x, y, z + (10 if kind == "nadel" else 8.5) * s))
        if base is None or top is None:
            continue
        h = math.hypot(top[0] - base[0], top[1] - base[1])
        if h <= 0:
            continue
        # Bildschirm-"oben" für den Baum
        ux, uy = (top[0] - base[0]) / h, (top[1] - base[1]) / h
        r_world = (2.4 if kind == "nadel" else 3.4) * s
        side = cam.project((x + cam.right[0] * r_world, y + cam.right[1] * r_world, z))
        r = abs(side[0] - base[0]) if side else h * 0.35
        col = hex2rgb(scene["tree_colors"][kind])
        if feder:
            col = mix(paper, mix(col, (sum(col) / 3,) * 3, 0.4), 0.55)
        vx, vy = uy, -ux
        if kind == "nadel":
            pts = [(base[0] + ux * h * 0.12 - vx * r, base[1] + uy * h * 0.12 - vy * r),
                   (base[0] + ux * h * 0.12 + vx * r, base[1] + uy * h * 0.12 + vy * r),
                   (base[0] + ux * h, base[1] + uy * h)]
        else:
            cx, cy = base[0] + ux * h * 0.6, base[1] + uy * h * 0.6
            pts = []
            for k in range(9):
                a = 2 * math.pi * k / 9
                rr = r * rng.uniform(0.85, 1.12)
                ry = h * 0.42 * rng.uniform(0.85, 1.1)
                pts.append((cx + vx * math.cos(a) * rr + ux * math.sin(a) * ry,
                            cy + vy * math.cos(a) * rr + uy * math.sin(a) * ry))
        stroke = INK if feder else mix(col, (0, 0, 0), 0.5)
        items.append((base[2] - 0.5, pts, col, stroke, 0.45, None, None))


def fit(items, focus_pts, cam, W, H, margin):
    proj = [cam.project(p) for p in focus_pts]
    proj = [p for p in proj if p]
    xs = [p[0] for p in proj]
    ys = [p[1] for p in proj]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    sc = min((W - 2 * margin) / ((x1 - x0) or 1), (H - 2 * margin) / ((y1 - y0) or 1))
    ox = W / 2 - (x0 + x1) / 2 * sc
    oy = H / 2 + (y0 + y1) / 2 * sc

    def tr(p):
        return (ox + p[0] * sc, oy - p[1] * sc)
    return tr, sc


def contours(scene, interval):
    """Höhenlinien (Marching Squares) als Liniensegmente in Weltkoordinaten."""
    t = scene["terrain"]
    H = t["heights"]
    res, dx, e = t["res"], t["dx"], t["extent"] / 2
    segs = []
    lo = min(min(r) for r in H)
    hi = max(max(r) for r in H)
    lev = math.ceil(lo / interval) * interval
    while lev <= hi:
        for j in range(res):
            for i in range(res):
                c = [(i, j, H[j][i]), (i + 1, j, H[j][i + 1]), (i + 1, j + 1, H[j + 1][i + 1]), (i, j + 1, H[j + 1][i])]
                pts = []
                for k in range(4):
                    a, b = c[k], c[(k + 1) % 4]
                    if (a[2] < lev) != (b[2] < lev):
                        f = (lev - a[2]) / (b[2] - a[2])
                        pts.append((-e + (a[0] + (b[0] - a[0]) * f) * dx, -e + (a[1] + (b[1] - a[1]) * f) * dx))
                if len(pts) >= 2:
                    segs.append((pts[0], pts[1], lev))
                if len(pts) == 4:
                    segs.append((pts[2], pts[3], lev))
        lev += interval
    return segs


def build_drawing(scene, view="vogelschau", style="feder", focus="burg", azimuth=None, elevation=None,
                  width=1600, height=1100, labels=None, show_env=True, fov=35, ortho=None):
    """Erzeugt eine geräteunabhängige Liste von Zeichenprimitiven (für SVG und PNG)."""
    v = dict(VIEWS.get(view, VIEWS["vogelschau"]))
    custom = azimuth is not None or elevation is not None
    if azimuth is not None:
        v["azimuth"] = azimuth
    if elevation is not None:
        v["elevation"] = elevation
    is_plan = v.get("elevation", 30) >= 89.9
    ortho = v.get("ortho", False) if ortho is None else ortho
    bb = scene["castle_bbox"]
    e = scene["terrain"]["extent"] / 2
    if focus == "alles":
        focus_pts = [(sx * e, sy * e, 0) for sx in (-1, 1) for sy in (-1, 1)]
        target = (0, 0, 0)
        radius = e * 1.4
    else:
        pad = 25 if focus == "burg" else float(focus)
        focus_pts = [(x, y, z) for x in (bb[0][0] - pad, bb[1][0] + pad)
                     for y in (bb[0][1] - pad, bb[1][1] + pad) for z in (bb[0][2] + 10, bb[1][2])]
        target = tuple((bb[0][i] + bb[1][i]) / 2 for i in range(3))
        radius = max(bb[1][0] - bb[0][0], bb[1][1] - bb[0][1]) / 2 + pad
    dist = radius / math.tan(math.radians(fov) / 2) * 1.6
    cam = Camera(target, v["azimuth"], v["elevation"], dist, fov, ortho)
    items = collect(scene, cam, style, show_env)
    if labels is None:
        labels = focus != "alles"
    margin, cartouche = 60, 90
    tr, sc = fit(items, focus_pts, cam, width, height - cartouche, margin)

    feder = style == "feder"
    paper = PAPER if feder else (244, 241, 234)
    frame = (20, 20, width - 40, height - cartouche - 30)
    P = {"size": (width, height), "paper": paper, "frame": frame, "clipped": [], "overlay": []}
    clipped, over = P["clipped"], P["overlay"]
    for depth, pts, fill, stroke, sw, dash, hatch in items:
        sp = [tr(p) for p in pts]
        if all(x < 0 or x > width for x, _ in sp) or all(y < 0 or y > height for _, y in sp):
            continue
        clipped.append(("poly", sp, fill, stroke, sw, dash, hatch))

    if is_plan:
        for (a, b, lev) in contours(scene, 5):
            p0, p1 = tr(cam.project((a[0], a[1], 0))), tr(cam.project((b[0], b[1], 0)))
            major = abs(lev % 25) < 1e-6
            clipped.append(("line", p0, p1, INK, 0.9 if major else 0.5, 0.55 if major else 0.25))

    if labels:
        for o in scene["objects"]:
            # Mauern, Gräben und Brücken haben keinen sinnvollen Mittelpunkt -> nur Baukörper beschriften
            if o["layer"] != "burg" or o["type"] not in ("tower", "building", "gate"):
                continue
            V = [vv for p in o["parts"] for vv in p["vertices"]]
            if not V:
                continue
            cx = sum(p[0] for p in V) / len(V)
            cy = sum(p[1] for p in V) / len(V)
            cz = max(p[2] for p in V)
            p = cam.project((cx, cy, cz + 3))
            if p:
                x, y = tr(p)
                clipped.append(("text", x, y, o["name"], 15, "middle", True, True))

    over.append(("rect", frame, None, INK, 1.6, None))
    meta = scene["meta"]
    sub = VIEW_TITLES.get(view, "") if not custom else ""
    if not sub:
        sub = f"Ansicht von Azimut {v['azimuth']:g}°, Höhenwinkel {v['elevation']:g}°"
    if meta.get("date"):
        sub += f" · Rekonstruktionsversuch, Zustand um {meta['date']}"
    yb = height - cartouche + 18
    over.append(("text", 30, yb + 22, meta.get("name", "Burg"), 28, "start", False, False))
    over.append(("text", 30, yb + 50, sub, 17, "start", True, False))
    lx = width - 600
    for x_off, (lab, dash, conf) in zip((0, 290, 440), [("gesichert / wahrscheinlich", None, "gesichert"),
                                                        ("Analogie", "4 2.5", "analogie"), ("Annahme", "1.2 2", "annahme")]):
        x = lx + x_off
        fill = hex2rgb(cl.CONFIDENCE_COLORS[conf]) if style == "befund" else None
        over.append(("rect", (x, yb + 8, 26, 14), fill, INK, 1.2, dash))
        over.append(("text", x + 34, yb + 20, lab, 13, "start", False, False))
    if is_plan or ortho:
        m = 50.0
        while sc * m > 420:
            m /= 2
        while sc * m < 120:
            m *= 2
        x0 = width - 600
        over.append(("line", (x0, yb + 50), (x0 + sc * m, yb + 50), INK, 3, 1.0))
        for k in range(1, 5):
            xx = x0 + sc * m * k / 5
            over.append(("line", (xx, yb + 46), (xx, yb + 54), INK, 1, 1.0))
        over.append(("text", x0 + sc * m + 8, yb + 55, f"{m:g} m", 13, "start", False, False))
        if is_plan:
            over.append(("text", x0 - 20, yb + 55, "Höhenlinien 5 m", 13, "end", False, False))
    if is_plan:
        nx, ny = width - 70, yb - 120
        over.append(("poly", [(nx, ny - 30), (nx - 10, ny + 10), (nx, ny + 2), (nx + 10, ny + 10)], INK, INK, 0.5, None, None))
        over.append(("text", nx, ny - 36, "N", 16, "middle", False, False))
    return P


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_svg(P):
    W, H = P["size"]
    ink = rgb2hex(INK)
    paper = rgb2hex(P["paper"])
    fx, fy, fw, fh = P["frame"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'font-family="Georgia, \'Times New Roman\', serif">', "<defs>",
           f'<pattern id="h1" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">'
           f'<line x1="0" y1="0" x2="0" y2="5" stroke="{ink}" stroke-width="0.6" stroke-opacity="0.55"/></pattern>',
           f'<pattern id="h2" width="3.5" height="3.5" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">'
           f'<line x1="0" y1="0" x2="0" y2="3.5" stroke="{ink}" stroke-width="0.7" stroke-opacity="0.7"/></pattern>',
           f'<clipPath id="frame"><rect x="{fx}" y="{fy}" width="{fw}" height="{fh}"/></clipPath>', "</defs>",
           f'<rect width="{W}" height="{H}" fill="{paper}"/>']

    def emit(prim):
        kind = prim[0]
        if kind == "poly":
            _, sp, fill, stroke, sw, dash, hatch = prim
            d = " ".join(f"{x:.1f},{y:.1f}" for x, y in sp)
            attr = f'fill="{rgb2hex(fill)}" stroke="{rgb2hex(stroke)}" stroke-width="{sw}" stroke-linejoin="round"'
            if dash:
                attr += f' stroke-dasharray="{dash}"'
            out.append(f'<polygon points="{d}" {attr}/>')
            if hatch:
                out.append(f'<polygon points="{d}" fill="url(#{hatch})" stroke="none"/>')
        elif kind == "line":
            _, (x0, y0), (x1, y1), col, w, op = prim
            out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{rgb2hex(col)}" '
                       f'stroke-width="{w}" stroke-opacity="{op}"/>')
        elif kind == "text":
            _, x, y, txt, size, anchor, italic, halo = prim
            st = ' font-style="italic"' if italic else ""
            if halo:
                st += f' stroke="{paper}" stroke-width="3" paint-order="stroke"'
            out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{ink}"{st}>'
                       f'{_esc(txt)}</text>')
        elif kind == "rect":
            _, (x, y, w, h), fill, stroke, sw, dash = prim
            da = f' stroke-dasharray="{dash}"' if dash else ""
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{rgb2hex(fill) if fill else "none"}" '
                       f'stroke="{rgb2hex(stroke)}" stroke-width="{sw}"{da}/>')

    out.append('<g clip-path="url(#frame)">')
    for prim in P["clipped"]:
        emit(prim)
    out.append("</g>")
    for prim in P["overlay"]:
        emit(prim)
    out.append("</svg>")
    return "\n".join(out)


def _font(size, italic=False):
    from PIL import ImageFont
    names = (["DejaVuSerif-Italic.ttf", "LiberationSerif-Italic.ttf", "FreeSerifItalic.ttf"] if italic else []) + \
            ["DejaVuSerif.ttf", "LiberationSerif-Regular.ttf", "FreeSerif.ttf", "DejaVuSans.ttf"]
    dirs = ["", "/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/truetype/liberation/",
            "/usr/share/fonts/truetype/freefont/", "/usr/share/fonts/TTF/", "/Library/Fonts/", "C:/Windows/Fonts/"]
    for n in names:
        for d in dirs:
            try:
                return ImageFont.truetype(d + n, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def to_png(P, path, scale=1.5):
    """PNG ohne externe Abhängigkeiten außer Pillow (inkl. Schraffur und Beschriftung)."""
    from PIL import Image, ImageDraw
    W, H = P["size"]
    ss = scale * 2  # Supersampling
    img = Image.new("RGB", (int(W * ss), int(H * ss)), tuple(P["paper"]))
    dr = ImageDraw.Draw(img)
    hatch_tiles = {}

    def hatch_img(kind, w, h):
        step = (5 if kind == "h1" else 3.5) * ss
        key = (kind, w, h)
        if key not in hatch_tiles:
            t = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            td = ImageDraw.Draw(t)
            alpha = 140 if kind == "h1" else 180
            k = -h
            while k < w + h:
                td.line([(k, 0), (k + h * math.tan(math.radians(35)), h)], fill=INK + (alpha,), width=max(1, int(ss * 0.6)))
                k += step / math.cos(math.radians(35))
            hatch_tiles[key] = t
        return hatch_tiles[key]

    def dashed(pts, col, w, dash):
        on, off = [float(v) * ss for v in dash.split()]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            L = math.hypot(x1 - x0, y1 - y0)
            t = 0.0
            while t < L:
                t1 = min(L, t + on)
                dr.line([(x0 + (x1 - x0) * t / L, y0 + (y1 - y0) * t / L),
                         (x0 + (x1 - x0) * t1 / L, y0 + (y1 - y0) * t1 / L)], fill=col, width=w)
                t = t1 + off

    def emit(prim):
        kind = prim[0]
        if kind == "poly":
            _, sp, fill, stroke, sw, dash, hatch = prim
            p = [(x * ss, y * ss) for x, y in sp]
            dr.polygon(p, fill=tuple(int(c) for c in fill))
            if hatch:
                xs = [q[0] for q in p]
                ys = [q[1] for q in p]
                x0, y0 = int(max(0, min(xs))), int(max(0, min(ys)))
                x1, y1 = int(min(img.width, max(xs) + 1)), int(min(img.height, max(ys) + 1))
                if x1 > x0 and y1 > y0:
                    mask = Image.new("L", (x1 - x0, y1 - y0), 0)
                    ImageDraw.Draw(mask).polygon([(q[0] - x0, q[1] - y0) for q in p], fill=255)
                    tile = hatch_img(hatch, 256, 256)
                    big = Image.new("RGBA", (x1 - x0, y1 - y0))
                    for tx in range(-(x0 % 256), x1 - x0, 256):
                        for ty in range(-(y0 % 256), y1 - y0, 256):
                            big.paste(tile, (tx, ty))
                    a = Image.composite(big, Image.new("RGBA", big.size, (0, 0, 0, 0)), mask)
                    img.paste(a, (x0, y0), a)
            if stroke is not None and sw >= 0.4 and tuple(stroke) != tuple(fill):
                w = max(1, int(round(sw * ss * 0.8)))
                col = tuple(int(c) for c in stroke)
                if dash:
                    dashed(p + [p[0]], col, w, dash)
                else:
                    dr.line(p + [p[0]], fill=col, width=w, joint="curve")
        elif kind == "line":
            _, (x0, y0), (x1, y1), col, w, op = prim
            c = tuple(int(P["paper"][i] * (1 - op) + col[i] * op) for i in range(3))
            dr.line([(x0 * ss, y0 * ss), (x1 * ss, y1 * ss)], fill=c, width=max(1, int(w * ss)))
        elif kind == "text":
            _, x, y, txt, size, anchor, italic, halo = prim
            f = _font(int(size * ss), italic)
            anc = {"middle": "ms", "start": "ls", "end": "rs"}[anchor]
            kw = {"stroke_width": int(3 * ss / 2), "stroke_fill": tuple(P["paper"])} if halo else {}
            dr.text((x * ss, y * ss), str(txt), font=f, fill=INK, anchor=anc, **kw)
        elif kind == "rect":
            _, (x, y, w, h), fill, stroke, sw, dash = prim
            box = [(x * ss, y * ss), ((x + w) * ss, y * ss), ((x + w) * ss, (y + h) * ss), (x * ss, (y + h) * ss)]
            if fill:
                dr.polygon(box, fill=tuple(fill))
            lw = max(1, int(sw * ss))
            if dash:
                dashed(box + [box[0]], INK, lw, dash)
            else:
                dr.line(box + [box[0]], fill=tuple(stroke), width=lw)

    for prim in P["clipped"]:
        emit(prim)
    fx, fy, fw, fh = [v * ss for v in P["frame"]]
    pc = tuple(P["paper"])
    dr.rectangle([0, 0, img.width, fy], fill=pc)
    dr.rectangle([0, fy + fh, img.width, img.height], fill=pc)
    dr.rectangle([0, 0, fx, img.height], fill=pc)
    dr.rectangle([fx + fw, 0, img.width, img.height], fill=pc)
    for prim in P["overlay"]:
        emit(prim)
    img = img.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    img.save(path)
    return path


def render_svg(scene, *args, **kw):
    """Kompatibilität: SVG-Text direkt erzeugen."""
    return to_svg(build_drawing(scene, *args, **kw))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("castle")
    ap.add_argument("--view", default="vogelschau", choices=list(VIEWS))
    ap.add_argument("--style", default="feder", choices=["feder", "farbe", "befund"])
    ap.add_argument("--focus", default="burg", help="burg | alles | Rand in Metern um die Burg (z. B. 150)")
    ap.add_argument("--azimuth", type=float, help="Blick VON dieser Kompassrichtung (0=N, 90=O)")
    ap.add_argument("--elevation", type=float, help="Höhenwinkel der Kamera in Grad (90 = senkrecht)")
    ap.add_argument("--fov", type=float, default=35)
    ap.add_argument("--ortho", action="store_true", help="Parallelprojektion (maßstäblich)")
    ap.add_argument("--no-labels", action="store_true")
    ap.add_argument("--labels", action="store_true", help="Beschriftung auch bei --focus alles")
    ap.add_argument("--no-env", action="store_true", help="nur die Burg, ohne Umgebung")
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=1100)
    ap.add_argument("-o", "--out", default=None, help="SVG-Datei")
    ap.add_argument("--png", default=None, help="PNG-Datei (zusätzlich oder statt SVG)")
    a = ap.parse_args(argv)

    scene = cl.build_scene(cl.load_castle(a.castle))
    labels = False if a.no_labels else (True if a.labels else None)
    P = build_drawing(scene, a.view, a.style, a.focus, a.azimuth, a.elevation, a.width, a.height,
                      labels, not a.no_env, a.fov, True if a.ortho else None)
    if a.out or not a.png:
        out = a.out or os.path.splitext(a.castle)[0] + f"_{a.view}.svg"
        with open(out, "w", encoding="utf-8") as f:
            f.write(to_svg(P))
        print(f"SVG: {out}")
    if a.png:
        to_png(P, a.png)
        print(f"PNG: {a.png}")


if __name__ == "__main__":
    main()
