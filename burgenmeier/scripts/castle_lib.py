"""Burgenmeier-Kernbibliothek: castle.json -> Szene (Gelände + Low-Poly-Objekte).

Koordinaten: lokale Meter, x = Ost, y = Nord, z = oben. Ursprung = site.lat/lon
(in der Regel die Burgmitte). Gelände-z ist so normiert, dass z(0, 0) = 0.

Die Szene ist ein reines dict und wird von build_model.py (GLB/OBJ/Viewer)
und draw_view.py (SVG/PNG-Zeichnung) gleichermaßen verwendet, damit 3D-Modell
und Zeichnung exakt dieselbe Geometrie zeigen.
"""

import json
import math
import os
import random

import numpy as np

CONFIDENCE_LEVELS = ["gesichert", "wahrscheinlich", "analogie", "annahme"]

CONFIDENCE_COLORS = {
    "gesichert": "#2f6f4e",
    "wahrscheinlich": "#8aa84a",
    "analogie": "#d9a43a",
    "annahme": "#c8553d",
}

MATERIALS = {
    "stone": "#b8ab95",
    "stone_dark": "#8c8274",
    "sandstone": "#c9a27a",
    "red_sandstone": "#a8644e",
    "brick": "#a45a3f",
    "plaster": "#e6dcc6",
    "timber": "#d8ccb0",
    "wood": "#8a6a45",
    "slate": "#4f565f",
    "tile": "#a4533a",
    "shingle": "#6e5a45",
    "thatch": "#b49a5c",
    "lead": "#7d8790",
    "dark": "#2a2420",
    "water": "#6f8fa3",
}

TERRAIN_COLORS = {
    "wiese": "#8fa06a",
    "weide": "#9aa871",
    "wald": "#5f7448",
    "acker1": "#c8b77a",
    "acker2": "#a9a25e",
    "acker3": "#b9a06a",
    "weinberg": "#7f8a4c",
    "garten": "#7d9a58",
    "weg": "#b9a58a",
    "siedlung": "#a8987c",
    "hof": "#b5a68a",
    "graben": "#7d8c5a",
    "fels": "#9a9488",
    "wasser": "#6f8fa3",
}

TREE_COLORS = {"laub": "#5a7a3a", "nadel": "#3f5a3a", "stamm": "#5a4330"}

ELEMENT_TYPES = ["wall", "tower", "building", "gate", "ditch", "bridge"]

ROOF_TYPES = ["gable", "hip", "shed", "pyramid", "cone", "flat", "crenellated", "none"]

DEFAULTS = {
    "wall": {"thickness": 2.0, "height": 8.0, "crenellated": True, "material": "stone"},
    "tower": {"shape": "round", "radius": 5.0, "height": 20.0, "roof": "cone",
              "material": "stone", "roof_material": "slate"},
    "building": {"height": 10.0, "roof": "gable", "material": "stone", "roof_material": "tile"},
    "gate": {"size": [8.0, 10.0], "height": 12.0, "roof": "hip",
             "material": "stone", "roof_material": "slate"},
    "ditch": {"width": 12.0, "depth": 6.0, "water": False},
    "bridge": {"width": 3.0, "material": "wood"},
}


# ---------------------------------------------------------------------------
# Laden
# ---------------------------------------------------------------------------

def load_castle(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("_base_dir", os.path.dirname(os.path.abspath(path)))
    return data


def element_defaults(el):
    out = dict(DEFAULTS.get(el.get("type"), {}))
    out.update(el)
    out.setdefault("layer", "burg")
    out.setdefault("evidence", {})
    return out


def confidence_of(obj):
    c = (obj.get("evidence") or {}).get("confidence", "annahme")
    return c if c in CONFIDENCE_LEVELS else "annahme"


# ---------------------------------------------------------------------------
# 2D-Geometrie
# ---------------------------------------------------------------------------

def poly_area(poly):
    a = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i][:2]
        x1, y1 = poly[(i + 1) % n][:2]
        a += x0 * y1 - x1 * y0
    return a / 2.0


def ensure_ccw(poly):
    poly = [tuple(p[:2]) for p in poly]
    if len(poly) > 1 and poly[0] == poly[-1]:
        poly = poly[:-1]
    return poly if poly_area(poly) >= 0 else poly[::-1]


def centroid(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i][:2]
        xj, yj = poly[j][:2]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def points_in_poly(X, Y, poly):
    """Vektorisierter Punkt-in-Polygon-Test über numpy-Arrays."""
    inside = np.zeros(X.shape, dtype=bool)
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i][:2]
        xj, yj = poly[j][:2]
        cond = (yi > Y) != (yj > Y)
        xint = (xj - xi) * (Y - yi) / ((yj - yi) if yj != yi else 1e-12) + xi
        inside ^= cond & (X < xint)
        j = i
    return inside


def dist_to_path(X, Y, path, closed=False):
    """Abstand jedes Punkts zur Polylinie; zusätzlich Segmentindex und Parameter t."""
    pts = [tuple(p[:2]) for p in path]
    if closed:
        pts = pts + [pts[0]]
    best = np.full(X.shape, np.inf)
    seg = np.zeros(X.shape, dtype=int)
    tpar = np.zeros(X.shape)
    for k in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[k], pts[k + 1]
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy or 1e-12
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0, 1)
        d = np.hypot(X - (x0 + t * dx), Y - (y0 + t * dy))
        m = d < best
        best = np.where(m, d, best)
        seg = np.where(m, k, seg)
        tpar = np.where(m, t, tpar)
    return best, seg, tpar


