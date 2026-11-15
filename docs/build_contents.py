"""Two-pass build that replaces the TOC and lists with static, correct page numbers.

Pass 1 builds the document and converts it to PDF. Page numbers are read from the PDF,
so they reflect what a reader will actually see. Pass 2 rebuilds the document with the
contents and lists as literal text - no fields, so nothing needs updating in Word or
LibreOffice.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = r"C:\dev\projects\products\phishguard\docs"
sys.path.insert(0, HERE)

from docx import Document  # noqa: E402
from pypdf import PdfReader  # noqa: E402

NODE = (r"C:\Users\tuyaa\AppData\Local\Programs\DeepSeek Harness\resources\runtime"
        r"\primary-runtime\dependencies\node\bin\node.exe")
CLI = (r"C:\Users\tuyaa\AppData\Local\Programs\DeepSeek Harness\resources\app.asar.unpacked"
       r"\dsh\node_modules\@deepseek-ai\libreoffice-kit\lib\cli.js")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def convert(docx_path: str, pdf_path: str) -> None:
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    subprocess.run([NODE, CLI, "convert", "--input", docx_path, "--output", pdf_path],
                   check=True, capture_output=True)


def page_texts(pdf_path: str):
    return [norm(p.extract_text() or "") for p in PdfReader(pdf_path).pages]


def find_page(pages, needle):
    target = norm(needle)
    if not target:
        return None
    for i, t in enumerate(pages, 1):
        if target in t:
            return i
    return None


def build(mode: str, suffix: str, topc: str = ""):
    env = dict(os.environ)
    env["NYAVU_MODE"] = mode
    env["NYAVU_SUFFIX"] = suffix
    env["NYAVU_TOC"] = topc
    subprocess.run([sys.executable, os.path.join(HERE, "build_full.py")],
                   cwd=HERE, env=env, check=True, capture_output=True)
    return os.path.join(HERE, f"Team_Project_Full_Report{suffix}.docx")


def collect(docx_path: str):
    """Captions carry their number as a field, so the number is not in paragraph.text.

    They are sequential in the document, so they are numbered here in order of
    appearance and the caption wording is matched against the PDF for its page.
    """
    d = Document(docx_path)
    heads, tables, figures = [], [], []
    t_no = f_no = 0
    for p in d.paragraphs:
        st = p.style.name
        text = p.text.strip()
        if st in ("Heading 1", "Heading 2", "Heading 3") and text:
            heads.append((int(st[-1]), text))
            continue
        m = re.match(r"^(Table|Figure)\s*\d*\s*:\s*(.+)$", text)
        if m:
            kind, body = m.group(1), m.group(2)
            if kind == "Table":
                t_no += 1
                tables.append({"label": f"Table {t_no}", "body": body})
            else:
                f_no += 1
                figures.append({"label": f"Figure {f_no}", "body": body})
    return heads, tables, figures


def romanise(n: int) -> str:
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, sym in vals:
        while n >= v:
            out += sym
            n -= v
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "four_merged"
    suffix = sys.argv[2] if len(sys.argv) > 2 else "_4ch_MERGED"

    # pass 1: no static contents yet
    docx1 = build(mode, suffix + "_pass1", "")
    pdf1 = docx1.replace(".docx", ".pdf")
    convert(docx1, pdf1)
    pages = page_texts(pdf1)

    body_start = find_page(pages, "CHAPTER ONE: INTRODUCTION")
    if not body_start:
        raise SystemExit("could not locate the body")

    heads, tables, figures = collect(docx1)

    entries = []
    for level, text in heads:
        idx = find_page(pages, text)
        if idx is None:
            continue
        if idx >= body_start:
            label = str(idx - body_start + 1)
        else:
            label = romanise(idx)
        entries.append({"level": level, "text": text, "page": label})

    lot = []
    for cap in tables:
        idx = find_page(pages, cap["body"])
        if idx:
            lot.append({"text": f"{cap['label']}: {cap['body']}",
                        "page": str(idx - body_start + 1)})

    lof = []
    for cap in figures:
        idx = find_page(pages, cap["body"])
        if idx:
            lof.append({"text": f"{cap['label']}: {cap['body']}",
                        "page": str(idx - body_start + 1)})

    data = {"entries": entries, "lot": lot, "lof": lof}
    json_path = os.path.join(HERE, f"contents{suffix}.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)

    print(f"headings mapped: {len(entries)} | tables: {len(lot)} | figures: {len(lof)}")

    # pass 2: rebuild with static contents
    docx2 = build(mode, suffix, json_path)
    if os.path.exists(docx1):
        os.remove(docx1)
    if os.path.exists(pdf1):
        os.remove(pdf1)
    pdf2 = docx2.replace(".docx", ".pdf")
    convert(docx2, pdf2)
    print("final:", docx2)
    print("final:", pdf2)


if __name__ == "__main__":
    main()
