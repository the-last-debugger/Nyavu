"""Generate the PWA icons (shield mark on the app's dark background)."""
import os

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "static")
BG = (10, 16, 32)
ACCENT = (63, 184, 245)
OK = (52, 211, 153)


def shield(size: int) -> Image.Image:
    scale = 4  # supersample for clean edges
    s = size * scale
    img = Image.new("RGB", (s, s), BG)
    d = ImageDraw.Draw(img)

    # shield outline
    cx = s / 2
    top = s * 0.16
    bottom = s * 0.86
    half = s * 0.27
    pts = [
        (cx - half, top + s * 0.03),
        (cx, top),
        (cx + half, top + s * 0.03),
        (cx + half, s * 0.52),
        (cx, bottom),
        (cx - half, s * 0.52),
    ]
    d.polygon(pts, fill=(18, 34, 58), outline=ACCENT, width=int(s * 0.035))

    # check mark
    w = int(s * 0.055)
    d.line([(cx - s * 0.12, s * 0.46), (cx - s * 0.02, s * 0.57)], fill=OK, width=w)
    d.line([(cx - s * 0.02, s * 0.57), (cx + s * 0.14, s * 0.36)], fill=OK, width=w)

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    for size in (192, 512):
        path = os.path.join(OUT, f"icon-{size}.png")
        shield(size).save(path)
        print("wrote", path)


if __name__ == "__main__":
    main()