def triangulate(poly):
    """Ear-Clipping für einfache Polygone (CCW). Gibt Indextripel zurück."""
    n = len(poly)
    if n < 3:
        return []
    if n == 3:
        return [(0, 1, 2)]
    idx = list(range(n))
    if poly_area(poly) < 0:
        idx.reverse()
    tris = []

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def in_tri(p, a, b, c):
        return cross(a, b, p) >= 0 and cross(b, c, p) >= 0 and cross(c, a, p) >= 0

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        found = False
        m = len(idx)
        for k in range(m):
            i0, i1, i2 = idx[(k - 1) % m], idx[k], idx[(k + 1) % m]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if cross(a, b, c) <= 1e-9:
                continue
            if any(in_tri(poly[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            found = True
            break
        if not found:  # degeneriert: Fächer als Notlösung
            for k in range(1, len(idx) - 1):
                tris.append((idx[0], idx[k], idx[k + 1]))
            return tris
    tris.append(tuple(idx))
    return tris


def main_axis(poly):
    """Richtung (Einheitsvektor) der längsten Polygonkante."""
    best, d = -1, (1.0, 0.0)
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0)
        if L > best:
            best, d = L, ((x1 - x0) / (L or 1), (y1 - y0) / (L or 1))
    return d


def compass_to_vec(deg):
    """Kompassrichtung (0 = Nord, 90 = Ost) -> Einheitsvektor (x, y)."""
    r = math.radians(deg)
    return (math.sin(r), math.cos(r))


def rect_poly(center, size, orientation=0.0):
    """Rechteck um center, size = [Länge, Breite]; Länge zeigt in Kompassrichtung orientation."""
    cx, cy = center
    L, W = size
    ux, uy = compass_to_vec(orientation)
    vx, vy = uy, -ux  # rechtwinklig
    hl, hw = L / 2, W / 2
    pts = [(cx - ux * hl - vx * hw, cy - uy * hl - vy * hw),
           (cx + ux * hl - vx * hw, cy + uy * hl - vy * hw),
           (cx + ux * hl + vx * hw, cy + uy * hl + vy * hw),
           (cx - ux * hl + vx * hw, cy - uy * hl + vy * hw)]
    return ensure_ccw(pts)


def circle_poly(center, r, n=12):
    cx, cy = center
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n))
            for k in range(n)]


# ---------------------------------------------------------------------------
# Gelände
# ---------------------------------------------------------------------------

def _value_noise(X, Y, scale, seed):
    rng = np.random.default_rng(seed)
    g = rng.random((64, 64))
    u = X / scale + 17.3
    v = Y / scale + 31.7
    i0 = np.floor(u).astype(int)
    j0 = np.floor(v).astype(int)
    fu = u - i0
    fv = v - j0
    fu = fu * fu * (3 - 2 * fu)
    fv = fv * fv * (3 - 2 * fv)
    i0 %= 64
    j0 %= 64
    i1 = (i0 + 1) % 64
    j1 = (j0 + 1) % 64
    a = g[j0, i0] * (1 - fu) + g[j0, i1] * fu
    b = g[j1, i0] * (1 - fu) + g[j1, i1] * fu
    return (a * (1 - fv) + b * fv) * 2 - 1


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


class Terrain:
    def __init__(self, extent, resolution):
        self.extent = float(extent)
        self.res = int(resolution)
        self.n = self.res + 1
        self.xs = np.linspace(-extent / 2, extent / 2, self.n)
        self.ys = np.linspace(-extent / 2, extent / 2, self.n)
        self.X, self.Y = np.meshgrid(self.xs, self.ys)  # [j (y), i (x)]
        self.h = np.zeros_like(self.X)
        self.dx = self.extent / self.res
        cx = (self.xs[:-1] + self.xs[1:]) / 2
        cy = (self.ys[:-1] + self.ys[1:]) / 2
        self.CX, self.CY = np.meshgrid(cx, cy)
        self.kind = np.full(self.CX.shape, "wiese", dtype=object)

    def sample(self, x, y):
        fx = (x + self.extent / 2) / self.dx
        fy = (y + self.extent / 2) / self.dx
        fx = min(max(fx, 0), self.res - 1e-6)
        fy = min(max(fy, 0), self.res - 1e-6)
        i, j = int(fx), int(fy)
        tx, ty = fx - i, fy - j
        h = self.h
        a = h[j, i] * (1 - tx) + h[j, i + 1] * tx
        b = h[j + 1, i] * (1 - tx) + h[j + 1, i + 1] * tx
        return float(a * (1 - ty) + b * ty)

    def sample_many(self, pts):
        return [self.sample(p[0], p[1]) for p in pts]

    def cell_heights(self):
        h = self.h
        return (h[:-1, :-1] + h[:-1, 1:] + h[1:, :-1] + h[1:, 1:]) / 4


