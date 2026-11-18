"""Builds Chapter Five (recommendations and conclusions)."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docbuild import Paper  # noqa: E402
from references import REFERENCES  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.join(OUT, "..", "tests", "results.json")
METRICS = os.path.join(OUT, "..", "ml", "artifacts", "metrics.json")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def body(p: Paper, *, page_break=False, include_references=True):
    m = load_json(METRICS, {})
    tests = load_json(TESTS, [])
    name = m.get("model_name", "logistic regression")
    res = (m.get("results") or {}).get(name, {})
    acc = res.get("accuracy", 0)
    f1 = res.get("f1", 0)
    fpr = res.get("false_positive_rate", 0)

    p.h1("CHAPTER FIVE: SYSTEM RECOMMENDATIONS AND CONCLUSIONS", page_break=page_break)

    p.h2("5.1 Introduction")
    p.para(
        "This chapter closes the project. It states the technology chosen to implement the system "
        "and why, summarises the modules that were delivered, presents the test regime and its "
        "outcome, and sets out the conclusions and the recommendations for future work.",
        space_after=2)

    p.h2("5.2 Proposed Technology and Reasons for Selection")
    p.para(
        "The system is implemented with the Python programming language, the scikit-learn library "
        "for model training, the FastAPI framework for the application programming interface, a "
        "SQLite database for storage, and a dependency-free progressive web application for the "
        "client.")
    p.caption("Technology selection and justification")
    p.table(
        ["Layer", "Technology", "Reason for selection"],
        [
            ["Language", "Python 3",
             "One language covers data preparation, model training and the service; the "
             "scientific libraries are mature and free."],
            ["Modelling", "scikit-learn",
             "Provides the three compared classifiers, cross-validation, splitting utilities and "
             "metric functions from one reproducible pipeline."],
            ["API", "FastAPI",
             "Produces a typed JSON interface with automatic documentation, in the same language "
             "as the model, with no separate server process."],
            ["Storage", "SQLite",
             "Serverless, file-based and adequate for a prototype; no hosting cost and no "
             "database administrator."],
            ["Client", "HTML, CSS and JavaScript (PWA)",
             "Requires no build step and no external dependency, so it runs offline and installs "
             "on a phone from the same codebase as the desktop site."],
            ["Deployment", "Docker and a free-tier host",
             "Reproducible environment; the container can be rebuilt from the repository at no "
             "cost."],
        ],
        widths=[2.4, 3.9, 9.1], font_size=8.8, align_center=False,
    )

    p.h2("5.3 Summary of Modules")
    p.para(
        "Module 1, URL intake and validation, accepts an address from a text field, an uploaded "
        "list or a camera QR scan, normalises it and rejects malformed input before any analysis "
        "runs. Module 2, feature extraction, reduces the address to its registrable domain and "
        "computes seventeen numeric features plus character n-gram features, with no network "
        "request. Module 3, classification and explanation, applies the trained model, converts "
        "the output into a risk band and assembles the reasons that raised the score. Module 4, "
        "results, history and accounts, presents the verdict, stores the scan, supports optional "
        "registration and serves the bulk screening and history views.")
    p.para(
        f"The delivered model is a {name} trained on {m.get('n_train', 0):,} addresses and "
        f"evaluated on {m.get('n_test', 0):,} held-out addresses that share no domain with the "
        f"training set. It reaches an accuracy of {acc * 100:.2f}%, an F1 score of {f1:.4f} and a "
        f"false-positive rate of {fpr * 100:.2f}%.")

    p.h2("5.4 Test Regime")
    p.para(
        "Testing combined unit checks on feature extraction, black-box tests of the application "
        "interface and end-to-end checks of the deployed system. Table 2 lists the end-to-end "
        "cases and their outcome; the detailed results, including the confusion matrix and the "
        "threshold analysis, are reported in Chapter Four.")
    rows = []
    if tests:
        for t in tests:
            rows.append([t["id"], t["case"], t["expected"], t["actual"], t["status"]])
    else:
        rows = [[", ", "Test results not generated", ", ", ", ", ", "]]
    p.caption("End-to-end test regime and results")
    p.table(["ID", "Test case", "Expected result", "Actual result", "Status"], rows,
            widths=[1.1, 4.6, 4.2, 4.2, 1.3], font_size=8.4, align_center=False)

    p.h2("5.5 Conclusions")
    p.para(
        "The project set out to design, develop and evaluate Nyavu, a machine-learning web application "
        "that assesses a URL for phishing and explains its verdict. All four specific objectives "
        "were met. The URL characteristics that separate the two classes were identified and "
        "implemented as seventeen domain-level features of the kind used in comparable work "
        "(Sahingoz et al., 2019). A labelled dataset of 26,202 addresses "
        "was assembled from open sources and partitioned by registrable domain so that no domain "
        "appears in both training and test data. Three classifiers were trained and compared, and "
        "the logistic regression was selected because it produces calibrated probabilities and "
        "its F1 was within one percentage point of the best score. The model was deployed behind "
        "an interface that reports a risk band, a score and the specific reasons behind it, and "
        "that installs on a mobile phone as a progressive web application.")
    p.para(
        "Two findings are worth recording beyond the delivery of the artefact. First, split "
        "discipline matters more than the choice of classifier: grouping by registrable domain "
        "removed the near-duplicate leakage that inflated earlier runs. Second, a benign sample "
        "drawn only from bare domains teaches the model that a subdomain implies phishing; "
        "reducing every address to its registrable domain removed a collection artefact that would "
        "otherwise have produced a detector which flagged ordinary websites. Both findings came "
        "from measurement, not from inspection, which is the argument for evaluating an artefact "
        "rather than asserting its quality.")

    p.h2("5.6 Recommendations and Future Work")
    p.para(
        "Several extensions follow directly from the limitations recorded in Chapter One. "
        "Contextual features such as domain age, certificate issuer and hosting network would "
        "raise accuracy on compromised legitimate sites, at the cost of network calls and latency. "
        "A scheduled retraining cycle, with drift monitoring against a fresh feed, would counter "
        "the decay that every phishing model suffers. A browser extension or a mail-gateway hook "
        "would move the check to the point where the user actually meets the link. On the client "
        "side, embedding a quantised model in the application would allow offline classification "
        "with no server at all. Finally, a formal usability study with representative users would "
        "replace the informal feedback used here and would test whether the explanations actually "
        "change behaviour, which is the claim the project is least able to support on its current "
        "evidence.")

    if include_references:
        p.h1("REFERENCES", page_break=True)
        p.references(REFERENCES)


def main():
    p = Paper()
    body(p)
    p.page_numbers()
    path = os.path.join(OUT, "Chapter_Five_Conclusions.docx")
    p.save(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
