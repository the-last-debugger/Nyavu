"""Builds the staged submissions: Chapters 1-2, and Chapters 1-4.

Each chapter starts its own section so the running head changes with the chapter while
page numbering continues unbroken. The title page carries neither a header nor a number.

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
import build_ch5  # noqa: E402
from build_full import TITLE, certification, declaration, title_page  # noqa: E402
from docbuild import Paper  # noqa: E402
from references import REFERENCES  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))


def build(upto: int):
    p = Paper(TITLE)

    title_page(p)                       # section 1: bare title page

    front = p.new_section(fmt="lowerRoman", start=2)   # title counts as i, unnumbered
    p.header_text(front, "KABARAK UNIVERSITY")

    declaration(p, page_break=False)
    certification(p)

    chapters = [
        (build_ch1.body, "CHAPTER ONE: INTRODUCTION"),
        (build_ch2.body, "CHAPTER TWO: LITERATURE REVIEW"),
        (build_ch3.body, "CHAPTER THREE: METHODOLOGY AND SYSTEM DESIGN"),
        (build_ch4.body, "CHAPTER FOUR: SYSTEM IMPLEMENTATION AND DEPLOYMENT"),
        (build_ch5.body, "CHAPTER FIVE: SYSTEM RECOMMENDATIONS AND CONCLUSIONS"),
    ]
    for index, (body, heading) in enumerate(chapters[:upto]):
        sec = p.new_section(fmt="decimal", start=1 if index == 0 else None)
        p.header_text(sec, heading)
        body(p, page_break=False, include_references=False)

    ref_sec = p.new_section(fmt="decimal", start=None)
    p.header_text(ref_sec, "REFERENCES")
    p.h1("REFERENCES", page_break=False)
    p.references(REFERENCES)

    suffix = os.environ.get("NYAVU_SUFFIX", "")
    name = f"Team_Project_Chapters_1-{upto}{suffix}.docx"
    path = os.path.join(OUT, name)
    p.save(path)
    words = sum(len(par.text.split()) for par in p.doc.paragraphs)
    print(f"wrote {name}: tables={len(p.doc.tables)} words~{words:,}")
    return path


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    build(n)