def _procedural_heights(T, spec):
    kind = spec.get("type", "hilltop")
    R = float(spec.get("relief", 60))
    E = T.extent
    X, Y = T.X, T.Y
    ux, uy = compass_to_vec(float(spec.get("direction", 90)))
    u = X * ux + Y * uy     # entlang Spornrichtung
    v = -X * uy + Y * ux    # quer dazu
    r = np.hypot(X, Y)
    pr = float(spec.get("plateau_radius", 40))
    if kind in ("hilltop", "gipfel"):
        L = max(E * 0.28, pr * 2.2)
        h = R * np.exp(-((r / L) ** 2)) + R * 0.35 * _smoothstep(E * 0.3, E * 0.55, r)
    elif kind in ("crag", "fels"):
        L = max(E * 0.16, pr * 1.6)
        h = R * np.exp(-((r / L) ** 2.6))
    elif kind in ("spur", "sporn"):
        w = max(E * 0.12, pr * 1.6)
        cross_p = np.exp(-((v / w) ** 2))
        along = np.where(u < 0, 1.0 + 0.35 * (-u / E), np.exp(-((u / (w * 0.9)) ** 2)))
        h = R * cross_p * along
        h = np.maximum(h, R * 0.35 * np.clip(-u / E, 0, 1) * 2)  # Bergrücken dahinter
        h = h + R * 0.7 * _smoothstep(E * 0.22, E * 0.5, np.abs(v))  # gegenüberliegende Talflanken
    elif kind in ("slope", "hang"):
        h = R * (0.5 - u / E)
    elif kind in ("lowland", "niederung", "island", "insel", "plain", "ebene"):
        h = np.zeros_like(X)
    else:
        raise ValueError(f"Unbekannter Geländetyp: {kind}")
    rough = float(spec.get("roughness", 0.3))
    seed = int(spec.get("seed", 7))
    amp = max(R, 6) * 0.12 * rough
    h = h + amp * _value_noise(X, Y, E / 6, seed) + amp * 0.4 * _value_noise(X, Y, E / 18, seed + 1)
    return h


def _heightmap_heights(T, hm):
    H = np.array(hm["heights"], dtype=float)
    ext = float(hm["extent"])
    n_rows, n_cols = H.shape
    fx = (T.X + ext / 2) / ext * (n_cols - 1)
    fy = (T.Y + ext / 2) / ext * (n_rows - 1)
    fx = np.clip(fx, 0, n_cols - 1 - 1e-6)
    fy = np.clip(fy, 0, n_rows - 1 - 1e-6)
    i = fx.astype(int)
    j = fy.astype(int)
    tx, ty = fx - i, fy - j
    a = H[j, i] * (1 - tx) + H[j, i + 1] * tx
    b = H[j + 1, i] * (1 - tx) + H[j + 1, i + 1] * tx
    return a * (1 - ty) + b * ty


def build_terrain(castle):
    site = castle.get("site", {})
    spec = dict(site.get("terrain", {}))
    extent = float(site.get("extent", 700))
    res = int(site.get("resolution", 70))
    T = Terrain(extent, res)
    hm_path = spec.get("heightmap")
    if hm_path:
        if not os.path.isabs(hm_path):
            hm_path = os.path.join(castle.get("_base_dir", "."), hm_path)
        with open(hm_path, encoding="utf-8") as f:
            T.h = _heightmap_heights(T, json.load(f))
    else:
        T.h = _procedural_heights(T, spec)
    T.h = T.h - T.sample(0, 0)
    T.h0 = T.h.copy()  # ursprüngliches Gelände (vor Graben/Plateau)

    # Burgplateau einebnen
    plateau = site.get("plateau")
    if plateau is not None or spec.get("plateau_radius"):
        if plateau and plateau.get("polygon"):
            poly = ensure_ccw(plateau["polygon"])
        else:
            poly = circle_poly((0, 0), float(spec.get("plateau_radius", 40)), 16)
        inside = points_in_poly(T.X, T.Y, poly)
        H = (plateau or {}).get("height")
        if H is None:
            H = float(np.mean(T.h[inside])) if inside.any() else 0.0
        d, _, _ = dist_to_path(T.X, T.Y, poly, closed=True)
        blend = 8.0
        w = np.where(inside, 1.0, 1.0 - _smoothstep(0, blend, d))
        T.h = T.h * (1 - w) + H * w
        T.plateau_poly = poly
        T.plateau_h = H
        cin = points_in_poly(T.CX, T.CY, poly)
        T.kind[cin] = "hof"
    else:
        T.plateau_poly = None
    return T


# ---------------------------------------------------------------------------
# Mesh-Bausteine
# ---------------------------------------------------------------------------

class Part:
    """Ein einfarbiges Teil-Mesh mit Polygonflächen (CCW von außen gesehen)."""

    def __init__(self, color, role="wall"):
        self.color = color
        self.role = role
        self.v = []
        self.f = []

    def add_v(self, x, y, z):
        self.v.append((float(x), float(y), float(z)))
        return len(self.v) - 1

    def add_f(self, idx):
        self.f.append(list(idx))

    def empty(self):
        return not self.f

    def to_dict(self):
        return {"color": self.color, "role": self.role,
                "vertices": [[round(c, 2) for c in p] for p in self.v],
                "faces": self.f}


def add_prism(part, poly, z0, z1, top=True, bottom=False):
    poly = ensure_ccw(poly)
    n = len(poly)
    b = [part.add_v(x, y, z0) for x, y in poly]
    t = [part.add_v(x, y, z1) for x, y in poly]
    for i in range(n):
        k = (i + 1) % n
        part.add_f([b[i], b[k], t[k], t[i]])
    if top:
        part.add_f(t)
    if bottom:
        part.add_f(b[::-1])
    return t


def seg_rect(p0, p1, thickness, ext=0.0):
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0) or 1e-6
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = -uy * thickness / 2, ux * thickness / 2
    x0, y0 = x0 - ux * ext, y0 - uy * ext
    x1, y1 = x1 + ux * ext, y1 + uy * ext
    return ensure_ccw([(x0 - nx, y0 - ny), (x1 - nx, y1 - ny), (x1 + nx, y1 + ny), (x0 + nx, y0 + ny)])


