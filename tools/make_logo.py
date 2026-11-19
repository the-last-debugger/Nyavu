"""The Nyavu mark: a cast net, drawn once and exported everywhere.

The reference is a throwing net seen edge on: strands leave an apex at the top, sag to a
base line, and end in knots. Two wefts cross them, so the mesh reads as a net rather than a
fan. A wordmark is not part of the mark; the name is set in the product's serif beside it.

Everything the web and the app use is generated here, so the two cannot drift apart:
the favicon, the manifest icons, the Apple touch icon, the five Android densities, a
transparent copy of the mark for the page header, and an SVG of the same geometry.
"""
from PIL import Image, ImageDraw
import math
import os

SAGE = (143, 169, 143)
KNOT = (203, 215, 203)
FIELD = (10, 15, 21)
BONE = (233, 227, 214)
EDGE = (255, 255, 255, 26)

SS = 4
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------- geometry

def net_geometry(compact: bool = False):
    """A shield drawn as a net.

    The rim is the top edge, wide and knotted; the strands fall to a short blunt tip rather
    than a spike, so they do not collapse into a blob where they meet. Two wefts cross them
    and hang slightly towards the tip, which is what makes it read as a net rather than as a
    shield with stripes.
    """
    rim_y = 0.13
    tip_y = 0.90
    strands = 5 if compact else 9
    rim_half = 0.42        # the rim spans 0.08 .. 0.92
    tip_half = 0.045       # a blunt tip, not a point

    tops, bottoms = [], []
    for i in range(strands):
        t = i / (strands - 1)
        tops.append((0.5 + (t - 0.5) * 2 * rim_half, rim_y))
        bottoms.append((0.5 + (t - 0.5) * 2 * tip_half, tip_y))

    strand_curves = []
    for top, bottom in zip(tops, bottoms):
        # the control point pulls the strand outwards near the middle, which is what gives a
        # shield its shoulder
        control = (top[0] + (top[0] - 0.5) * 0.55, rim_y + (tip_y - rim_y) * 0.58)
        strand_curves.append((top, control, bottom))

    def at(curve, t):
        (x0, y0), (x1, y1), (x2, y2) = curve
        u = 1 - t
        return (u * u * x0 + 2 * u * t * x1 + t * t * x2,
                u * u * y0 + 2 * u * t * y1 + t * t * y2)

    wefts = []
    bands = ((0.46, 0.022),) if compact else ((0.38, 0.022), (0.68, 0.016))
    for fraction, sag_amount in bands:
        band = []
        for curve in strand_curves:
            x, y = at(curve, fraction)
            band.append((x, y + sag_amount * math.sin(math.pi * min(max(x, 0.0), 1.0))))
        wefts.append(band)

    knots = tops
    return strand_curves, wefts, knots, (0.5, tip_y)


def curve_points(control_a, control_b, control_c, steps=26):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        pts.append((
            u * u * control_a[0] + 2 * u * t * control_b[0] + t * t * control_c[0],
            u * u * control_a[1] + 2 * u * t * control_b[1] + t * t * control_c[1],
        ))
    return pts


def smooth_path(points, steps=12):
    """A polyline smoothed through its points, for the wefts."""
    out = []
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        out.append(a)
        out.append(mid)
    out.append(points[-1])
    return out


# ------------------------------------------------------------------ drawing

def draw_mark(draw, size, colour, knot_colour, scale=1.0, offset=(0.0, 0.0),
              width_scale=1.0, compact: bool = False):
    strands, wefts, knots, _ = net_geometry(compact=compact)
    stroke = max(1, int(size * (0.034 if compact else 0.019) * width_scale))

    def px(p):
        x = (p[0] * scale + offset[0]) * size
        y = (p[1] * scale + offset[1]) * size
        return (x, y)

    # every point goes through px: the geometry is 0..1 and the canvas is pixels, and
    # forgetting that once drew the whole net inside a single pixel
    for a, c, b in strands:
        draw.line([px(p) for p in curve_points(a, c, b)], fill=colour, width=stroke, joint="curve")
    for weft in wefts:
        draw.line([px(p) for p in smooth_path(weft)], fill=colour, width=stroke, joint="curve")
    for knot in knots:
        r = size * 0.022
        cx, cy = px(knot)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=knot_colour)

    # nine rounded strand ends meeting at the tip read as a frayed edge; one small filled cap
    # closes the shape the way the corner of a shield is closed
    tip_x, tip_y = px((0.5, 0.90))
    cap_w = size * 0.070 * scale
    cap_h = size * 0.020 * scale
    draw.ellipse([tip_x - cap_w, tip_y - cap_h, tip_x + cap_w, tip_y + cap_h], fill=colour)


