"""Builds the Chapter One submission (due 1 November 2026).

Layout target: three pages of chapter body (guideline maximum), with the cover page
and the reference list outside that count.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docbuild import Paper  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
TITLE = ("Design and Development of a Machine-Learning-Based "
         "Phishing URL Detection Web and Mobile Application")

TEAM = [
    ("Donald Enron", "CS/M/0626/01/25", "Team Leader"),
    ("Justus Kibet", "INTE/M/0317/01/25", "Team Member"),
    ("Ian Mazigulu", "CS/M/0665/01/25", "Team Member"),
    ("Allan Kibet", "CS/M/2790/09/21", "Team Member"),
]

REFERENCES = [
    "Alkhalil, Z., Hewage, C., Nawaf, L., & Khan, I. (2021). Phishing attacks: A recent "
    "comprehensive study and a new anatomy. Frontiers in Computer Science, 3, 563060. "
    "https://doi.org/10.3389/fcomp.2021.563060",

    "Anti-Phishing Working Group. (2025). Phishing activity trends report, fourth quarter "
    "2025. APWG. https://docs.apwg.org/reports/apwg_trends_report_q4_2025.pdf",

    "Interisle Consulting Group. (2025). Phishing landscape 2025: An annual study of the "
    "scope and distribution of phishing. Interisle. https://interisle.net",

    "Moore, T., & Clayton, R. (2007). Examining the impact of website take-down on phishing. "
    "Proceedings of the Anti-Phishing Working Group eCrime Researchers Summit, 1-13. "
    "https://doi.org/10.1145/1299015.1299013",

    "Sahingoz, O. K., Buber, E., Demir, O., & Diri, B. (2019). Machine learning based "
    "phishing detection from URLs. Expert Systems with Applications, 117, 345-357. "
    "https://doi.org/10.1016/j.eswa.2018.09.029",

    "Sheng, S., Wardman, B., Warner, G., Cranor, L. F., Hong, J., & Zhang, C. (2009). An "
    "empirical analysis of phishing blacklists. Proceedings of the Sixth Conference on Email "
    "and Anti-Spam (CEAS 2009).",
]


def cover(p: Paper):
    logo = os.path.join(OUT, "assets", "logo.png")
    if os.path.exists(logo):
        p.logo(logo, width_cm=3.0, space_after=12)
    p.para("KABARAK UNIVERSITY", bold=True, align="center", size=16, space_after=2)
    p.para("School of Science, Engineering and Technology", align="center", size=11, space_after=2)
    p.para("Department of Computer Science and Information Technology",
           align="center", size=11, space_after=34)
    p.para(TITLE.upper(), bold=True, align="center", size=14, space_after=34)
    p.para("A project proposal submitted in partial fulfilment of the requirements for the "
           "award of the degree of Bachelor of Science in Computer Security of Kabarak University",
           align="center", size=11, space_after=26)
    p.para("PROJECT TEAM", bold=True, align="center", size=11, space_after=8)
    for name, reg, role in TEAM:
        p.para(f"{name}, {reg}  ({role})", align="center", size=11, space_after=2)
    p.para("", space_after=34)
    p.para("NOVEMBER 2026", bold=True, align="center", size=12, space_after=0)


def terms_table(p: Paper, terms):
    from docx.shared import Cm, Pt
    t = p.doc.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    t.autofit = False
    widths = (Cm(4.6), Cm(11.6))
    for term, meaning in terms:
        cells = t.add_row().cells
        for cell, text, bold, w in ((cells[0], term, True, widths[0]),
                                    (cells[1], meaning, False, widths[1])):
            cell.width = w
            cell.text = ""
            para = cell.paragraphs[0]
            para.paragraph_format.line_spacing = 1.0
            para.paragraph_format.space_after = Pt(1)
            para.paragraph_format.space_before = Pt(1)
            run = para.add_run(text)
            run.bold = bold
            run.font.size = Pt(9.5)
            run.font.name = "Times New Roman"
    for col, w in zip(t.columns, widths):
        col.width = w


def body(p: Paper, *, page_break=True, include_references=True):
    p.h1("CHAPTER ONE: INTRODUCTION", page_break=page_break)

    p.h2("1.1 Introduction")
    p.para(
        "This chapter introduces the project, states the problem that current detection "
        "approaches leave unresolved, and presents the objectives, research questions, "
        "significance, scope and modules that guide the work.", space_after=2)

    p.h2("1.2 Background of the Study")
    p.para(
        "Internet access in Kenya has become the ordinary medium for banking, mobile money, "
        "education and government services. Each depends on a user following a link, so the link "
        "rather than the organisation has become the point at which trust is decided.",
        space_after=2)
    p.para(
        "Phishing exploits that decision. An attacker sends a message that appears to come from a "
        "trusted organisation and directs the recipient to a page imitating the genuine service in "
        "order to collect passwords, card details or one-time codes (Alkhalil et al., 2021). Such "
        "addresses are built to survive a glance: a brand name inside a subdomain, characters "
        "swapped for visually similar ones, a hyphenated compound domain, or a cheap top-level "
        "domain registered for the purpose. Interisle Consulting Group (2025) reports a 38% "
        "year-on-year rise in phishing volume, and the Anti-Phishing Working Group (2025) "
        "reports sustained high volume.", space_after=2)
    p.para(
        "In Kenya the target is frequently mobile money and retail banking, where one deception "
        "moves funds immediately. Machine learning offers an alternative to lists of known bad "
        "addresses: learning the structural patterns that separate fraudulent from legitimate "
        "addresses lets a classifier assess one it has never seen. This project builds such a "
        "classifier and delivers it as Nyavu, Swahili for a fishing net, in a web and mobile application "
        "that explains each verdict.",
        space_after=2)

    p.h2("1.3 Problem Statement")
    p.para(
        "Users receive suspicious links continuously and must judge them in seconds. Most cannot "
        "parse a host name, and a well-built phishing address differs from the genuine one by a "
        "few characters, so the decision rests on appearance rather than evidence.", space_after=2)
    p.para(
        "The tools that support that decision are largely reactive. Blocklists and safe-browsing "
        "services collect addresses that have been reported, verify them and publish them for "
        "browsers to check; they are accurate on what they contain, but they cannot describe an "
        "address that nobody has reported yet, so a new page stays live until it has been "
        "reported, verified and distributed (Sheng et al., 2009). Manual inspection, which remains "
        "the fallback for most users, requires expertise that a convincing imitation defeats and "
        "takes longer than the few seconds in which the decision is usually made. Rule-based "
        "filters score hand-written features such as address length, keywords and character "
        "counts; they are brittle, easily avoided, and the thresholds that catch more attacks also "
        "flag legitimate sites. Commercial detection services return a verdict for a subscription, "
        "but the logic is closed and the user's browsing data leaves the device.", space_after=2)
    p.para(
        "Because the dominant defences depend on prior reporting, a fresh phishing address is both "
        "live and unrecognised until it is reported and verified (Moore & Clayton, 2007). And "
        "where a tool does return a verdict it rarely explains it, so a user told only that a link "
        "is unsafe learns nothing that transfers to the next message.",
        space_after=2, space_before=4)

    p.h3("1.3.1 Proposed Solution")
    p.para(
        "The project proposes a machine-learning web and mobile application that assesses a URL "
        "from its textual structure when it is submitted, without prior reports and without "
        "fetching the page. Four decisions answer the weaknesses described above. Generalising "
        "from patterns rather than looking up a list lets it assess addresses that have never been "
        "reported. Computing the features from the address alone gives a verdict in milliseconds "
        "without exposing the user to the destination. Reporting the characteristics that raised "
        "the score makes the verdict auditable. Inference on commodity hardware with open data "
        "keeps it affordable.")

    p.h2("1.4 Objectives")
    p.h3("1.4.1 General Objective")
    p.para(
        "To develop a machine-learning-based web and mobile application that assesses submitted "
        "URLs for phishing and communicates the basis of that assessment.", space_after=2)
    p.h3("1.4.2 Specific Objectives")
    p.nlist([
        "To design a lexical and structural feature set, together with a dataset preparation "
        "procedure, that captures the characteristics distinguishing phishing addresses from "
        "legitimate ones.",
        "To implement and compare machine-learning classifiers trained on that dataset and select "
        "the best-performing model for deployment.",
        "To evaluate the accuracy of the selected classifier and the clarity of the explanations "
        "it presents to non-expert users.",
    ], style="roman")

    p.h2("1.5 Research Questions")
    p.nlist([
        "Which lexical and structural URL characteristics distinguish phishing addresses from "
        "legitimate ones?",
        "Which classification model, trained on the prepared dataset, achieves the best balance "
        "between detection performance and false-positive rate?",
        "How accurately does the selected classifier classify URLs, and how clearly does it "
        "explain its verdicts to non-expert users?",
    ], style="roman-lower")

    p.h2("1.6 Significance and Justification")
    p.para(
        "Ordinary users gain a second opinion on a link, with an explanation they can learn from. "
        "Students and researchers gain a reproducible example of applying supervised learning to a "
        "security problem with open data. The work is timely because phishing is increasing while "
        "the cost of hosting a small classifier has fallen.")

    p.h2("1.7 Scope and Limitations of the Study")
    p.para(
        "The study covers the analysis of HTTP and HTTPS addresses, the construction of a labelled "
        "dataset from public phishing feeds and domain rankings, the training and comparison of "
        "classifiers, and their delivery through a browser application that is also installable on "
        "a mobile device.",
        space_after=2)
    p.para(
        "The study does not inspect page content, download files, monitor browsing traffic or "
        "guarantee that a site is safe, and it does not implement browser or operating-system "
        "integration. "
        "Performance depends on the representativeness of the dataset, and a model trained on "
        "historical addresses loses accuracy as tactics change. Because the decision is two-class, "
        "some legitimate addresses will be flagged and some fraudulent ones will pass, so a verdict "
        "is an assessment rather than a certainty.")

    p.h2("1.8 Proposed Modules")
    p.para(
        "Nyavu has four modules. URL intake and validation accepts an address, a pasted list "
        "or a scanned QR code and rejects malformed input. Feature extraction reduces the address "
        "to interpretable numeric features and character n-grams of the host name, without any "
        "network request. Classification and explanation turns the model output into a probability "
        "and the reasons behind it. Results, history and accounts presents the verdict and reasons, "
        "keeps a history of checks and supports optional accounts and bulk screening. The interface "
        "is a progressive web application built with Python, scikit-learn, FastAPI and SQLite, so "
        "one codebase serves desktop and mobile.")

    if include_references:
        p.h1("REFERENCES", page_break=True)
        p.references(REFERENCES)


def front_pages(p: Paper):
    p.h1("DECLARATION", page_break=True)
    p.para(
        "We, the undersigned, declare that this project report is our original work and has not "
        "been submitted for the award of a degree in any other university or institution. All "
        "sources of information used have been acknowledged, and where the work of others has "
        "been quoted or paraphrased the source has been cited.")
    p.para("")
    p.table(["Name", "Registration number", "Signature", "Date"],
            [[t[0], t[1], "", ""] for t in TEAM],
            widths=[4.6, 4.6, 4.0, 2.6], font_size=9.5, align_center=False)

    p.h1("CERTIFICATION", page_break=True)
    p.para("This project report has been submitted for examination with our approval as "
           "university supervisor.")
    p.para("")
    p.table(["Role", "Name", "Signature", "Date"],
            [["Supervisor", "", "", ""], ["Co-supervisor", "", "", ""]],
            widths=[3.6, 5.4, 3.8, 3.0], font_size=9.5, align_center=False)
    p.para("")
    p.para("Department of Computer Science and Information Technology", align="left")
    p.para("School of Science, Engineering and Technology", align="left")
    p.para("Kabarak University", align="left")


def main():
    p = Paper(TITLE)
    cover(p)
    front_pages(p)
    body(p)
    p.page_numbers()
    p.update_fields_on_open()
    path = os.path.join(OUT, "Chapter_One_Submission.docx")
    p.save(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
