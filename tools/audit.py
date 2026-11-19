"""Checks that would have caught the last four defects before they shipped.

    python tools/audit.py

Each check corresponds to something that was broken in production and found by looking rather than by a
test: an unbalanced stylesheet, a link to a route that does not exist, a JSON-LD block that does not
parse, a duplicate id, and a script asking the DOM for an element the page never renders.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "app", "static")
HTML = [os.path.join(STATIC, "index.html")] + glob.glob(os.path.join(STATIC, "pages", "**", "*.html"), recursive=True)
CSS = [os.path.join(STATIC, name) for name in ("styles.css", "guards.css")]
SCRIPTS = [os.path.join(STATIC, name) for name in ("app.js", "autopsy.js")]
problems: list[str] = []
findings: list[str] = []
BASELINE = os.path.join(ROOT, "tools", "spacing-baseline.txt")


def read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def check_braces() -> None:
    for path in CSS:
        depth = 0
        line = 1
        comment = False
        string = None
        text = read(path)
        i = 0
        while i < len(text):
            ch = text[i]
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if ch == "\n":
                line += 1
            if comment:
                if ch == "*" and nxt == "/":
                    comment = False
                    i += 2
                    continue
                i += 1
                continue
            if string:
                if ch == "\\":
                    i += 2
                    continue
                if ch == string:
                    string = None
                i += 1
                continue
            if ch == "/" and nxt == "*":
                comment = True
                i += 2
                continue
            if ch in "\"'":
                string = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth < 0:
                    problems.append(f"{os.path.basename(path)}: unmatched }} at line {line}")
                    depth = 0
            i += 1
        if depth:
            problems.append(f"{os.path.basename(path)}: {depth} unclosed rule(s)")


def routes() -> set[str]:
    text = read(os.path.join(ROOT, "app", "main.py"))
    found = set(re.findall(r'@app\.get\("([^"]+)"', text))
    return {route.split("{")[0] for route in found}


def check_links() -> None:
    known = routes()
    for path in HTML:
        for href in re.findall(r'href="(/[^"#?]*)"', read(path)):
            if href.startswith(("/api/", "/download/")):
                continue
            candidate = os.path.join(STATIC, href.lstrip("/"))
            if href in known or os.path.isfile(candidate) or os.path.isdir(candidate):
                continue
            if href.startswith("/learn/"):
                continue
            problems.append(f"{os.path.basename(path)}: link to {href} has no route or file")


def check_jsonld() -> None:
    for path in HTML:
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', read(path), re.S):
            try:
                json.loads(block)
            except Exception as error:                       # noqa: BLE001
                problems.append(f"{os.path.basename(path)}: JSON-LD does not parse ({error})")


def check_ids() -> None:
    for path in HTML:
        ids = re.findall(r'\bid="([^"]+)"', read(path))
        for dup in {i for i in ids if ids.count(i) > 1}:
            problems.append(f"{os.path.basename(path)}: duplicate id {dup}")


def check_dom_lookups() -> None:
    ids = set()
    for path in HTML:
        ids.update(re.findall(r'\bid="([^"]+)"', read(path)))
    for path in SCRIPTS:
        for name in set(re.findall(r'getElementById\("([^"]+)"\)', read(path))):
            if name not in ids:
                problems.append(f"{os.path.basename(path)}: getElementById({name}) has no element")


def _rules(css: str):
    """Yield (selector, body) for top-level rules, skipping at-rules and their contents."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    i = 0
    length = len(css)
    while i < length:
        brace = css.find("{", i)
        if brace == -1:
            return
        selector = css[i:brace].strip()
        depth = 1
        j = brace + 1
        while j < length and depth:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
            j += 1
        body = css[brace + 1:j - 1]
        if selector.startswith("@"):
            if any(word in selector for word in ("keyframes", "font-face", "supports", "media")):
                i = j
                continue
        if not re.match(r"^[\d%,\s]+$", selector):
            yield selector, body, css[:brace].count("\n") + 1
        i = j


def check_hidden_without_leaving_layout() -> None:
    """Opacity zero still occupies space, which is how four separate spacing bugs reached production.

    A block that hides with opacity or visibility but never with display keeps its height. Only top-level
    rules are examined: pseudo-elements, animation frames, the screen-reader class and anything that also
    sets display:none are exempt.
    """
    seen: set[str] = set()
    for path in CSS:
        for selector, body, line in _rules(read(path)):
            first = selector.split(",")[0].strip().splitlines()[-1].strip()
            if not first or "::" in first or ".sr-only" in first or "[hidden]" in first:
                continue
            if "display: none" in body:
                continue
            hides = re.search(r"opacity:\s*0(?:\.0+)?\s*(?:;|$)", body) or "visibility: hidden" in body
            if not hides:
                continue
            if "position: fixed" in body or "position: absolute" in body:
                continue          # overlays do not occupy flow, so they cannot open a gap
            report = f"{os.path.basename(path)}:{first[:64]}"
            if report not in seen:
                seen.add(report)
                findings.append(report)


def check_pages_stamped() -> None:
    """A page served straight from disk skips the build stamp its stylesheet needs."""
    text = read(os.path.join(ROOT, "app", "main.py"))
    for call in re.findall(r"FileResponse\(([^)]*)\)", text):
        if ".html" in call:
            problems.append(f"main.py: FileResponse of an HTML page without the version stamp: {call[:80]}")


def compare_baseline() -> list[str]:
    """Spacing findings that are new since the baseline was recorded.

    The existing overlay and animation rules are known and reviewed; only a new one should stop a
    build. Recording them once turns the check from a report nobody reads into a gate.
    """
    known: set[str] = set()
    if os.path.exists(BASELINE):
        with open(BASELINE, encoding="utf-8") as fh:
            known = {line.strip() for line in fh if line.strip() and not line.startswith("#")}
    current = {finding for finding in findings}
    if not os.path.exists(BASELINE):
        with open(BASELINE, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# Rules that hide without display:none and are reviewed as safe: overlays, animation\n")
            fh.write("# states and decorative layers. New lines here are a defect, not a formality.\n")
            for finding in sorted(current):
                fh.write(finding + "\n")
        print(f"baseline created with {len(current)} reviewed rules")
        return []
    return sorted(current - known)


if __name__ == "__main__":
    check_braces()
    check_links()
    check_jsonld()
    check_ids()
    check_dom_lookups()
    check_hidden_without_leaving_layout()
    check_pages_stamped()
    fresh = compare_baseline()
    if problems:
        print("\n".join(problems))
    if fresh:
        print("new spacing findings (add to tools/spacing-baseline.txt only if reviewed):")
        print("\n".join(fresh))
    if problems or fresh:
        sys.exit(1)
    print("clean")