def add_merlons(part, p0, p1, thickness, z, mw=1.0, gap=1.0, mh=1.3):
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0)
    if L < mw:
        return
    k = int((L + gap) // (mw + gap))
    if k < 1:
        return
    used = k * mw + (k - 1) * gap
    start = (L - used) / 2
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    for m in range(k):
        a = start + m * (mw + gap)
        q0 = (x0 + ux * a, y0 + uy * a)
        q1 = (x0 + ux * (a + mw), y0 + uy * (a + mw))
        add_prism(part, seg_rect(q0, q1, thickness), z, z + mh)


def add_parapet_ring(part, poly, z, thickness=0.7):
    """Zinnenkranz innen entlang des Polygonrands."""
    poly = ensure_ccw(poly)
    n = len(poly)
    cx, cy = centroid(poly)
    for i in range(n):
        p0, p1 = poly[i], poly[(i + 1) % n]
        # um halbe Stärke nach innen versetzen
        q = []
        for (x, y) in (p0, p1):
            dx, dy = cx - x, cy - y
            d = math.hypot(dx, dy) or 1
            q.append((x + dx / d * thickness / 2, y + dy / d * thickness / 2))
        add_merlons(part, q[0], q[1], thickness, z)


def _roof_frame(poly, ridge_dir=None):
    if ridge_dir is not None:
        ux, uy = compass_to_vec(float(ridge_dir))
    else:
        ux, uy = main_axis(poly)
    vx, vy = -uy, ux
    us = [x * ux + y * uy for x, y in poly]
    vs = [x * vx + y * vy for x, y in poly]
    return (ux, uy), (vx, vy), (min(us), max(us), min(vs), max(vs))


def add_roof(part, poly, z, kind, height=None, ridge_dir=None, overhang=0.4):
    poly = ensure_ccw(poly)
    if kind in ("flat", "none", None):
        return
    if kind in ("pyramid", "cone"):
        cx, cy = centroid(poly)
        if height is None:
            r = max(math.hypot(x - cx, y - cy) for x, y in poly)
            height = r * (2.2 if kind == "cone" else 1.4)
        ring = []
        for x, y in poly:
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy) or 1
            ring.append((x + dx / d * overhang, y + dy / d * overhang))
        idx = [part.add_v(x, y, z) for x, y in ring]
        apex = part.add_v(cx, cy, z + height)
        n = len(ring)
        for i in range(n):
            part.add_f([idx[i], idx[(i + 1) % n], apex])
        part.add_f(idx[::-1])
        return
    (ux, uy), (vx, vy), (u0, u1, v0, v1) = _roof_frame(poly, ridge_dir)
    u0 -= overhang
    u1 += overhang
    v0 -= overhang
    v1 += overhang
    width = v1 - v0
    if height is None:
        height = width / 2 * (1.2 if kind != "shed" else 0.5)

    def P(u, v, zz):
        return part.add_v(u * ux + v * vx, u * uy + v * vy, zz)

    A, B, C, D = P(u0, v0, z), P(u1, v0, z), P(u1, v1, z), P(u0, v1, z)
    vc = (v0 + v1) / 2
    if kind == "gable":
        R1, R2 = P(u0, vc, z + height), P(u1, vc, z + height)
        part.add_f([A, B, R2, R1])
        part.add_f([C, D, R1, R2])
        part.add_f([D, A, R1])
        part.add_f([B, C, R2])
    elif kind == "hip":
        inset = min(width / 2, (u1 - u0) / 2 - 0.01)
        R1, R2 = P(u0 + inset, vc, z + height), P(u1 - inset, vc, z + height)
        part.add_f([A, B, R2, R1])
        part.add_f([C, D, R1, R2])
        part.add_f([D, A, R1])
        part.add_f([B, C, R2])
    elif kind == "shed":
        Ct, Dt = P(u1, v1, z + height), P(u0, v1, z + height)
        part.add_f([A, B, Ct, Dt])
        part.add_f([C, D, Dt, Ct])
        part.add_f([D, A, Dt])
        part.add_f([B, C, Ct])
    else:
        raise ValueError(f"Unbekannte Dachform: {kind}")
    part.add_f([A, D, C, B])


# ---------------------------------------------------------------------------
# Elemente -> Objekte
# ---------------------------------------------------------------------------

def _mat(name, default="stone"):
    if name is None:
        name = default
    if isinstance(name, str) and name.startswith("#"):
        return name
    return MATERIALS.get(name, MATERIALS[default])


def _footprint(el):
    if el.get("polygon"):
        return ensure_ccw(el["polygon"])
    center = el.get("center", [0, 0])
    if el.get("type") == "tower" and el.get("shape", "round") == "round" and not el.get("size"):
        return circle_poly(center, float(el.get("radius", 5)), int(el.get("segments", 12)))
    size = el.get("size")
    if size is None:
        r = float(el.get("radius", 5))
        size = [2 * r, 2 * r]
    if isinstance(size, (int, float)):
        size = [size, size]
    return rect_poly(center, size, float(el.get("orientation", 0)))


def _ground(T, poly):
    hs = T.sample_many(poly) + [T.sample(*centroid(poly))]
    return min(hs), sum(hs) / len(hs), max(hs)


