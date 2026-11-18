"""One icon for the product, drawn once and rendered at every size.

A net, not a shield and not a spiderweb: a diamond lattice whose threads bow very slightly
outward, with a knot at every vertex so the corners read as bullets rather than joins, and
the whole thing stretched vertically by about a tenth so it sits in the square like a net
hanging rather than a graph plotted.

The same file feeds the web manifest, the favicon, the apple touch icon and the Android
launcher densities, so the two products cannot drift apart again.
"""
from PIL import Image, ImageDraw
import math
import os

SAGE = (143, 169, 143)
KNOT = (203, 215, 203)
FIELD = (10, 15, 21)
EDGE = (255, 255, 255, 22)

SS = 4  # supersample factor


def bezier(p0, p1, p2, steps=22):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def draw_icon(size: int) -> Image.Image:
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = int(s * 0.055)
    d.rounded_rectangle([pad, pad, s - pad, s - pad], radius=int(s * 0.235),
                        fill=FIELD + (255,), outline=EDGE, width=max(1, s // 160))

    # A net, not a mesh: warps and wefts crossing at right angles, each thread bowed a
    # little outward so the square hangs rather than rules, and stretched vertically so it
    # sits in the icon like something hung up rather than a plotted grid.
    stretch = 1.09
    span = 0.60
    cols, rows = 4, 4

    def to_px(p):
        return (s / 2 + p[0] * s * 0.5, s / 2 + p[1] * s * 0.5)

    thread = max(2, int(s * 0.015))

    xs = [(-span + 2 * span * c / (cols - 1)) for c in range(cols)]
    ys = [(-span * stretch + 2 * span * stretch * r / (rows - 1)) for r in range(rows)]

    def bow_amount(v):
        # threads near the edge bow outward more, which is what gives a net its sag
        return 0.045 + 0.05 * abs(v)

    # warps: near vertical, bowed sideways
    for x in xs:
        a = (x, ys[0])
        b = (x, ys[-1])
        ctrl = (x + (0.11 if x >= 0 else -0.11) * (1 + bow_amount(x) * 6), 0.0)
        d.line(bezier(to_px(a), to_px(ctrl), to_px(b)), fill=SAGE + (232,), width=thread, joint="curve")

    # wefts: near horizontal, bowed up or down
    for y in ys:
        a = (xs[0], y)
        b = (xs[-1], y)
        ctrl = (0.0, y + (0.11 if y >= 0 else -0.11) * (1 + bow_amount(y) * 6))
        d.line(bezier(to_px(a), to_px(ctrl), to_px(b)), fill=SAGE + (232,), width=thread, joint="curve")

    # a knot at every crossing: the bullets the net hands off between threads
    for r, y in enumerate(ys):
        for c, x in enumerate(xs):
            px = to_px((x, y))
            corner = r in (0, rows - 1) and c in (0, cols - 1)
            edge = r in (0, rows - 1) or c in (0, cols - 1)
            radius = s * (0.036 if corner else 0.028 if edge else 0.024)
            d.ellipse([px[0] - radius, px[1] - radius, px[0] + radius, px[1] + radius],
                      fill=KNOT + (255,))

    return img.resize((size, size), Image.LANCZOS)


SIZES = {
    "android/app/src/main/res/mipmap-mdpi/ic_launcher.png": 48,
    "android/app/src/main/res/mipmap-hdpi/ic_launcher.png": 72,
    "android/app/src/main/res/mipmap-xhdpi/ic_launcher.png": 96,
    "android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png": 144,
    "android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png": 192,
    "app/static/icon-192.png": 192,
    "app/static/icon-512.png": 512,
    "app/static/apple-touch-icon.png": 180,
    "app/static/favicon-32.png": 32,
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    for rel, size in SIZES.items():
        path = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        draw_icon(size).save(path)
        print(f"{rel:58} {size}px")
    draw_icon(512).save(os.path.join(ROOT, "docs", "icon-preview.png"))
    print("preview written to docs/icon-preview.png")
