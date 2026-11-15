"""Builds each chapter as a standalone document, with a running head and scoped references."""
from __future__ import annotations

import os
import re
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


def cited_only(text: str, refs: list[str]) -> list[str]:
    """Keep only the references whose author surname appears in this chapter."""
    low = text.lower()
    kept = []
    for ref in refs:
        head = ref.split(".")[0]
        surname = head.split(",")[0].strip()
        if surname.lower().startswith("anti-phishing"):
            pattern = r"anti-phishing"
        elif surname.lower().startswith("interisle"):
            pattern = r"interisle"
        else:
            pattern = r"\b" + re.escape(surname.split()[-1]) + r"\b"
        if re.search(pattern, low, re.IGNORECASE):
            kept.append(ref)
    return kept


def build(body_fn, filename: str, heading: str) -> str:
    p = Paper(TITLE)                    # section 1: bare title page

    front = p.new_section(fmt="lowerRoman", start=2)   # title counts as i, unnumbered
    p.header_text(front, "KABARAK UNIVERSITY")
    declaration(p, page_break=False)
    certification(p)

    body = p.new_section(fmt="decimal", start=1)
    p.header_text(body, heading)
    body_fn(p, page_break=False, include_references=False)

    text = " ".join(x.text for x in p.doc.paragraphs)
    refs = cited_only(text, REFERENCES)
    if refs:
        refsec = p.new_section(fmt="decimal", start=None)
        p.header_text(refsec, "REFERENCES")
        p.h1("REFERENCES", page_break=False)
        p.references(refs)

    path = os.path.join(OUT, filename)
    p.save(path)
    print(f"    {filename}: {len(refs)} of {len(REFERENCES)} references cited")
    return filename


def main() -> None:
    jobs = [
        (build_ch1.body, "Team_Project_Chapter_One.docx", "CHAPTER ONE: INTRODUCTION"),
        (build_ch2.body, "Team_Project_Chapter_Two.docx", "CHAPTER TWO: LITERATURE REVIEW"),
        (build_ch3.body, "Team_Project_Chapter_Three.docx",
         "CHAPTER THREE: METHODOLOGY AND SYSTEM DESIGN"),
        (build_ch4.body, "Team_Project_Chapter_Four.docx",
         "CHAPTER FOUR: SYSTEM IMPLEMENTATION AND DEPLOYMENT"),
        (build_ch5.body, "Team_Project_Chapter_Five.docx",
         "CHAPTER FIVE: SYSTEM RECOMMENDATIONS AND CONCLUSIONS"),
    ]
    for fn, name, heading in jobs:
        print("wrote", build(fn, name, heading))


if __name__ == "__main__":
    main()
