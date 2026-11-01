"""
Overlap check: compares the generated chapters against the source documents the team
was given (project guidelines, marking scheme, timeline, outline, supervision form).

This is not Turnitin. Turnitin compares against a very large index of published and
submitted work that we cannot reach from here. What this check *can* do is catch the
realistic hazard: text copied or lightly paraphrased from the provided templates,
which is what most often pushes a project over the similarity threshold.

Method: 8-word shingles. A shingle present in both a chapter and a source document is
reported, with the sentence it came from.
"""
from __future__ import annotations

import os
import re

from docx import Document

DOCS = r"C:\dev\phishguard\docs"
SRC = r"C:\dev\_pdf_extract"

CHAPTERS = [
    "Chapter_One_Submission.docx",
    "Chapter_Two_Literature_Review.docx",
    "Chapter_Three_Methodology.docx",
    "Chapter_Four_Implementation.docx",
    "Chapter_Five_Conclusions.docx",
]

SHINGLE = 8


def normalise(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def shingles(words):
    return {" ".join(words[i:i + SHINGLE]) for i in range(len(words) - SHINGLE + 1)}


def main() -> None:
    sources = {}
    for name in os.listdir(SRC):
        if name.endswith(".txt"):
            sources[name] = normalise(open(os.path.join(SRC, name), encoding="utf-8").read())
    print(f"sources loaded: {len(sources)}")

    total_flagged = 0
    for chapter in CHAPTERS:
        path = os.path.join(DOCS, chapter)
        if not os.path.exists(path):
            print(f"missing {chapter}")
            continue
        doc = Document(path)
        text = normalise(" ".join(p.text for p in doc.paragraphs))
        words = text.split()
        if len(words) < SHINGLE:
            continue
        ours = shingles(words)
        overlap = {}
        for name, src_words in sources.items():
            src_sh = shingles(src_words.split())
            hit = ours & src_sh
            if hit:
                overlap[name] = hit
        flagged = sum(len(v) for v in overlap.values())
        total_flagged += flagged
        pct = 100 * flagged / max(len(ours), 1)
        print(f"\n{chapter}: {len(words):,} words, {len(ours):,} shingles, "
              f"{flagged} matched ({pct:.2f}% of shingles)")
        for name, hits in overlap.items():
            print(f"   against {name}: {len(hits)}")
            for s in list(hits)[:3]:
                print(f"      \"{s}\"")

    print(f"\nTOTAL matched shingles across chapters: {total_flagged}")
    if total_flagged == 0:
        print("No 8-word sequence in the chapters also appears in the provided documents.")
    else:
        print("Review each quoted shingle above and rewrite it in your own words.")


if __name__ == "__main__":
    main()
