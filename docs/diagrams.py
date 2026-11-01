"""
Generates the Chapter Three design figures.

    Figure 1  Context diagram (level 0 DFD)
    Figure 2  Level 1 data flow diagram
    Figure 3  Use case diagram
    Figure 4  Entity relationship diagram
    Figure 5  Low-fidelity interface wireframe

Drawn with matplotlib so every figure is reproducible from source.
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)

INK = "#1b2a41"
PROC = "#e3eefb"
PROC_E = "#2f6296"
ENT = "#fdf1dd"
ENT_E = "#b07d2b"
STORE = "#e8f6ea"
STORE_E = "#357a48"
GREY = "#5d6b80"
FONT = "DejaVu Sans"
MONO = "DejaVu Sans Mono"


def canvas(w, h, xlim, ylim):
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("white")
    return fig, ax


def box(ax, x, y, w, h, lines, fc, ec, fs=9.5, lw=1.3, step=0.30):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle="round,pad=0.02,rounding_size=0.12",
                                linewidth=lw, edgecolor=ec, facecolor=fc, zorder=3))
    if isinstance(lines, str):
        lines = [lines]
    y0 = y + step * (len(lines) - 1) / 2
    for i, ln in enumerate(lines):
        ax.text(x, y0 - i * step, ln, ha="center", va="center", fontsize=fs,
                color=INK, family=FONT, zorder=4,
                fontweight="bold" if i == 0 else "normal")


def store(ax, x, y, w, h, label, fs=9.5):
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, linewidth=1.3,
                           edgecolor=STORE_E, facecolor=STORE, zorder=3))
    ax.plot([x - w / 2 + 0.16, x + w / 2 - 0.16], [y + h / 2 - 0.02] * 2,
            color=STORE_E, lw=1.3, zorder=4)
    ax.text(x, y, label, ha="center", va="center", fontsize=fs, color=INK,
            family=FONT, zorder=5)


def arrow(ax, p, q, label="", *, rad=0.0, fs=8.2, color=INK, lw=1.2,
          off=(0, 0), ls="-", both=False):
    style = "<|-|>" if both else "-|>"
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=13,
                                 connectionstyle=f"arc3,rad={rad}", linewidth=lw,
                                 color=color, linestyle=ls, zorder=2,
                                 shrinkA=4, shrinkB=4))
    if label:
        mx, my = (p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=fs, color=GREY,
                family=FONT, zorder=6,
                bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=.95))


def actor(ax, x, y, label, scale=1.0):
    r = 0.19 * scale
    ax.add_patch(Circle((x, y + 0.55 * scale), r, fill=False, lw=1.4, ec=INK, zorder=3))
    ax.plot([x, x], [y + 0.36 * scale, y - 0.10 * scale], color=INK, lw=1.4, zorder=3)
    ax.plot([x - 0.28 * scale, x + 0.28 * scale], [y + 0.20 * scale] * 2,
            color=INK, lw=1.4, zorder=3)
    ax.plot([x, x - 0.20 * scale], [y - 0.10 * scale, y - 0.44 * scale],
            color=INK, lw=1.4, zorder=3)
    ax.plot([x, x + 0.20 * scale], [y - 0.10 * scale, y - 0.44 * scale],
            color=INK, lw=1.4, zorder=3)
    ax.text(x, y - 0.58 * scale, label, ha="center", va="top", fontsize=8.8,
            color=INK, family=FONT, fontweight="bold")


# --------------------------------------------------------------------------- #
def context_diagram():
    fig, ax = canvas(11.6, 7.2, (0, 11.6), (0, 7.2))
    ax.text(5.8, 6.95, "Nyavu — Context Diagram (Level 0)",
            ha="center", fontsize=11.5, color=INK, fontweight="bold", family=FONT)

    box(ax, 5.8, 3.6, 3.9, 1.55, ["0", "Nyavu", "URL Detection System"],
        PROC, PROC_E, fs=10.5)
    box(ax, 1.35, 3.6, 2.3, 0.95, ["Internet User"], ENT, ENT_E, fs=9.8)
    box(ax, 10.15, 5.9, 2.6, 1.05, ["Public URL Sources", "(phishing feeds,", "domain rankings)"],
        ENT, ENT_E, fs=8.6, step=0.28)
    box(ax, 10.15, 1.15, 2.3, 0.85, ["Administrator"], ENT, ENT_E, fs=9.8)

    arrow(ax, (2.52, 3.95), (3.82, 3.95), "submitted URL", off=(0, 0.20))
    arrow(ax, (3.82, 3.22), (2.52, 3.22), "verdict, score, reasons", off=(0, -0.24))
    arrow(ax, (9.0, 5.55), (7.05, 4.42), "labelled URL data (offline)",
          rad=-0.12, off=(0.10, 0.30))
    arrow(ax, (7.25, 3.00), (9.05, 1.45), "scan log, model metrics",
          rad=0.12, off=(0.05, -0.32))
    ax.text(5.8, 0.30, "A verdict is an assessment, never a guarantee of safety.",
            ha="center", fontsize=8.4, color=GREY, style="italic", family=FONT)
    fig.savefig(os.path.join(OUT, "fig_context.png"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def level1_dfd():
    fig, ax = canvas(12.2, 7.6, (0, 12.2), (0, 7.6))
    ax.text(6.1, 7.32, "Nyavu — Level 1 Data Flow Diagram",
            ha="center", fontsize=11.5, color=INK, fontweight="bold", family=FONT)

    box(ax, 1.20, 5.60, 2.05, 0.95, ["Internet User"], ENT, ENT_E, fs=9.4)
    box(ax, 4.30, 5.60, 2.95, 1.15, ["1.0", "URL intake and", "validation"], PROC, PROC_E, fs=9.1)
    box(ax, 8.05, 5.60, 2.95, 1.15, ["2.0", "Feature extraction", "(domain level)"], PROC, PROC_E, fs=9.1)
    box(ax, 8.05, 2.70, 2.95, 1.15, ["3.0", "Classification and", "explanation"], PROC, PROC_E, fs=9.1)
    box(ax, 2.60, 2.70, 2.95, 1.15, ["4.0", "History and", "reporting"], PROC, PROC_E, fs=9.1)

    store(ax, 4.90, 0.85, 2.55, 0.60, "D1  scans")
    store(ax, 1.20, 0.85, 2.20, 0.60, "D2  sessions")
    store(ax, 8.05, 0.85, 2.55, 0.60, "D3  trained model")

    arrow(ax, (2.25, 5.60), (2.80, 5.60), "URL", off=(0, 0.24))
    arrow(ax, (5.80, 5.60), (6.55, 5.60), "valid domain", off=(0, 0.24))
    arrow(ax, (8.05, 5.01), (8.05, 3.29), "feature vector", off=(1.10, 0))
    arrow(ax, (8.05, 1.17), (8.05, 2.11), "model, weights", off=(1.10, 0))
    arrow(ax, (6.55, 2.70), (4.10, 2.70), "verdict, score, reasons", off=(0, 0.24))
    arrow(ax, (3.85, 2.11), (4.62, 1.17), "scan record", off=(0.30, 0.18))
    arrow(ax, (2.05, 1.17), (2.30, 2.11), "user profile", off=(-0.35, 0.10), ls="--")
    arrow(ax, (1.75, 3.29), (1.06, 5.01), "history, reports", off=(-0.62, 0.05))

    ax.text(6.10, 0.12, "Dashed flow: optional account data. Model weights are read-only "
                        "at request time.",
            ha="center", fontsize=7.8, color=GREY, style="italic", family=FONT)
    fig.savefig(os.path.join(OUT, "fig_dfd_level1.png"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def use_case():
    fig, ax = canvas(11.8, 7.6, (0, 11.8), (0, 7.6))
    ax.text(5.9, 7.32, "Nyavu — Use Case Diagram",
            ha="center", fontsize=11.5, color=INK, fontweight="bold", family=FONT)

    ax.add_patch(Rectangle((2.45, 0.60), 6.95, 6.20, fill=False, ec=GREY, lw=1.2, ls="--"))
    ax.text(5.92, 6.55, "Nyavu system", ha="center", fontsize=8.6,
            color=GREY, family=FONT, style="italic")

    cases = {
        "analyse": (4.05, 5.70, "Analyse a URL"),
        "verdict": (7.75, 5.70, "View verdict and reasons"),
        "qr": (4.05, 4.62, "Scan a QR code"),
        "bulk": (7.75, 4.62, "Screen a list (bulk)"),
        "auth": (4.05, 3.54, "Register / sign in"),
        "export": (7.75, 3.54, "Export results"),
        "history": (4.05, 2.46, "View scan history"),
        "metrics": (7.75, 2.46, "Inspect model metrics"),
        "manage": (7.75, 1.38, "Manage users"),
    }
    for key, (x, y, label) in cases.items():
        ax.add_patch(Ellipse((x, y), 2.55, 0.86, facecolor=PROC, edgecolor=PROC_E,
                             lw=1.2, zorder=3))
        ax.text(x, y, label, ha="center", va="center", fontsize=8.1, color=INK,
                family=FONT, zorder=4)

    actor(ax, 1.00, 5.55, "Web user")
    actor(ax, 1.00, 2.65, "Registered\nuser")
    actor(ax, 10.75, 2.15, "Administrator")

    def link(a, b, ls="-"):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-", lw=1.1, color=INK,
                                     zorder=2, shrinkA=0, shrinkB=0, linestyle=ls))

    link((1.42, 5.45), (2.78, 5.66))
    link((1.38, 5.18), (2.80, 4.72))
    link((1.42, 2.55), (2.78, 3.50))
    link((1.38, 2.28), (2.78, 2.50))
    link((10.32, 2.05), (9.02, 2.42))
    link((10.32, 1.70), (9.02, 1.42))
    link((10.20, 2.55), (9.02, 3.45))

    # include relationships
    ax.add_patch(FancyArrowPatch((5.20, 5.52), (6.48, 5.62), arrowstyle="-|>",
                                 mutation_scale=11, lw=1.0, color=GREY, ls="--",
                                 zorder=2))
    ax.add_patch(FancyArrowPatch((5.18, 4.80), (6.52, 5.42), arrowstyle="-|>",
                                 mutation_scale=11, lw=1.0, color=GREY, ls="--",
                                 zorder=2))
    ax.text(5.74, 5.20, "Â«includeÂ»", fontsize=7.2, color=GREY, family=FONT,
            ha="center", style="italic", rotation=-8)
    ax.text(5.62, 5.86, "Â«includeÂ»", fontsize=7.2, color=GREY, family=FONT,
            ha="center", style="italic")

    fig.savefig(os.path.join(OUT, "fig_usecase.png"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def erd():
    fig, ax = canvas(11.8, 7.8, (0, 11.8), (0, 7.8))
    ax.text(5.9, 7.50, "Nyavu — Entity Relationship Diagram",
            ha="center", fontsize=11.5, color=INK, fontweight="bold", family=FONT)

    def entity(x, y_top, w, name, attrs):
        head = 0.42
        row_h = 0.29
        h = head + row_h * len(attrs) + 0.16
        y = y_top - h / 2
        ax.add_patch(Rectangle((x - w / 2, y_top - h), w, h, facecolor="white",
                               edgecolor=PROC_E, lw=1.3, zorder=3))
        ax.add_patch(Rectangle((x - w / 2, y_top - head), w, head, facecolor=PROC,
                               edgecolor=PROC_E, lw=1.3, zorder=4))
        ax.text(x, y_top - head / 2, name, ha="center", va="center", fontsize=9.0,
                fontweight="bold", color=INK, family=FONT, zorder=5)
        for i, (a, kind) in enumerate(attrs):
            yy = y_top - head - 0.24 - i * row_h
            prefix = {"pk": "PK ", "fk": "FK ", "": "   "}[kind]
            ax.text(x - w / 2 + 0.15, yy, prefix + a, ha="left", va="center",
                    fontsize=7.7, color=INK if kind else GREY, family=MONO, zorder=5,
                    fontweight="bold" if kind == "pk" else "normal")
        return {"x": x, "top": y_top, "bottom": y_top - h, "w": w,
                "left": x - w / 2, "right": x + w / 2}

    users = entity(2.10, 6.85, 3.10, "users", [
        ("id", "pk"), ("email", ""), ("full_name", ""), ("password_hash", ""),
        ("created_at", "")])
    sessions = entity(2.10, 4.05, 3.10, "sessions", [
        ("token", "pk"), ("user_id", "fk"), ("created_at", "")])
    scans = entity(8.55, 6.85, 4.30, "scans", [
        ("id", "pk"), ("user_id", "fk"), ("url", ""), ("domain", ""),
        ("verdict", ""), ("probability", ""), ("created_at", "")])
    models = entity(8.55, 3.55, 4.30, "models", [
        ("id", "pk"), ("name", ""), ("version", ""), ("accuracy", ""),
        ("trained_at", ""), ("is_active", "")])

    def vline(x, y1, y2):
        ax.plot([x, x], [y1, y2], color=INK, lw=1.2, zorder=2)

    def hline(x1, x2, y):
        ax.plot([x1, x2], [y, y], color=INK, lw=1.2, zorder=2)

    # users 1 -- n sessions
    vline(2.10, users["bottom"], sessions["top"])
    ax.text(2.32, (users["bottom"] + sessions["top"]) / 2 + 0.14, "1", fontsize=9,
            color=INK, fontweight="bold", family=FONT)
    ax.text(2.32, (users["bottom"] + sessions["top"]) / 2 - 0.20, "0..*", fontsize=9,
            color=INK, fontweight="bold", family=FONT)
    ax.text(2.60, (users["bottom"] + sessions["top"]) / 2, "holds", fontsize=8.0,
            color=GREY, family=FONT, style="italic", va="center")

    # users 1 -- n scans
    hline(users["right"], scans["left"], 6.30)
    ax.text(users["right"] + 0.30, 6.46, "1", fontsize=9, color=INK,
            fontweight="bold", family=FONT)
    ax.text(scans["left"] - 0.42, 6.46, "0..*", fontsize=9, color=INK,
            fontweight="bold", family=FONT)
    ax.text((users["right"] + scans["left"]) / 2, 6.06, "records", fontsize=8.0,
            color=GREY, family=FONT, style="italic", ha="center")


    # scans n -- 1 models  (batch label, dashed)
    ax.add_patch(FancyArrowPatch((8.55, scans["bottom"]), (8.55, models["top"]),
                                 arrowstyle="-", lw=1.0, color=GREY, ls=":",
                                 zorder=2))
    ax.text(8.80, (scans["bottom"] + models["top"]) / 2,
            "produced by a\nversioned model", fontsize=7.6, color=GREY,
            family=FONT, style="italic", ha="left", va="center")

    ax.text(5.9, 0.55, "Registrable domain is stored alongside the URL so that scans "
                       "can be grouped by domain.", fontsize=7.6, color=GREY,
            style="italic", family=FONT, ha="center")
    fig.savefig(os.path.join(OUT, "fig_erd.png"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def wireframe():
    fig, ax = canvas(10.6, 7.4, (0, 10.6), (0, 7.4))
    ax.text(5.3, 7.15, "Nyavu — Low-fidelity wireframe (detector screen)",
            ha="center", fontsize=11.0, color=INK, fontweight="bold", family=FONT)

    def rect(x, y, w, h, fc="#ffffff", ec="#9aa7b8", lw=1.0, ls="-", r=0.03):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle=f"round,pad=0.02,rounding_size={r}",
                                    facecolor=fc, edgecolor=ec, lw=lw, linestyle=ls, zorder=2))

    rect(0.45, 0.40, 9.7, 6.30, fc="#fbfcfd", lw=1.4)
    rect(0.45, 6.18, 9.7, 0.52, fc="#eef1f5")
    ax.text(0.68, 6.44, "nyavu.app", fontsize=7.6, color=GREY, family=MONO)

    rect(0.68, 5.42, 9.25, 0.55, fc="#eef1f5")
    ax.text(0.86, 5.69, "Nyavu", fontsize=9.0, fontweight="bold", color=INK, family=FONT)
    ax.text(4.35, 5.69, "Detector    Bulk scan    History    Model", fontsize=7.4,
            color=GREY, family=FONT)
    rect(8.55, 5.55, 1.20, 0.28, fc="#dfe6ef")
    ax.text(9.15, 5.69, "Sign in", fontsize=7.0, color=GREY, ha="center", family=FONT)

    ax.text(0.72, 4.85, "Check a link before you click it.", fontsize=10.5,
            fontweight="bold", color=INK, family=FONT)
    ax.text(0.72, 4.52, "Paste a URL. The model scores it and explains why.",
            fontsize=7.8, color=GREY, family=FONT)

    rect(0.72, 3.78, 6.45, 0.50)
    ax.text(0.90, 4.03, "https://example.com/login", fontsize=8.0, color=GREY,
            family=MONO, va="center")
    rect(7.42, 3.78, 1.45, 0.50, fc="#dbe9f8", ec="#7aa7d6")
    ax.text(8.15, 4.03, "Analyse", fontsize=8.2, color="#1c4a7a", ha="center",
            fontweight="bold", family=FONT, va="center")
    rect(9.02, 3.78, 0.50, 0.50)
    ax.text(9.27, 4.03, "â–£", fontsize=8.6, color=GREY, ha="center", family=FONT, va="center")

    for x, w in ((0.72, 1.35), (2.20, 1.95), (4.28, 1.70)):
        rect(x, 3.24, w, 0.32, fc="#f2f5f9")
        ax.text(x + w / 2, 3.40, "sample URL", fontsize=6.6, color=GREY, ha="center",
                family=FONT, va="center")

    rect(0.72, 1.00, 8.80, 2.02, fc="#fbfcfd", ls="--")
    ax.add_patch(Circle((1.62, 2.01), 0.50, fill=False, ec="#9aa7b8", lw=1.2, ls="--"))
    ax.text(1.62, 2.01, "risk\nscore", fontsize=6.6, color=GREY, ha="center",
            va="center", family=FONT)
    ax.text(2.62, 2.56, "Verdict band and headline", fontsize=8.2, color=INK, family=FONT)
    ax.text(2.62, 2.18, "submitted URL", fontsize=7.0, color=GREY, family=FONT)
    for i in range(3):
        rect(2.62, 1.55 - i * 0.26, 6.40 - i * 0.75, 0.18, fc="#eef1f5", lw=0)
        ax.text(2.70, 1.64 - i * 0.26, f"reason {i + 1}", fontsize=6.4, color=GREY,
                va="center", family=FONT)

    ax.text(5.3, 0.14, "Low-fidelity sketch â€” layout only; visual design follows the brand system.",
            ha="center", fontsize=7.4, color=GREY, style="italic", family=FONT)
    fig.savefig(os.path.join(OUT, "fig_wireframe.png"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def concept_map():
    fig, ax = canvas(12.2, 7.4, (0, 12.2), (0, 7.4))
    ax.text(6.1, 7.15, "Nyavu — Concept map",
            ha="center", fontsize=11.5, color=INK, fontweight="bold", family=FONT)

    for x, label in ((2.05, "INDEPENDENT VARIABLES"),
                     (6.10, "PROPOSED SYSTEM"),
                     (10.15, "DEPENDENT VARIABLES")):
        ax.text(x, 6.60, label, ha="center", fontsize=8.0, color=GREY,
                family=FONT, fontweight="bold")

    ivs = [
        (2.05, 5.55, ["URL lexical and structural", "characteristics (length, digits,", "hyphens, entropy, TLD)"]),
        (2.05, 3.75, ["Domain-level signals", "(brand proximity, typosquatting,", "character substitution)"]),
        (2.05, 1.95, ["Labelled training data", "(phishing feeds and", "domain rankings)"]),
    ]
    for x, y, lines in ivs:
        box(ax, x, y, 3.10, 1.10, lines, PROC, PROC_E, fs=7.6, step=0.24)

    dv = [
        (10.15, 5.55, ["Classification accuracy"]),
        (10.15, 3.75, ["False-positive rate"]),
        (10.15, 1.95, ["Explanation clarity and", "user trust"]),
    ]
    for x, y, lines in dv:
        box(ax, x, y, 2.90, 1.00, lines, ENT, ENT_E, fs=8.0, step=0.24)

    # system column
    ax.add_patch(FancyBboxPatch((4.70, 1.40), 2.80, 4.75,
                                boxstyle="round,pad=0.02,rounding_size=0.14",
                                facecolor="#f4f8fd", edgecolor=PROC_E, lw=1.4, zorder=2))
    stages = [(5.55, "1  Feature extraction"),
              (3.95, "2  Classification model"),
              (2.35, "3  Explanation layer")]
    for y, label in stages:
        box(ax, 6.10, y, 2.45, 0.72, [label], "white", PROC_E, fs=7.8)
    arrow(ax, (6.10, 5.19), (6.10, 4.31), "", lw=1.0)
    arrow(ax, (6.10, 3.59), (6.10, 2.71), "", lw=1.0)

    for (_x, y, _l) in ivs:
        arrow(ax, (3.60, y), (4.70, 3.90 if y > 4 else y), "", rad=0.0, color=GREY, lw=1.0)
    for (_x, y, _l) in dv:
        arrow(ax, (7.50, 3.90 if y > 4 else y), (8.70, y), "", rad=0.0, color=GREY, lw=1.0)

    box(ax, 6.10, 0.55, 2.90, 0.62, ["Phishing tactics evolve"], "#fdf1dd", ENT_E, fs=7.6)
    arrow(ax, (6.10, 0.88), (6.10, 1.38), "", rad=0.0, color=GREY, lw=1.0, ls="--")
    ax.text(6.28, 1.12, "moderates", fontsize=6.8, color=GREY, family=FONT, style="italic")

    ax.text(6.10, 0.12, "Phishing characteristics drive the classifier, whose output "
                        "determines detection, false positives and trust.",
            ha="center", fontsize=7.4, color=GREY, style="italic", family=FONT)
    fig.savefig(os.path.join(OUT, "fig_concept_map.png"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    context_diagram()
    level1_dfd()
    use_case()
    erd()
    wireframe()
    concept_map()
    print("figures written to", OUT)