def icon(size: int) -> Image.Image:
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = int(s * 0.055)
    d.rounded_rectangle([pad, pad, s - pad, s - pad], radius=int(s * 0.235),
                        fill=FIELD + (255,), outline=EDGE, width=max(1, s // 160))
    # the mark sits in the lower two thirds, so the dome reads as an arch in the square
    compact = size <= 72
    draw_mark(d, s, SAGE + (240,), KNOT + (255,), scale=0.80 if compact else 0.82,
              offset=(0.10, 0.06) if compact else (0.09, 0.07), compact=compact)
    return img.resize((size, size), Image.LANCZOS)


def mark_only(size: int, colour=BONE, knot=None, compact: bool = False) -> Image.Image:
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_mark(d, s, colour + (255,), (knot or colour) + (255,), scale=0.90, offset=(0.05, 0.05),
              compact=compact)
    return img.resize((size, size), Image.LANCZOS)


def svg(compact: bool = False) -> str:
    strands, wefts, knots, _ = net_geometry(compact=compact)
    pts = []
    for a, c, b in strands:
        pts.append(
            f'<path d="M{a[0]*100:.2f},{a[1]*100:.2f} Q{c[0]*100:.2f},{c[1]*100:.2f} '
            f'{b[0]*100:.2f},{b[1]*100:.2f}"/>'
        )
    for weft in wefts:
        commands = " L".join(f"{x*100:.2f},{y*100:.2f}" for x, y in smooth_path(weft))
        pts.append(f'<path class="weft" d="M{commands}"/>')
    dots = "".join(
        f'<circle cx="{x*100:.2f}" cy="{y*100:.2f}" r="1.9"/>' for x, y in knots
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" '
        'aria-label="Nyavu">\n'
        f'  <g fill="none" stroke="currentColor" stroke-width="{3.4 if compact else 1.9}" '
        'stroke-linecap="round" stroke-linejoin="round">\n    '
        + "\n    ".join(pts) + "\n  </g>\n"
        '  <g fill="currentColor" stroke="none">\n    ' + dots + "\n  </g>\n"
        "</svg>\n"
    )


TARGETS = {

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

if __name__ == "__main__":
    for rel, size in TARGETS.items():
        path = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        icon(size).save(path)
        print(f"{rel:58} {size}px")

    mark_only(512).save(os.path.join(ROOT, "app", "static", "logo-mark.png"))
    # the in-app mark has no field behind it: it sits on the app's own background
    mark_only(192).save(os.path.join(
        ROOT, "android", "app", "src", "main", "res", "drawable-nodpi", "logo_mark.png"))

    # the React Native shell
    assets = os.path.join(ROOT, "expo-app", "assets")
    os.makedirs(assets, exist_ok=True)
    icon(1024).save(os.path.join(assets, "icon.png"))
    icon(1024).save(os.path.join(assets, "adaptive-icon.png"))
    mark_only(1024).save(os.path.join(assets, "splash-mark.png"))
    print("expo assets written: icon, adaptive-icon, splash-mark")
    mark_only(512).save(os.path.join(ROOT, "docs", "logo-preview.png"))
    for name, compact in (("logo-mark.svg", False), ("logo-mark-small.svg", True)):
        with open(os.path.join(ROOT, "app", "static", name), "w", encoding="utf-8") as fh:
            fh.write(svg(compact=compact))
    print("logo-mark.png, logo-mark.svg and docs/logo-preview.png written")
