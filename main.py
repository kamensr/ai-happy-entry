#!/usr/bin/env python3
"""ai-happy-01 entry: a deterministic, happy-making image.

Draws a warm little scene — a smiling sun over rolling hills, a rainbow,
flowers, and a tiny happy cat — using nothing but the Python standard
library. Output is byte-identical on every run.

Usage:
    MAKEFUN_OUTPUT=/somewhere python3 main.py   # writes <dir>/entry.png
"""

import os
import math
import struct
import zlib

# ---------------------------------------------------------------------------
# Canvas settings
# ---------------------------------------------------------------------------
W, H = 1024, 1024
SS = 2                      # supersampling factor for smooth edges
SW, SH = W * SS, H * SS     # working surface (supersampled)

OUTPUT_NAME = "entry.png"


# ---------------------------------------------------------------------------
# Tiny deterministic rasterizer helpers (supersampled space)
# ---------------------------------------------------------------------------

def smoothstep(edge0, edge1, x):
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


class Canvas:
    """Float RGB buffer in supersampled space."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.buf = [[[0.0, 0.0, 0.0] for _ in range(w)] for _ in range(h)]

    def blend(self, x, y, color, alpha):
        """alpha-blend `color` into pixel (x, y)."""
        if x < 0 or y < 0 or x >= self.w or y >= self.h or alpha <= 0:
            return
        px = self.buf[y][x]
        a = min(1.0, alpha)
        for i in range(3):
            px[i] = px[i] * (1 - a) + color[i] * a

    def disk(self, cx, cy, r, color, softness=1.5, alpha=1.0):
        """Anti-aliased filled circle."""
        x0 = max(0, int(cx - r - softness * 2))
        x1 = min(self.w - 1, int(cx + r + softness * 2))
        y0 = max(0, int(cy - r - softness * 2))
        y1 = min(self.h - 1, int(cy + r + softness * 2))
        for y in range(y0, y1 + 1):
            dy = y - cy
            for x in range(x0, x1 + 1):
                dx = x - cx
                d = (dx * dx + dy * dy) ** 0.5
                a = smoothstep(r + softness, r - softness, d) * alpha
                if a > 0:
                    self.blend(x, y, color, a)

    def ring(self, cx, cy, r, thickness, color, alpha=1.0, softness=1.5):
        """Anti-aliased ring (annulus)."""
        x0 = max(0, int(cx - r - thickness - softness * 2))
        x1 = min(self.w - 1, int(cx + r + thickness + softness * 2))
        y0 = max(0, int(cy - r - thickness - softness * 2))
        y1 = min(self.h - 1, int(cy + r + thickness + softness * 2))
        inner = r - thickness / 2
        outer = r + thickness / 2
        for y in range(y0, y1 + 1):
            dy = y - cy
            for x in range(x0, x1 + 1):
                dx = x - cx
                d = (dx * dx + dy * dy) ** 0.5
                a_in = smoothstep(inner - softness, inner + softness, d)
                a_out = smoothstep(outer + softness, outer - softness, d)
                a = a_in * a_out * alpha
                if a > 0:
                    self.blend(x, y, color, a)

    def rect(self, x0, y0, x1, y1, color, alpha=1.0):
        """Axis-aligned rectangle with soft edges."""
        ix0, ix1 = max(0, int(x0) - 2), min(self.w - 1, int(x1) + 2)
        iy0, iy1 = max(0, int(y0) - 2), min(self.h - 1, int(y1) + 2)
        for y in range(iy0, iy1 + 1):
            ay = smoothstep(y0 - 1, y0 + 1, y) * smoothstep(y1 + 1, y1 - 1, y)
            for x in range(ix0, ix1 + 1):
                ax = smoothstep(x0 - 1, x0 + 1, x) * smoothstep(x1 + 1, x1 - 1, x)
                a = ax * ay * alpha
                if a > 0:
                    self.blend(x, y, color, a)

    def hill(self, base_y, amplitude, cycles, phase, color, alpha=1.0):
        """A gentle rolling hill: anything below the curve gets the color."""
        for y in range(max(0, int(base_y - amplitude - 2)), self.h):
            for x in range(self.w):
                # smooth sine curve
                curve = base_y - amplitude * (0.5 + 0.5 * math.sin(
                    x / self.w * 6.28318 * cycles + phase))
                if y >= curve:
                    self.blend(x, y, color, alpha)

    def downsample(self):
        """Average SS x SS blocks -> final int RGB rows."""
        rows = []
        for y in range(H):
            row = bytearray()
            for x in range(W):
                r = g = b = 0.0
                for sy in range(SS):
                    for sx in range(SS):
                        px = self.buf[y * SS + sy][x * SS + sx]
                        r += px[0]
                        g += px[1]
                        b += px[2]
                n = SS * SS
                row.append(clamp8(r / n))
                row.append(clamp8(g / n))
                row.append(clamp8(b / n))
            rows.append(bytes(row))
        return rows


def clamp8(v):
    return max(0, min(255, int(round(v))))


# ---------------------------------------------------------------------------
# PNG writer (stdlib only)
# ---------------------------------------------------------------------------

def write_png(path, rows, width, height):
    def chunk(tag, data):
        raw = tag + data
        return struct.pack(">I", len(data)) + raw + struct.pack(
            ">I", zlib.crc32(raw) & 0xFFFFFFFF
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    body = bytearray()
    for row in rows:
        body.append(0)  # filter: none
        body += row
    idat = zlib.compress(bytes(body), 9)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", idat)
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------------------
# Colors (0-255 RGB)
# ---------------------------------------------------------------------------

def C(r, g, b):
    return [float(r), float(g), float(b)]


SKY_TOP = C(255, 214, 165)
SKY_BOT = C(255, 244, 214)
SUN_CORE = C(255, 236, 130)
SUN_EDGE = C(255, 190, 80)
HILL_FAR = C(168, 208, 141)
HILL_MID = C(120, 178, 110)
HILL_NEAR = C(86, 148, 92)
RAINBOW = [
    C(255, 120, 120), C(255, 170, 90), C(255, 225, 100),
    C(140, 210, 130), C(110, 180, 235), C(160, 130, 220),
]
WHITE = C(255, 255, 255)
INK = C(70, 50, 45)
CHEEK = C(255, 150, 120)
FLOWER_PINK = C(255, 160, 190)
FLOWER_YELLOW = C(255, 220, 110)
FLOWER_WHITE = C(255, 252, 245)
CAT_BODY = C(255, 176, 120)
CAT_INK = C(90, 60, 50)


# ---------------------------------------------------------------------------
# Scene drawing
# ---------------------------------------------------------------------------

def draw_sky(cnv):
    """Vertical warm gradient (direct buffer write for speed)."""
    for y in range(cnv.h):
        t = y / (cnv.h - 1)
        t = t * t * (3 - 2 * t)  # ease
        r = SKY_TOP[0] * (1 - t) + SKY_BOT[0] * t
        g = SKY_TOP[1] * (1 - t) + SKY_BOT[1] * t
        b = SKY_TOP[2] * (1 - t) + SKY_BOT[2] * t
        row = cnv.buf[y]
        for x in range(cnv.w):
            px = row[x]
            px[0] = r
            px[1] = g
            px[2] = b


def draw_sun(cnv):
    cx, cy, r = SW * 0.72, SH * 0.26, SW * 0.14
    # rays
    for i in range(12):
        a = math.radians(i * 30 + 8)
        x1 = cx + math.cos(a) * (r * 1.18)
        y1 = cy + math.sin(a) * (r * 1.18)
        x2 = cx + math.cos(a) * (r * 1.52)
        y2 = cy + math.sin(a) * (r * 1.52)
        for t in range(7):
            tt = t / 6
            cnv.disk(x1 + (x2 - x1) * tt, y1 + (y2 - y1) * tt,
                     r * 0.035, SUN_EDGE, softness=1.0, alpha=0.9)
    # soft halo
    cnv.disk(cx, cy, r * 1.9, C(255, 230, 160), softness=r * 0.5, alpha=0.45)
    cnv.disk(cx, cy, r * 1.45, C(255, 220, 130), softness=r * 0.3, alpha=0.5)
    # body
    cnv.disk(cx, cy, r, SUN_CORE, softness=2.5)
    # face
    ex, ey = r * 0.34, r * 0.16
    for sx in (-1, 1):
        cnv.disk(cx + sx * ex, cy + ey, r * 0.075, INK, softness=1.2)
    # smile: arc of small disks
    for i in range(14):
        a = math.radians(20 + i * 10)
        sx = cx + math.cos(a) * r * 0.42
        sy = cy + ey + math.sin(a) * r * 0.34
        cnv.disk(sx, sy, r * 0.045, INK, softness=1.0)
    # rosy cheeks
    for sx in (-1, 1):
        cnv.disk(cx + sx * r * 0.58, cy + r * 0.34, r * 0.11, CHEEK, softness=3.0, alpha=0.55)


def draw_rainbow(cnv):
    cx, cy = SW * 0.34, SH * 0.78
    base_r = SW * 0.52
    n = len(RAINBOW)
    band = SW * 0.018
    gap = SW * 0.006
    for i, col in enumerate(RAINBOW):
        rr = base_r - i * (band + gap)
        # only upper arc
        cnv.ring(cx, cy, rr, band, col, alpha=0.85, softness=1.5)


def draw_hills(cnv):
    cnv.hill(SH * 0.72, SH * 0.06, 1.2, 0.0, HILL_FAR)
    cnv.hill(SH * 0.80, SH * 0.07, 1.7, 2.1, HILL_MID)
    cnv.hill(SH * 0.90, SH * 0.06, 1.3, 4.4, HILL_NEAR)


def draw_flower(cnv, x, y, size, petal_col, core_col):
    import math
    for i in range(6):
        a = math.radians(i * 60)
        px = x + math.cos(a) * size
        py = y + math.sin(a) * size
        cnv.disk(px, py, size * 0.62, petal_col, softness=1.0)
    cnv.disk(x, y, size * 0.5, core_col, softness=1.0)


def draw_birds(cnv):
    """Simple distant birds: two soft arcs each."""
    for (fx, fy, fs) in [(0.55, 0.34, 1.0), (0.64, 0.28, 0.7), (0.47, 0.24, 0.55)]:
        cx, cy = fx * SW, fy * SH
        s = SW * 0.024 * fs
        for sx in (-1, 1):
            for i in range(7):
                t = i / 6
                bx = cx + sx * s * t
                by = cy - math.sin(t * math.pi) * s * 0.45
                cnv.disk(bx, by, s * 0.09, C(95, 85, 95),
                         softness=0.8, alpha=0.85)


def draw_hearts(cnv):
    """A couple of tiny floating hearts of affection."""
    for (fx, fy, fs, alpha) in [(0.575, 0.70, 1.0, 0.9), (0.365, 0.64, 0.6, 0.8)]:
        hx, hy = fx * SW, fy * SH
        r = SW * 0.013 * fs
        col = C(255, 105, 130)
        cnv.disk(hx - r * 0.7, hy - r * 0.5, r * 0.75, col, softness=1.0, alpha=alpha)
        cnv.disk(hx + r * 0.7, hy - r * 0.5, r * 0.75, col, softness=1.0, alpha=alpha)
        cnv.disk(hx, hy + r * 0.15, r * 0.95, col, softness=1.0, alpha=alpha)
        cnv.disk(hx, hy + r * 0.55, r * 0.6, col, softness=1.0, alpha=alpha)


def draw_flowers(cnv):
    # little flower patches on the near hill
    spots = [
        (0.12, 0.965, 9, FLOWER_PINK, FLOWER_YELLOW),
        (0.20, 0.935, 7, FLOWER_WHITE, C(255, 190, 90)),
        (0.30, 0.985, 10, FLOWER_YELLOW, C(255, 255, 255)),
        (0.55, 0.955, 8, FLOWER_PINK, FLOWER_YELLOW),
        (0.64, 0.985, 10, FLOWER_WHITE, C(255, 190, 90)),
        (0.75, 0.945, 7, FLOWER_YELLOW, FLOWER_WHITE),
        (0.88, 0.975, 9, FLOWER_PINK, FLOWER_YELLOW),
        (0.95, 0.955, 7, FLOWER_WHITE, C(255, 190, 90)),
    ]
    for fx, fy, fs, pc, cc in spots:
        draw_flower(cnv, fx * SW, fy * SH, fs, pc, cc)


def draw_cat(cnv):
    """A tiny round happy cat sitting on the mid hill."""
    cx, cy = SW * 0.47, SH * 0.845
    s = SW * 0.052  # body radius
    # body
    cnv.disk(cx, cy, s, CAT_BODY, softness=2.0)
    # ears
    for sx in (-1, 1):
        cnv.disk(cx + sx * s * 0.62, cy - s * 0.85, s * 0.30, CAT_BODY, softness=1.5)
        cnv.disk(cx + sx * s * 0.62, cy - s * 0.85, s * 0.13, C(255, 220, 210), softness=1.0)
    # eyes (happy closed arcs)
    for sx in (-1, 1):
        for i in range(6):
            a = math.radians(180 + i * 12)
            ex = cx + sx * s * 0.36 + math.cos(a) * s * 0.14
            ey = cy - s * 0.12 - abs(math.sin(a)) * s * 0.14
            cnv.disk(ex, ey, s * 0.06, CAT_INK, softness=0.8)
    # nose
    cnv.disk(cx, cy + s * 0.10, s * 0.06, C(230, 120, 110), softness=0.8)
    # little "w" smile: two symmetric half-circle arcs
    for sx in (-1, 1):
        ccx = cx + sx * s * 0.16
        for i in range(6):
            a = math.radians(10 + i * 32)
            mx = ccx + math.cos(a) * s * 0.13
            my = cy + s * 0.22 + math.sin(a) * s * 0.13
            cnv.disk(mx, my, s * 0.045, CAT_INK, softness=0.8)
    # whiskers
    for sx in (-1, 1):
        for ang in (-14, 0, 14):
            for i in range(6):
                t = i / 5
                wx = cx + sx * (s * 0.75 + t * s * 0.55)
                wy = cy + s * 0.10 + sx * math.sin(math.radians(ang)) * (t * s * 0.55)
                cnv.disk(wx, wy, s * 0.025, C(120, 90, 80),
                         softness=0.6, alpha=0.7)
    # blush
    for sx in (-1, 1):
        cnv.disk(cx + sx * s * 0.55, cy + s * 0.22, s * 0.14, CHEEK, softness=2.0, alpha=0.5)


def draw_clouds(cnv):
    for (fx, fy, fs, alpha) in [
        (0.18, 0.16, 1.0, 0.9),
        (0.52, 0.10, 0.7, 0.85),
    ]:
        cx, cy = fx * SW, fy * SH
        r = SW * 0.045 * fs
        for (dx, dy, rr) in [(-1.4, 0.1, 0.8), (-0.6, -0.4, 1.0),
                             (0.4, -0.15, 0.9), (1.2, 0.15, 0.7),
                             (0.0, 0.25, 1.1)]:
            cnv.disk(cx + dx * r, cy + dy * r, r * rr, WHITE, softness=3.0, alpha=alpha)


def render():
    cnv = Canvas(SW, SH)
    draw_sky(cnv)
    draw_clouds(cnv)
    draw_sun(cnv)
    draw_birds(cnv)
    draw_rainbow(cnv)
    draw_hills(cnv)
    draw_hearts(cnv)
    draw_flowers(cnv)
    draw_cat(cnv)
    return cnv.downsample()


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT", "/output")
    os.makedirs(out_dir, exist_ok=True)
    rows = render()
    write_png(os.path.join(out_dir, OUTPUT_NAME), rows, W, H)


if __name__ == "__main__":
    main()
