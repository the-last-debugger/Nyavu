"""Builds the complete project report: front matter, five chapters, references, appendices."""
from __future__ import annotations

import json
import os
import sys

from docx.shared import Cm, Pt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_ch1  # noqa: E402
import build_ch2  # noqa: E402
import build_ch3  # noqa: E402
import build_ch4  # noqa: E402
import build_ch5  # noqa: E402
from docbuild import Paper  # noqa: E402
from references import REFERENCES  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(OUT, "..", "ml", "artifacts")

TITLE = ("Design and Development of a Machine-Learning-Based "
         "Phishing URL Detection Web and Mobile Application")

TEAM = [
    ("Donald Enron", "CS/M/0626/01/25"),
    ("Justus Kibet", "INTE/M/0317/01/25"),
    ("Ian Mazigulu", "CS/M/0665/01/25"),
    ("Allan Kibet", "CS/M/2790/09/21"),
]


def metrics():
    try:
        with open(os.path.join(ART, "metrics.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def title_page(p: Paper):
    logo = os.path.join(OUT, "assets", "logo.png")
    if os.path.exists(logo):
        p.logo(logo, width_cm=3.2, space_after=14)
    p.para("KABARAK UNIVERSITY", bold=True, align="center", size=16, space_after=2)
    p.para("School of Science, Engineering and Technology", align="center", size=11, space_after=2)
    p.para("Department of Computer Science and Information Technology",
           align="center", size=11, space_after=28)
    p.para(TITLE.upper(), bold=True, align="center", size=14, space_after=24)
    p.para("NYAVU", bold=True, align="center", size=12, space_after=18)
    p.para("A project report submitted in partial fulfilment of the requirements for the "
           "award of the degree of Bachelor of Science in Computer Security of Kabarak University",
           align="center", size=11, space_after=20)
    p.para("by", align="center", size=11, space_after=8)
    for name, reg in TEAM:
        p.para(f"{name}  —  {reg}", align="center", size=11, space_after=2)
    p.para("", space_after=20)
    p.para("Supervisor: ______________________________________", align="center", size=11,
           space_after=18)
    p.para("NOVEMBER 2026", bold=True, align="center", size=12, space_after=0)


def declaration(p: Paper, page_break: bool = True):
    p.h1("DECLARATION", page_break=page_break)
    p.para(
        "We, the undersigned, declare that this project report is our original work and has not "
        "been submitted for the award of a degree in any other university or institution. All "
        "sources of information used have been acknowledged, and where the work of others has been "
        "quoted or paraphrased the source has been cited.")
    p.para("")
    p.table(["Name", "Registration number", "Signature", "Date"],
            [[n, r, "", ""] for n, r in TEAM],
            widths=[4.6, 4.6, 4.0, 2.6], font_size=9.5, align_center=False)


def certification(p: Paper):
    p.h1("CERTIFICATION", page_break=True)
    p.para(
        "This project report has been submitted for examination with our approval as university "
        "supervisor.")
    p.para("")
    p.table(["Role", "Name", "Signature", "Date"],
            [["Supervisor", "", "", ""], ["Co-supervisor", "", "", ""]],
            widths=[3.6, 5.4, 3.8, 3.0], font_size=9.5, align_center=False)
    p.para("")
    p.para("Department of Computer Science and Information Technology", align="left")
    p.para("School of Science, Engineering and Technology", align="left")
    p.para("Kabarak University", align="left")


def copyright_page(p: Paper):
    p.h1("COPYRIGHT", page_break=True)
    p.para(
        "\u00a9 2026, Donald Enron, Justus Kibet, Ian Mazigulu and Allan Kibet. All rights "
        "reserved. No part of this report may be reproduced, stored in a retrieval system or "
        "transmitted in any form or by any means, electronic, mechanical, photocopying or "
        "otherwise, without the prior written permission of the authors or Kabarak University.")


def dedication(p: Paper):
    p.h1("DEDICATION", page_break=True)
    p.para(
        "To our families, whose patience carried the long evenings, and to the teachers who first "
        "showed us that a system is understood by taking it apart.")


def acknowledgement(p: Paper):
    p.h1("ACKNOWLEDGEMENT", page_break=True)
    p.para(
        "We thank our supervisor for direction that kept the project inside its scope, and the "
        "Department of Computer Science and Information Technology for access to the laboratory "
        "and to the resources used to train the model. We thank the colleagues who opened links "
        "we asked them to open and told us honestly whether the result made sense, and the "
        "maintainers of the public phishing feeds and domain rankings without which no dataset "
        "could have been built. Finally we thank each other, for turning up.")


def abstract(p: Paper):
    m = metrics()
    name = m.get("model_name", "logistic regression")
    res = (m.get("results") or {}).get(name, {})
    acc = res.get("accuracy", 0) * 100
    f1 = res.get("f1", 0)
    n = m.get("n_total", 0)

    p.h1("ABSTRACT", page_break=True)
    p.para(
        "Phishing is still the most common way in which credentials and payment details are "
        "stolen, and the link inside a message is the point at which a user has to decide whether "
        "to trust a request. Existing defences are largely reactive: a blocklist can only describe "
        "addresses that have already been reported and verified. This project designed, developed "
        "and evaluated Nyavu, a machine-learning web application that assesses a URL from its "
        "textual structure, without fetching the page and without depending on prior reports.")
    p.para(
        f"A labelled corpus of {n:,} addresses was assembled from the OpenPhish feed, the "
        "Phishing.Database aggregator and the Tranco top-one-million ranking. Phishing entries "
        "hosted on domains inside the top 200,000 of that ranking were removed, because a "
        "name-based classifier cannot distinguish a compromised legitimate domain from the same "
        "domain before compromise. Every address was reduced to its registrable domain, seventeen "
        "numeric features and character n-grams were extracted, and three classifiers were "
        "compared on a split that shares no domain between training and test sets. Logistic "
        f"regression was selected for deployment because it produces calibrated probabilities; it "
        f"reaches {acc:.2f}% accuracy and an F1 of {f1:.3f} on held-out data.")
    p.para(
        "The model is deployed behind an interface that reports a risk band, a score and the "
        "specific characteristics behind each verdict, and that installs on a phone as a "
        "progressive web application. The report concludes that split discipline and freedom from "
        "collection artefacts matter more to a deployed detector than the choice of classifier.")
    p.rich([("Keywords: ", {"bold": True}),
            ("phishing; URL classification; machine learning; explainable detection; progressive "
             "web application; cybersecurity", {})], space_after=2)


def abbreviations(p: Paper):
    p.h1("LIST OF ABBREVIATIONS AND ACRONYMS", page_break=True)
    rows = [
        ["API", "Application Programming Interface"],
        ["APA", "American Psychological Association"],
        ["CSV", "Comma-Separated Values"],
        ["DNS", "Domain Name System"],
        ["eTLD+1", "Registrable domain (public suffix plus one label)"],
        ["FPR", "False-Positive Rate"],
        ["F1", "Harmonic mean of precision and recall"],
        ["HTTP(S)", "Hypertext Transfer Protocol (Secure)"],
        ["IDN", "Internationalised Domain Name"],
        ["JSON", "JavaScript Object Notation"],
        ["ML", "Machine Learning"],
        ["PWA", "Progressive Web Application"],
        ["ROC-AUC", "Area under the Receiver Operating Characteristic curve"],
        ["SQL", "Structured Query Language"],
        ["URL", "Uniform Resource Locator"],
        ["UTC", "Coordinated Universal Time"],
    ]
    p.table(["Abbreviation", "Meaning"], rows, widths=[3.6, 12.2], font_size=9.5,
            align_center=False)


def key_terms(p: Paper):
    p.h1("DEFINITION OF KEY TERMS", page_break=True)
    rows = [
        ["Phishing", "A deception in which a message or website impersonates a trusted party in "
                     "order to obtain credentials, payment details or personal information."],
        ["URL", "Uniform resource locator; the address that identifies a resource on the internet."],
        ["Registrable domain", "The public suffix plus one label, for example example.co.ke; the "
                               "unit a name-based classifier can judge."],
        ["Machine learning", "The construction of models that learn patterns from example data in "
                             "order to predict on new data."],
        ["Classification", "Assignment of an input to one of a predefined set of categories; here, "
                           "phishing or legitimate."],
        ["Feature", "A measurable property of an input used by a model when making a decision."],
        ["False positive", "A legitimate address incorrectly classified as phishing."],
        ["False negative", "A phishing address incorrectly classified as legitimate."],
        ["Progressive web application", "A website that can be installed on a device and used like "
                                        "a native application."],
    ]
    p.table(["Term", "Meaning"], rows, widths=[3.8, 12.0], font_size=9.5, align_center=False)


def appendices(p: Paper, page_break: bool = True):
    p.h1("APPENDICES", page_break=page_break)

    p.h2("Appendix I: Budget")
    p.para(
        "The project was delivered at zero monetary cost. Every component is either open source "
        "or available on a free tier; the only resource consumed was development time.")
    p.table(["Item", "Choice", "Cost"],
            [["Data", "OpenPhish, Phishing.Database, Tranco", "0"],
             ["Language and libraries", "Python, scikit-learn, FastAPI", "0"],
             ["Database", "SQLite", "0"],
             ["Development tools", "Visual Studio Code, Git", "0"],
             ["Hosting (prototype)", "Free-tier container host", "0"],
             ["Model training", "Existing laptop, CPU only", "0"],
             ["Total", "", "KSh 0"]],
            widths=[4.6, 9.0, 2.2], font_size=9.5, align_center=False)

    p.h2("Appendix II: Data Collection Tool")
    p.para(
        "Requirements were gathered with the structured checklist below, derived from the project "
        "objectives and reviewed with the supervisor.")
    p.table(["#", "Question", "Purpose"],
            [["1", "Where does the user first meet the link (SMS, email, social)?",
              "Locate the point of intervention."],
             ["2", "What does the user currently do before opening an unknown link?",
              "Establish the baseline behaviour."],
             ["3", "What would make a warning believable?",
              "Define the explanation requirement."],
             ["4", "Would the tool be used on a phone, a laptop, or both?",
              "Set the client requirement."],
             ["5", "What would make the user stop trusting the tool?",
              "Set the false-positive requirement."]],
            widths=[0.9, 8.4, 6.5], font_size=9.2, align_center=False)

    p.h2("Appendix III: Sample Test Data")
    p.para(
        "The first rows of the held-out predictions file, which records the true label, the "
        "predicted label and the model probability for every test address.")
    rows = []
    path = os.path.join(ART, "holdout_predictions.csv")
    try:
        with open(path, encoding="utf-8") as fh:
            next(fh)
            for i, line in enumerate(fh):
                if i >= 12:
                    break
                parts = line.strip().split(",")
                if len(parts) >= 5:
                    rows.append([parts[0][:46], parts[1], parts[2], parts[3][:6]])
    except Exception:
        rows = [["unavailable", "", "", ""]]
    p.table(["URL", "True", "Pred", "P(phish)"], rows,
            widths=[8.2, 1.6, 1.6, 2.2], font_size=8.0, align_center=False)

    p.h2("Appendix IV: Source Code")
    p.para(
        "The implementation is organised as follows, and is submitted with this report as an "
        "archive. Line counts are approximate.")
    p.table(["Path", "Purpose", "Lines"],
            [["ml/acquire_data.py", "Downloads the feeds and builds the labelled corpus", "~190"],
             ["ml/curate_data.py", "Removes compromised-domain rows and rebalances", "~110"],
             ["ml/features.py", "Registrable-domain reduction and 17 features", "~230"],
             ["ml/train.py", "Trains, compares and persists the three classifiers", "~250"],
             ["app/main.py", "FastAPI routes for scan, bulk, history and auth", "~210"],
             ["app/predictor.py", "Model load, inference, attribution, reputation prior", "~140"],
             ["app/db.py", "SQLite schema and queries", "~180"],
             ["app/static/", "Single-page client, stylesheet, service worker", "~700"],
             ["tests/run_tests.py", "Scripted end-to-end test run", "~160"],
             ["docs/", "Report builders, diagrams and figures", "~1600"]],
            widths=[4.6, 9.6, 2.0], font_size=8.6, align_center=False)

    p.h2("Appendix V: Project Schedule")
    p.table(["Week", "Activity", "Deliverable"],
            [["1", "Concept, problem definition, objectives", "Concept paper"],
             ["2–6", "Requirements, wireframes, dataset search", "Wireframe sketch"],
             ["7", "Data acquisition and curation", "Labelled corpus"],
             ["8", "Feature engineering and baseline model", "Metrics table"],
             ["9", "Model comparison and selection", "Selected model"],
             ["10", "Interface implementation", "Working detector"],
             ["11", "Testing and deployment", "Deployed system"],
             ["12", "Report writing and presentation", "Final report"]],
            widths=[1.4, 9.0, 5.4], font_size=9.2, align_center=False)



def merged_tail(p: Paper):
    """Chapter Five's substance, carried inside Chapter Four for the four-chapter form.

    The marking scheme awards marks for a summary of modules, a test regime, the choice
    of technology and conclusions with recommendations. All four survive here, so the
    four-chapter structure does not cost those marks.
    """
    p.h2("4.14 Summary of Modules and Recommendations")
    p.para(
        "Four modules make up the delivered system, and each can be pointed to in the "
        "repository. URL intake and validation accepts an address from a field, an uploaded list or "
        "a camera scan, normalises it and rejects malformed input before any analysis runs. Feature "
        "extraction reduces the address to its registrable domain and computes the seventeen numeric "
        "features together with the character n-grams, making no network request. Classification and "
        "explanation applies the trained model, converts the output into a risk band and assembles "
        "the reasons that raised the score. Results, history and accounts presents the verdict, "
        "stores the scan, and serves the bulk screening and history views.")
    p.para(
        "The technology behind those modules was chosen for the constraints of the project rather "
        "than for novelty. Python covers data preparation, training and service in one language; "
        "scikit-learn provides reproducible pipelines, grouped splitting and the metric functions "
        "used in this chapter; FastAPI exposes a typed JSON interface in that same language; SQLite "
        "stores the results without an administrator or a hosting fee; and the client is plain HTML, "
        "CSS and JavaScript with no build step, so nothing can fail to compile in front of an "
        "examiner. The training and evaluation described in this chapter are reproducible from a "
        "clean checkout with a fixed seed.")
    p.para(
        "Three recommendations follow from the evaluation. Contextual signals - domain age, "
        "certificate issuer, hosting network - would raise accuracy on compromised legitimate sites, "
        "at the cost of network calls and latency. Retraining should be scheduled rather than "
        "occasional, with the frozen baseline kept for comparison, because every phishing model "
        "decays as tactics change. And the check belongs at the point of contact: a browser client "
        "that scores a link as it is clicked would reach the user earlier than a page they must "
        "remember to visit. None of these requires a change to the classifier; all three extend the "
        "same service.")



def _leader(p, text: str, page: str, indent_cm: float = 0.0, size: int = 11):
    from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
    from docx.shared import Cm as _Cm, Pt as _Pt
    para = p.doc.add_paragraph()
    pf = para.paragraph_format
    pf.left_indent = _Cm(indent_cm)
    pf.space_after = _Pt(2)
    pf.line_spacing = 1.0
    pf.tab_stops.add_tab_stop(_Cm(15.6), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    run = para.add_run(f"{text}\t{page}")
    run.font.size = _Pt(size)
    return para


def static_toc(p: Paper, entries):
    for e in entries:
        indent = {1: 0.0, 2: 0.7, 3: 1.4}.get(e["level"], 1.4)
        bold = e["level"] == 1
        para = _leader(p, e["text"], e["page"], indent)
        for r in para.runs:
            r.bold = bold


def static_list(p: Paper, title: str, items, prefix: str):
    p.h1(title, page_break=True)
    for i, item in enumerate(items, 1):
        _leader(p, item["text"], item["page"], 0.0, size=10)


def main():
    p = Paper(TITLE)
    title_page(p)                       # section 1: bare title page

    front = p.new_section(fmt="lowerRoman", start=2)   # title counts as i, unnumbered
    p.header_text(front, "KABARAK UNIVERSITY")

    declaration(p, page_break=False)
    certification(p)
    copyright_page(p)
    dedication(p)
    acknowledgement(p)
    abstract(p)

    p.h1("TABLE OF CONTENTS", page_break=True)
    contents_path = os.environ.get("NYAVU_TOC", "")
    if contents_path and os.path.exists(contents_path):
        data = json.load(open(contents_path, encoding="utf-8"))
        static_toc(p, data.get("entries", []))
        static_list(p, "LIST OF TABLES", data.get("lot", []), "Table")
        static_list(p, "LIST OF FIGURES", data.get("lof", []), "Figure")
    else:
        p.add_toc("1-3")
        p.list_of("Table")
        p.list_of("Figure")
    abbreviations(p)
    key_terms(p)

    # body starts a new section: arabic numbering from 1, running head per chapter
    mode = os.environ.get("NYAVU_MODE", "five")
    chapters = [
        (build_ch1.body, "CHAPTER ONE: INTRODUCTION"),
        (build_ch2.body, "CHAPTER TWO: LITERATURE REVIEW"),
        (build_ch3.body, "CHAPTER THREE: METHODOLOGY AND SYSTEM DESIGN"),
        (build_ch4.body, "CHAPTER FOUR: SYSTEM IMPLEMENTATION AND DEPLOYMENT"),
    ]
    if mode == "five":
        chapters.append((build_ch5.body,
                         "CHAPTER FIVE: SYSTEM RECOMMENDATIONS AND CONCLUSIONS"))
    for index, (body, heading) in enumerate(chapters):
        sec = p.new_section(fmt="decimal", start=1 if index == 0 else None)
        p.header_text(sec, heading)
        body(p, page_break=False, include_references=False)

    if mode == "four_merged":
        merged_tail(p)

    ref_sec = p.new_section(fmt="decimal", start=None)
    p.header_text(ref_sec, "REFERENCES")
    p.h1("REFERENCES", page_break=False)
    p.references(REFERENCES)

    app_sec = p.new_section(fmt="decimal", start=None)
    p.header_text(app_sec, "APPENDICES")
    appendices(p, page_break=False)

    p.update_fields_on_open()
    suffix = os.environ.get("NYAVU_SUFFIX", "")
    path = os.path.join(OUT, f"Team_Project_Full_Report{suffix}.docx")
    p.save(path)

    words = sum(len(par.text.split()) for par in p.doc.paragraphs)
    print(f"wrote {path}")
    print(f"paragraphs={len(p.doc.paragraphs)} tables={len(p.doc.tables)} words~{words:,}")


if __name__ == "__main__":
    main()
