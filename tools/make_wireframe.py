"""
The low-fidelity wireframe for the report, drawn to match the product as delivered.

It is deliberately grey and loose: a wireframe that looks like a screenshot stops being a
wireframe. What it does carry is the real structure and the real words, because the previous
figure said "Check a link before you click it" and showed a single result panel, and both had
stopped being true.

Run: python tools/make_wireframe.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1672, 1179
SCALE = 1

INK = (58, 62, 58)
SOFT = (120, 126, 120)
FAINT = (170, 176, 170)
LINE = (140, 146, 140)
PAPER = (252, 253, 251)
WASH = (238, 241, 236)
BAND = (226, 231, 226)


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def dashed(draw, box, colour=FAINT, dash=7, gap=5, width=2):
    x0, y0, x1, y1 = box
    for x in range(x0, x1, dash + gap):
        draw.line([(x, y0), (min(x + dash, x1), y0)], fill=colour, width=width)
        draw.line([(x, y1), (min(x + dash, x1), y1)], fill=colour, width=width)
    for y in range(y0, y1, dash + gap):
        draw.line([(x0, y), (x0, min(y + dash, y1))], fill=colour, width=width)
        draw.line([(x1, y), (x1, min(y + dash, y1))], fill=colour, width=width)


def box(draw, box_coords, radius=10, fill=None, outline=LINE, width=2):
    draw.rounded_rectangle(box_coords, radius=radius, fill=fill, outline=outline, width=width)


def label(draw, xy, text, size=17, bold=False, colour=INK, anchor="la"):
    draw.text(xy, text, font=font(size, bold), fill=colour, anchor=anchor)


def build():
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    label(draw, (W // 2, 40), "Nyavu — low-fidelity wireframe (detector screen)",
          size=30, bold=True, colour=INK, anchor="ma")

    # browser chrome
    chrome = (84, 92, W - 84, H - 72)
    box(draw, chrome, radius=14, outline=SOFT, width=2)
    draw.line([(chrome[0], 140), (chrome[2], 140)], fill=SOFT, width=2)
    label(draw, (108, 106), "nyavu.app", size=17, colour=SOFT)
    for i in range(3):
        draw.ellipse([(chrome[2] - 96 + i * 26, 106), (chrome[2] - 82 + i * 26, 120)],
                     outline=FAINT, width=2)

    # header: mark, wordmark, navigation, account
    head_y = 176
    draw.ellipse([(108, head_y), (140, head_y + 32)], outline=SOFT, width=2)
    draw.line([(124, head_y + 4), (124, head_y + 28)], fill=FAINT, width=1)
    label(draw, (154, head_y + 4), "Nyavu", size=24, bold=True)
    nav = ["Detector", "Bulk scan", "History", "Model"]
    nav_x = 420
    for item in nav:
        label(draw, (nav_x, head_y + 8), item, size=17,
              colour=INK if item == "Detector" else SOFT)
        nav_x += len(item) * 10 + 44
    box(draw, (W - 300, head_y - 4, W - 168, head_y + 44), radius=22, outline=SOFT)
    label(draw, ((W - 300 + W - 168) // 2, head_y + 8), "Sign in", size=17, colour=SOFT, anchor="ma")

    # hero
    label(draw, (108, 250), "Read the address", size=40, bold=True)
    label(draw, (108, 300), "before you trust it.", size=40, bold=True)
    label(draw, (108, 366), "Paste a link. Nyavu reads the name the way you should:", size=17, colour=SOFT)
    label(draw, (108, 392), "from the right, where it counts.", size=17, colour=SOFT)

    # the scanner: one field, actions beneath on a phone, beside on a desktop
    card = (108, 436, W - 108, 540)
    box(draw, card, radius=18, fill=WASH, outline=LINE)
    draw.arc([(132, 470), (156, 494)], 200, 20, fill=SOFT, width=2)
    draw.arc([(140, 478), (164, 502)], 200, 20, fill=SOFT, width=2)
    label(draw, (184, 476), "https://example.com/login", size=19, colour=SOFT)
    box(draw, (W - 372, 456, W - 236, 520), radius=26, fill=BAND, outline=LINE)
    label(draw, ((W - 372 + W - 236) // 2, 476), "Analyse", size=18, bold=True, anchor="ma")
    box(draw, (W - 214, 456, W - 148, 520), radius=16, outline=LINE)
    for dx, dy in ((0, 0), (34, 0), (0, 34), (34, 34)):
        draw.line([(W - 190 + dx, 474 + dy), (W - 176 + dx, 474 + dy)], fill=SOFT, width=2)
        draw.line([(W - 190 + dx, 474 + dy), (W - 190 + dx, 488 + dy)], fill=SOFT, width=2)
    label(draw, (W - 190 + 34, 488), "", size=12)

    # sample addresses
    label(draw, (108, 566), "Or try one", size=16, colour=SOFT)
    samples = ["safaricom.co.ke", "safaricom-secure-login.tk",
               "mpesa.co.ke.verify-account.top", "197.248.11.9"]
    x = 226
    for sample in samples:
        width = len(sample) * 9 + 34
        box(draw, (x, 552, x + width, 590), radius=19, outline=FAINT)
        label(draw, (x + 17, 560), sample, size=15, colour=SOFT)
        x += width + 18

    # the verdict, which the product shows as a dialog over the page
    dialog = (150, 618, W - 150, H - 120)
    dashed(draw, dialog)
    label(draw, (dialog[0] + 28, 636), "Verdict dialog (opens over the page)", size=17, bold=True, colour=SOFT)
    label(draw, (dialog[0] + 28, 674), "Band and headline", size=26, bold=True)
    label(draw, (dialog[0] + 28, 714), "submitted address", size=16, colour=SOFT)
    label(draw, (dialog[0] + 28, 744), "risk out of 100", size=16, colour=SOFT)
    draw.line([(dialog[0] + 28, 776), (dialog[2] - 28, 776)], fill=FAINT, width=2)

    # the dissection: three pieces, each with its note
    piece_x = dialog[0] + 28
    for text, note in (("https://", "encrypted"),
                       ("mpesa.", "a label the owner can invent"),
                       (".top", "cheap and abused")):
        label(draw, (piece_x, 796), text, size=18)
        label(draw, (piece_x, 824), note, size=14, colour=SOFT)
        piece_x += max(len(text), len(note)) * 8 + 60

    label(draw, (dialog[0] + 28, 866), "Read it from the right. The name before the ending is the one somebody bought.",
          size=15, colour=SOFT)

    # reasons, as rows
    for index in range(3):
        top = 906 + index * 44
        box(draw, (dialog[0] + 28, top, dialog[2] - 28, top + 34), radius=10, outline=FAINT)
        label(draw, (dialog[0] + 42, top + 8), f"{index + 1}", size=14, colour=SOFT)
        label(draw, (dialog[0] + 66, top + 8), "reason, in a sentence a non-specialist can act on",
              size=15, colour=SOFT)

    label(draw, (W // 2, H - 44),
          "Wireframe: structure and wording only. Colour, type and motion follow the brand system.",
          size=16, colour=SOFT, anchor="ma")

    out = os.path.join(ROOT, "docs", "wireframe-detector.png")
    img.save(out)
    print("wrote", out, img.size)


if __name__ == "__main__":
    build()
