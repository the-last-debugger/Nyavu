"""Builds the staged submissions: Chapters 1-2, and Chapters 1-4.

Usage:  python build_combined.py [2|4]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_ch1  # noqa: E402
import build_ch2  # noqa: E402
import build_ch3  # noqa: E402
import build_ch4  # noqa: E402
from build_full import TITLE, title_page  # noqa: E402
from docbuild import Paper  # noqa: E402
from references import REFERENCES  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))


def build(upto: int):
    p = Paper(TITLE)
    p.set_page_numbering(p.doc.sections[0], fmt="decimal", start=1)
    p.footer_page_numbers(p.doc.sections[0])

    title_page(p)

    build_ch1.body(p, page_break=True, include_references=False)
    if upto >= 2:
        build_ch2.body(p, page_break=True, include_references=False)
    if upto >= 3:
        build_ch3.body(p, page_break=True, include_references=False)
    if upto >= 4:
        build_ch4.body(p, page_break=True, include_references=False)

    p.h1("REFERENCES", page_break=True)
    p.references(REFERENCES)

    name = f"Nyavu_Chapters_1-{upto}.docx"
    path = os.path.join(OUT, name)
    p.save(path)
    words = sum(len(par.text.split()) for par in p.doc.paragraphs)
    print(f"wrote {name}: tables={len(p.doc.tables)} words~{words:,}")
    return path


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    build(n)