def _base_z(el, T, poly):
    lo, mean, hi = _ground(T, poly)
    if el.get("base") is not None:
        g = float(el["base"])
    else:
        g = mean
    return lo - 1.5, g


def build_body(el, T, poly, parts):
    walls = Part(_mat(el.get("material")), "wall")
    roof = Part(_mat(el.get("roof_material"), "slate"), "roof")
    found, g = _base_z(el, T, poly)
    top = g + float(el.get("height", 10))
    add_prism(walls, poly, found, top)
    kind = el.get("roof", "gable")
    if kind == "crenellated":
        add_parapet_ring(walls, poly, top)
    elif kind not in ("flat", "none"):
        add_roof(roof, poly, top, kind, el.get("roof_height"), el.get("ridge_direction"))
    parts += [walls, roof]
    return g, top


def build_wall(el, T):
    walls = Part(_mat(el.get("material")), "wall")
    path = [tuple(p[:2]) for p in el["path"]]
    if el.get("closed"):
        path = path + [path[0]]
    t = float(el.get("thickness", 2))
    H = float(el.get("height", 8))
    # in Stücke ≤ 12 m teilen, damit die Mauerkrone dem Gelände getreppt folgt
    pts = [path[0]]
    for p0, p1 in zip(path[:-1], path[1:]):
        L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        k = max(1, int(math.ceil(L / 12)))
        for s in range(1, k + 1):
            pts.append((p0[0] + (p1[0] - p0[0]) * s / k, p0[1] + (p1[1] - p0[1]) * s / k))
    for p0, p1 in zip(pts[:-1], pts[1:]):
        if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) < 0.05:
            continue
        g0, g1 = T.sample(*p0), T.sample(*p1)
        gm = T.sample((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
        top = (g0 + g1 + gm) / 3 + H
        add_prism(walls, seg_rect(p0, p1, t, ext=t / 2), min(g0, g1, gm) - 1.5, top)
        if el.get("crenellated", True):
            add_merlons(walls, p0, p1, t * 0.45, top)
    return [walls]


def build_tower(el, T):
    poly = _footprint(el)
    parts = []
    g, top = build_body(dict(el, roof=el.get("roof", "cone")), T, poly, parts)
    return parts


def build_building(el, T):
    poly = _footprint(el)
    parts = []
    build_body(el, T, poly, parts)
    return parts


def build_gate(el, T):
    poly = _footprint(el)
    parts = []
    g, top = build_body(el, T, poly, parts)
    # Durchfahrt als dunkler, leicht vorstehender Kasten entlang der Tiefe
    center = el.get("center") or centroid(poly)
    size = el.get("size", [8, 10])
    orient = float(el.get("orientation", 0))
    pw = float(el.get("passage_width", 3.2))
    ph = float(el.get("passage_height", 4.2))
    passage = Part(MATERIALS["dark"], "opening")
    add_prism(passage, rect_poly(center, [size[0] + 0.2, pw], orient), g - 0.1, g + ph)
    parts.append(passage)
    return parts


def build_bridge(el, T):
    p0, p1 = [tuple(p[:2]) for p in el["path"][:2]]
    w = float(el.get("width", 3))
    z = el.get("deck_height")
    if z is None:
        z = max(T.sample(*p0), T.sample(*p1))
    z = float(z)
    deck = Part(_mat(el.get("material"), "wood"), "bridge")
    add_prism(deck, seg_rect(p0, p1, w), z - 0.6, z)
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    piers = int(el.get("piers", max(0, int(L // 8))))
    for k in range(1, piers + 1):
        t = k / (piers + 1)
        c = (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)
        add_prism(deck, seg_rect((c[0] - 0.4 * (p1[0] - p0[0]) / L, c[1] - 0.4 * (p1[1] - p0[1]) / L),
                                 (c[0] + 0.4 * (p1[0] - p0[0]) / L, c[1] + 0.4 * (p1[1] - p0[1]) / L), w * 0.8),
                  T.sample(*c) - 1, z - 0.6)
    return [deck]


def carve_path(T, path, width, depth, closed=False, surface=None):
    """Senkt das Gelände entlang einer Linie ab (Graben, Fluss)."""
    d, seg, tpar = dist_to_path(T.X, T.Y, path, closed)
    half = width / 2
    prof = np.clip(1 - (d / half) ** 2, 0, 1)
    if surface is None:
        T.h = np.where(d < half, T.h - depth * prof, T.h)
    else:
        target = surface - depth * prof
        T.h = np.where(d < half, np.minimum(T.h, target), T.h)
        bank = (d >= half) & (d < half + 4)
        T.h = np.where(bank, np.maximum(np.minimum(T.h, surface + (d - half) * 0.6), T.h - 50), T.h)
    return d


def water_ribbon(path, width, levels, closed=False):
    pts = [tuple(p[:2]) for p in path]
    lv = list(levels)
    if closed:
        pts = pts + [pts[0]]
        lv = lv + [lv[0]]
    part = Part(MATERIALS["water"], "water")
    n = len(pts)
    L, R = [], []
    for i in range(n):
        if i == 0:
            dx, dy = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]
        elif i == n - 1:
            dx, dy = pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1]
        else:
            dx, dy = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
        d = math.hypot(dx, dy) or 1
        nx, ny = dy / d * width / 2, -dx / d * width / 2
        R.append(part.add_v(pts[i][0] + nx, pts[i][1] + ny, lv[i]))
        L.append(part.add_v(pts[i][0] - nx, pts[i][1] - ny, lv[i]))
    for i in range(n - 1):
        part.add_f([R[i], R[i + 1], L[i + 1], L[i]])
    return part


def _running_min_levels(T, path, offset):
    lv = []
    cur = None
    for p in path:
        h = T.sample(p[0], p[1])
        cur = h if cur is None else min(cur, h)
        lv.append(cur + offset)
    return lv


# ---------------------------------------------------------------------------
# Umgebung
# ---------------------------------------------------------------------------

def _rand_points_in_poly(poly, count, rng, min_dist=0.0, reject=None):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    out = []
    tries = 0
    while len(out) < count and tries < count * 40:
        tries += 1
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if not point_in_poly(x, y, poly):
            continue
        if reject and reject(x, y):
            continue
        if min_dist and any((x - a) ** 2 + (y - b) ** 2 < min_dist ** 2 for a, b in out):
            continue
        out.append((x, y))
    return out


def _seg_dist(x, y, path):
    best, bdir = 1e18, (1.0, 0.0)
    for p0, p1 in zip(path[:-1], path[1:]):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L2 = dx * dx + dy * dy or 1e-9
        t = max(0, min(1, ((x - p0[0]) * dx + (y - p0[1]) * dy) / L2))
        d = math.hypot(x - p0[0] - t * dx, y - p0[1] - t * dy)
        if d < best:
            L = math.sqrt(L2)
            best, bdir = d, (dx / L, dy / L)
    return best, bdir


def build_environment(castle, T, objects, trees, castle_polys):
    env = (castle.get("site") or {}).get("environment") or {}
    rng = random.Random(int((castle.get("site") or {}).get("terrain", {}).get("seed", 7)))
    roads = [[tuple(p[:2]) for p in r["path"]] for r in env.get("roads", [])]
    water_polys = []

    def env_obj(oid, name, kind, parts, item):
        objects.append({
            "id": oid, "name": name, "type": kind, "layer": "umgebung",
            "confidence": confidence_of(item),
            "sources": (item.get("evidence") or {}).get("sources", []),
            "note": (item.get("evidence") or {}).get("note", ""),
            "parts": [p.to_dict() for p in parts if not p.empty()],
        })

    # Landnutzung (Zellfarben) – Reihenfolge = Priorität aufsteigend
    for f in env.get("fields", []):
        poly = ensure_ccw(f["polygon"])
        m = points_in_poly(T.CX, T.CY, poly) & (T.kind != "hof")
        kind = f.get("kind", "acker")
        if kind == "acker":
            ax, ay = main_axis(poly)
            stripe = np.floor((T.CX * -ay + T.CY * ax) / float(f.get("strip_width", 14))).astype(int) % 3
            for s in range(3):
                T.kind[m & (stripe == s)] = f"acker{s + 1}"
        else:
            T.kind[m] = {"wiese": "wiese", "weide": "weide", "weinberg": "weinberg",
                         "garten": "garten"}.get(kind, "wiese")
    for fo in env.get("forest", []):
        poly = ensure_ccw(fo["polygon"])
        T.kind[points_in_poly(T.CX, T.CY, poly) & (T.kind != "hof")] = "wald"
    for s in env.get("settlements", []):
        poly = ensure_ccw(s["polygon"])
        T.kind[points_in_poly(T.CX, T.CY, poly)] = "siedlung"
    for r in env.get("roads", []):
        d, _, _ = dist_to_path(T.CX, T.CY, r["path"])
        T.kind[d < float(r.get("width", 4)) / 2 + T.dx * 0.35] = "weg"

    # Gewässer: Flüsse, Seen
    for k, rv in enumerate(env.get("rivers", [])):
        path = [tuple(p[:2]) for p in rv["path"]]
        w = float(rv.get("width", 10))
        lv = _running_min_levels(T, path, -0.6)
        if rv.get("level") is not None:
            lv = [float(rv["level"])] * len(path)
        d, seg, tpar = dist_to_path(T.X, T.Y, path)
        lv_arr = np.array(lv)
        surf = lv_arr[seg] * (1 - tpar) + lv_arr[np.minimum(seg + 1, len(lv) - 1)] * tpar
        carve_path(T, path, w * 1.3, float(rv.get("depth", 2)), surface=surf)
        dc, _, _ = dist_to_path(T.CX, T.CY, path)
        T.kind[dc < w / 2 + T.dx * 0.3] = "wasser"
        env_obj(f"fluss_{k}", rv.get("name", "Fluss"), "river", [water_ribbon(path, w, [l + 0.15 for l in lv])], rv)
    for k, wa in enumerate(env.get("water", [])):
        poly = ensure_ccw(wa["polygon"])
        level = wa.get("level")
        if level is None:
            level = min(T.sample_many(poly)) - 0.5
        level = float(level)
        inside = points_in_poly(T.X, T.Y, poly)
        T.h = np.where(inside, np.minimum(T.h, level - 1.5), T.h)
        T.kind[points_in_poly(T.CX, T.CY, poly)] = "wasser"
        part = Part(MATERIALS["water"], "water")
        idx = [part.add_v(x, y, level + 0.1) for x, y in poly]
        part.add_f(idx)
        env_obj(f"see_{k}", wa.get("name", "Gewässer"), "water", [part], wa)
        water_polys.append(poly)

    def blocked(x, y, extra=0.0):
        cx = int((x + T.extent / 2) / T.dx)
        cy = int((y + T.extent / 2) / T.dx)
        if 0 <= cx < T.res and 0 <= cy < T.res and T.kind[cy, cx] in ("wasser", "weg", "hof"):
            return True
        for poly in castle_polys:
            if point_in_poly(x, y, poly):
                return True
        for rp in roads:
            if _seg_dist(x, y, rp)[0] < 3 + extra:
                return True
        return False

    # Wald -> Bäume (als Instanzen)
    max_trees = int(env.get("max_trees", 2500))
    for fo in env.get("forest", []):
        poly = ensure_ccw(fo["polygon"])
        area = abs(poly_area(poly))
        dens = float(fo.get("density", 0.6))
        count = int(area / 90 * dens)
        count = min(count, max(0, max_trees - len(trees)))
        kind = fo.get("kind", "laub")
        for x, y in _rand_points_in_poly(poly, count, rng, reject=blocked):
            k = kind if kind in ("laub", "nadel") else rng.choice(["laub", "laub", "nadel"])
            trees.append([round(x, 1), round(y, 1), round(T.sample(x, y), 2), k, round(rng.uniform(0.8, 1.3), 2)])

    # Siedlungen -> Häuser
    for k, s in enumerate(env.get("settlements", [])):
        poly = ensure_ccw(s["polygon"])
        walls = Part(MATERIALS[s.get("material", "timber")], "wall")
        roof = Part(MATERIALS[s.get("roof_material", "thatch")], "roof")
        n = int(s.get("houses", 12))
        pts = _rand_points_in_poly(poly, n, rng, min_dist=11, reject=lambda x, y: blocked(x, y, 3))
        ax = main_axis(poly)
        for x, y in pts:
            d, rd = (1e9, ax)
            for rp in roads:
                dd, ddir = _seg_dist(x, y, rp)
                if dd < d:
                    d, rd = dd, ddir
            if d > 30:
                rd = ax
            ang = math.degrees(math.atan2(rd[0], rd[1])) + rng.choice([0, 90]) + rng.uniform(-8, 8)
            L, W = rng.uniform(8, 12), rng.uniform(5, 7)
            fp = rect_poly((x, y), [L, W], ang)
            g = min(T.sample_many(fp))
            add_prism(walls, fp, g - 1, g + rng.uniform(3.2, 4.2))
            top = walls.v[-1][2]
            add_roof(roof, fp, top, "gable", W * 0.75, ang, 0.5)
        parts = [walls, roof]
        if s.get("church"):
            cx, cy = centroid(poly)
            ch = Part(MATERIALS["stone"], "wall")
            chr_ = Part(MATERIALS["slate"], "roof")
            fp = rect_poly((cx, cy), [20, 9], s.get("church_orientation", 90))
            g = min(T.sample_many(fp))
            add_prism(ch, fp, g - 1, g + 8)
            add_roof(chr_, fp, g + 8, "gable", 6, s.get("church_orientation", 90))
            tx, ty = compass_to_vec(float(s.get("church_orientation", 90)))
            tw = rect_poly((cx - tx * 13, cy - ty * 13), [6, 6], s.get("church_orientation", 90))
            add_prism(ch, tw, g - 1, g + 18)
            add_roof(chr_, tw, g + 18, "pyramid", 9)
            parts += [ch, chr_]
        env_obj(f"siedlung_{k}", s.get("name", "Siedlung"), "settlement", parts, s)


# ---------------------------------------------------------------------------
# Szene
# ---------------------------------------------------------------------------

BUILDERS = {"wall": build_wall, "tower": build_tower, "building": build_building,
            "gate": build_gate, "bridge": build_bridge}


def build_scene(castle):
    T = build_terrain(castle)
    elements = [element_defaults(e) for e in castle.get("elements", [])]
    objects = []
    trees = []

    # 1. Gräben verändern das Gelände zuerst
    for el in elements:
        if el["type"] != "ditch":
            continue
        path = el["path"]
        closed = bool(el.get("closed"))
        d = carve_path(T, path, float(el["width"]), float(el["depth"]), closed)
        dc, _, _ = dist_to_path(T.CX, T.CY, path, closed)
        T.kind[(dc < float(el["width"]) / 2) & (T.kind != "hof")] = "graben"
        if el.get("water"):
            lv = min(T.sample(p[0], p[1]) for p in path)
            level = float(el.get("water_level", lv + float(el["depth"]) * 0.55))
            pts = [tuple(p[:2]) for p in path]
            part = water_ribbon(pts, float(el["width"]) * 0.75, [level] * len(pts), closed)
            T.kind[(dc < float(el["width"]) * 0.75 / 2)] = "wasser"
            objects.append(_obj(el, [part]))

    # 2. Bauwerke
    castle_polys = []
    for el in elements:
        if el["type"] == "ditch":
            continue
        builder = BUILDERS.get(el["type"])
        if builder is None:
            raise ValueError(f"Unbekannter Elementtyp: {el['type']} ({el.get('id')})")
        parts = builder(el, T)
        objects.append(_obj(el, parts))
        if el["type"] in ("tower", "building", "gate"):
            castle_polys.append(_footprint(el))

    # 3. Umgebung
    build_environment(castle, T, objects, trees, castle_polys)

    palette = list(TERRAIN_COLORS.keys())
    kinds = [[palette.index(k) for k in row] for row in T.kind]
    meta = castle.get("meta", {})
    return {
        "meta": {
            "name": meta.get("name", "Burg"),
            "date": meta.get("date"),
            "description": meta.get("description", ""),
            "sources": meta.get("sources", []),
            "lat": castle.get("site", {}).get("lat"),
            "lon": castle.get("site", {}).get("lon"),
            "elevation": castle.get("site", {}).get("elevation"),
        },
        "terrain": {
            "extent": T.extent, "res": T.res, "dx": T.dx,
            "heights": [[round(float(v), 2) for v in row] for row in T.h],
            "palette": [TERRAIN_COLORS[k] for k in palette],
            "palette_names": palette,
            "cells": kinds,
        },
        "objects": objects,
        "trees": trees,
        "tree_colors": TREE_COLORS,
        "confidence_colors": CONFIDENCE_COLORS,
        "castle_bbox": _bbox([v for o in objects if o["layer"] == "burg"
                              for p in o["parts"] for v in p["vertices"]]),
    }


def _obj(el, parts):
    ev = el.get("evidence") or {}
    return {
        "id": el.get("id") or el.get("name") or el["type"],
        "name": el.get("name") or el.get("id") or el["type"],
        "type": el["type"],
        "layer": el.get("layer", "burg"),
        "phase": el.get("phase", ""),
        "confidence": confidence_of(el),
        "sources": ev.get("sources", []),
        "note": ev.get("note", ""),
        "parts": [p.to_dict() for p in parts if not p.empty()],
    }


def _bbox(verts):
    if not verts:
        return [[-50, -50, 0], [50, 50, 20]]
    a = np.array(verts)
    return [a.min(axis=0).round(2).tolist(), a.max(axis=0).round(2).tolist()]


# ---------------------------------------------------------------------------
# Baumgeometrie (für GLB-Export und Zeichnung)
# ---------------------------------------------------------------------------

def tree_parts(trees):
    """Erzeugt zusammengefasste Low-Poly-Meshes aller Bäume."""
    crown_l = Part(TREE_COLORS["laub"], "tree")
    crown_n = Part(TREE_COLORS["nadel"], "tree")
    trunk = Part(TREE_COLORS["stamm"], "trunk")
    for x, y, z, kind, s in trees:
        add_prism(trunk, circle_poly((x, y), 0.35 * s, 3), z - 0.5, z + 2.2 * s, top=False)
        if kind == "nadel":
            ring = circle_poly((x, y), 2.4 * s, 6)
            idx = [crown_n.add_v(px, py, z + 1.5 * s) for px, py in ring]
            apex = crown_n.add_v(x, y, z + 10 * s)
            for i in range(6):
                crown_n.add_f([idx[i], idx[(i + 1) % 6], apex])
            crown_n.add_f(idx[::-1])
        else:
            ring = circle_poly((x, y), 3.4 * s, 6)
            zm = z + 5.0 * s
            idx = [crown_l.add_v(px, py, zm) for px, py in ring]
            top = crown_l.add_v(x, y, z + 8.5 * s)
            bot = crown_l.add_v(x, y, z + 1.8 * s)
            for i in range(6):
                crown_l.add_f([idx[i], idx[(i + 1) % 6], top])
                crown_l.add_f([idx[(i + 1) % 6], idx[i], bot])
    return [p for p in (trunk, crown_l, crown_n) if not p.empty()]


# ---------------------------------------------------------------------------
# Triangulierung von Polygonflächen (für GLB/OBJ/Viewer)
# ---------------------------------------------------------------------------

def face_normal(pts):
    """Newell-Normale eines (räumlichen) Polygons."""
    nx = ny = nz = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0, z0 = pts[i]
        x1, y1, z1 = pts[(i + 1) % n]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / L, ny / L, nz / L)


def triangulate_face(pts):
    """Polygon im Raum -> Dreiecke (Indizes in pts), Umlaufsinn wie das Polygon."""
    if len(pts) == 3:
        return [(0, 1, 2)]
    n = face_normal(pts)
    ax = max(range(3), key=lambda k: abs(n[k]))
    keep = [k for k in range(3) if k != ax]
    flat = [(p[keep[0]], p[keep[1]]) for p in pts]
    tris = triangulate(flat)
    out = []
    for a, b, c in tris:
        tn = face_normal([pts[a], pts[b], pts[c]])
        if tn[0] * n[0] + tn[1] * n[1] + tn[2] * n[2] < 0:
            b, c = c, b
        out.append((a, b, c))
    return out


def part_triangles(part):
    """Teil-dict -> Liste von Dreiecken [(p0, p1, p2), ...] in lokalen Koordinaten."""
    V = part["vertices"]
    out = []
    for f in part["faces"]:
        pts = [V[i] for i in f]
        for a, b, c in triangulate_face(pts):
            out.append((pts[a], pts[b], pts[c]))
    return out


def terrain_triangles(terrain):
    """Gelände -> Liste (Dreieck, Farbe)."""
    H = terrain["heights"]
    res = terrain["res"]
    dx = terrain["dx"]
    e = terrain["extent"] / 2
    pal = terrain["palette"]
    out = []
    for j in range(res):
        for i in range(res):
            x0, x1 = -e + i * dx, -e + (i + 1) * dx
            y0, y1 = -e + j * dx, -e + (j + 1) * dx
            a = (x0, y0, H[j][i])
            b = (x1, y0, H[j][i + 1])
            c = (x1, y1, H[j + 1][i + 1])
            d = (x0, y1, H[j + 1][i])
            col = pal[terrain["cells"][j][i]]
            out.append(((a, b, c), col))
            out.append(((a, c, d), col))
    return out
