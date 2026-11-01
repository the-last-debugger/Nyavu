"""Builds the Chapter Three submission (methodology and system design)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docbuild import Paper  # noqa: E402
from references import REFERENCES  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(OUT, "figures")
SHOTS = os.path.join(OUT, "screenshots")


def body(p: Paper, *, page_break=True, include_references=True):
    p.h1("CHAPTER THREE: METHODOLOGY AND SYSTEM DESIGN", page_break=page_break)

    p.h2("3.1 Introduction")
    p.para(
        "This chapter explains how the system was researched, specified and designed. It states "
        "the research approach and the software development model, describes how requirements "
        "were gathered and what they are, records the feasibility assessment, and then presents "
        "the system design through a context diagram, a level 1 data flow diagram, a use case "
        "diagram, an entity relationship diagram and interface prototypes. Chapter Four reports "
        "the implementation and testing of the design presented here.", space_after=2)

    p.h2("3.2 Research Methodology")
    p.para(
        "The project follows design science research: a problem is identified, an artefact is "
        "built to address it, and the artefact is evaluated against explicit criteria (Hevner et "
        "al., 2004). The artefact is the Nyavu system. Evaluation is quantitative and "
        "experimental. Classification performance is measured on labelled data using accuracy, "
        "precision, recall, F1, ROC-AUC and the false-positive rate, with a fixed random seed and "
        "a domain-disjoint split so the result can be reproduced. Usability is assessed against "
        "task completion: a user should be able to obtain and understand a verdict in a single "
        "step, on a desktop or on a phone.")

    p.h3("3.2.1 Development Methodology")
    p.para(
        "Development followed an agile, iterative model in one-week increments (Sommerville, "
        "2016). Each increment produced something that could be run and demonstrated: first the "
        "dataset and feature extractor, then the classifier and its evaluation, then the "
        "application interface, then the explanation layer and the mobile client.")
    p.para(
        "The model suits this project because the requirements were not fully known at the start "
        "and because the work is inseparable from experimentation: the feature set and the choice "
        "of classifier could only be settled by measuring them. Iteration also allowed the "
        "evaluation to change the design. An early run showed that a benign sample drawn entirely "
        "from bare domains let the model learn that the presence of a subdomain implies phishing; "
        "the next increment reduced every URL to its registrable domain and retrained, which "
        "removed the artefact.")
    p.para(
        "The model has weaknesses. Documentation can lag behind the code, scope can creep because "
        "the next increment is always easy to justify, and progress depends on the availability of "
        "the team. These were mitigated by fixing the backlog for each increment in advance, "
        "demonstrating the increment before starting the next, and treating documentation and "
        "tests as part of the definition of done rather than as separate tasks.")

    p.h2("3.3 Data Collection Methods")
    p.para(
        "Requirements were gathered from three sources. Document analysis of existing detection "
        "tools, their published documentation and published evaluations established what the "
        "current systems do and where they fail. Analysis of public phishing samples established "
        "the structure of the addresses that must be recognised. A structured requirements "
        "checklist, derived from the project objectives, was reviewed with the project team and "
        "the supervisor and refined into the functional and non-functional requirements below.")
    p.para(
        "The training and evaluation data are entirely secondary and openly available. Phishing "
        "addresses were collected from the OpenPhish public feed and the Phishing.Database "
        "aggregator; legitimate domains were sampled from the Tranco top-one-million list (Pochat "
        "et al., 2019). Legitimate entries were restricted to the top 200,000 positions so that "
        "the negatives reflect established sites rather than the long tail of the ranking. No "
        "personal data and no user browsing data were collected at any stage.")

    p.h2("3.4 System Analysis")
    p.h3("3.4.1 Functional Requirements")
    p.caption("Functional requirements")
    p.table(
        ["ID", "Requirement", "Priority"],
        [
            ["FR1", "Accept a URL from the user and return a classification.", "Must"],
            ["FR2", "Display a risk score, a risk band and the model confidence.", "Must"],
            ["FR3", "Explain each verdict with the characteristics that influenced it.", "Must"],
            ["FR4", "Validate and normalise input, rejecting malformed addresses.", "Must"],
            ["FR5", "Screen a list of URLs uploaded as a CSV or text file.", "Should"],
            ["FR6", "Scan a QR code using the device camera.", "Should"],
            ["FR7", "Retain a history of past checks for the current user.", "Should"],
            ["FR8", "Support optional registration and sign-in.", "Should"],
            ["FR9", "Publish the model comparison and evaluation metrics.", "Could"],
            ["FR10", "Export screening results for a third-party tool.", "Could"],
        ],
        widths=[1.3, 12.0, 2.1], font_size=9,
    )

    p.h3("3.4.2 Non-Functional Requirements")
    p.caption("Non-functional requirements")
    p.table(
        ["ID", "Requirement", "Measure"],
        [
            ["NFR1", "A verdict is returned quickly.", "Under 500 ms per URL on a laptop CPU."],
            ["NFR2", "Inference needs no network access.", "No outbound call in the request path."],
            ["NFR3", "The interface works on a phone.", "Responsive layout; installable."],
            ["NFR4", "The system costs nothing to run.", "Open data, open-source stack, free tier."],
            ["NFR5", "Results are reproducible.", "Fixed seed; scripts committed with the report."],
            ["NFR6", "Credentials are not stored in plain text.", "PBKDF2-SHA256, 200,000 iterations."],
        ],
        widths=[1.4, 7.0, 7.0], font_size=9, align_center=False,
    )

    p.h3("3.4.3 Feasibility Study")
    p.para(
        "Technical feasibility. Every component is free and mature: Python with scikit-learn for "
        "the model, FastAPI for the application interface, SQLite for storage and a plain browser "
        "for the client. Inference needs no graphics processor, and the trained model is a few "
        "megabytes, so it runs on an ordinary laptop.")
    p.para(
        "Economic feasibility. The project has no monetary cost. Data are free, the toolchain is "
        "open source, and the application is deployed on a free tier. The only resource consumed "
        "is development time.")
    p.para(
        "Operational feasibility. The system runs in a browser and needs no installation; on a "
        "phone it can be added to the home screen as a progressive web application. No change to "
        "an organisation's network or workflow is required to use it.")

    p.h2("3.5 System Design")
    p.h3("3.5.1 Architectural Design")
    p.para(
        "The system is a three-tier application. The presentation tier is a progressive web "
        "application served as static files, with no build step and no external dependencies. The "
        "application tier is a FastAPI service that validates input, extracts features, applies "
        "the model and assembles the explanation. The data tier is a SQLite database holding "
        "users, sessions, scans and model versions. The model artefact is loaded once at start-up "
        "and is never written during a request, which keeps the request path read-only.")
    p.para(
        "Separating the model behind an application interface is what makes the mobile client "
        "affordable: the same endpoint serves the desktop site, the installed web application and "
        "any future native client, so the detection logic exists once.")

    p.h3("3.5.2 Context Diagram")
    p.para(
        "The context diagram below places the system in its environment. The internet user submits addresses and "
        "receives verdicts. Public URL sources supply labelled data for offline training. The "
        "administrator receives the scan log and the model metrics. No other external system is "
        "consulted at request time.")
    p.figure(os.path.join(FIG, "fig_context.png"),
             "Context diagram of the Nyavu system", width_cm=15.0)

    p.h3("3.5.3 Level 1 Data Flow Diagram")
    p.para(
        "The level 1 data flow diagram below decomposes the system into four processes. Process 1.0 validates the submitted "
        "address. Process 2.0 extracts the domain-level feature vector. Process 3.0 applies the "
        "model and assembles the explanation. Process 4.0 records the scan and serves the history. "
        "Three data stores are used: scans, sessions and the trained model.")
    p.figure(os.path.join(FIG, "fig_dfd_level1.png"),
             "Level 1 data flow diagram", width_cm=15.5)

    p.h3("3.5.4 Use Case Diagram")
    p.para(
        "The use case diagram below shows the actors and their use cases. A visitor can analyse a URL or scan a QR "
        "code, and both actions include viewing the verdict and its reasons. A registered user can "
        "additionally screen a list, review history, export results and manage an account. The "
        "administrator inspects model metrics and user accounts.")
    p.figure(os.path.join(FIG, "fig_usecase.png"),
             "Use case diagram", width_cm=14.5)

    p.h3("3.5.5 Database Design")
    p.para(
        "The entity relationship diagram below shows the data model. A user holds zero or more sessions and "
        "records zero or more scans; a scan belongs to at most one user, and the foreign key is "
        "nullable so that anonymous scans are retained. Each scan stores the registrable domain "
        "next to the full address so scans can be grouped by domain without parsing the URL again. "
        "The models table is append-only and records which version produced the active results.")
    p.figure(os.path.join(FIG, "fig_erd.png"),
             "Entity relationship diagram", width_cm=14.5)

    p.h3("3.5.6 Interface Design")
    p.para(
        "The low-fidelity wireframe below fixed the layout before any styling: a single "
        "input row with a primary action and a secondary camera action, a row of sample addresses "
        "for demonstration, and a result panel containing a risk indicator, a verdict band and a "
        "list of reasons. The high-fidelity result is described in Chapter Four.")
    p.figure(os.path.join(FIG, "fig_wireframe.png"),
             "Low-fidelity wireframe of the detector screen", width_cm=14.0)

    hi = os.path.join(SHOTS, "shot_result_desktop.png")
    if os.path.exists(hi):
        p.figure(hi, "High-fidelity interface: a flagged URL with its explanation",
                 width_cm=15.0)

    p.h2("3.6 Research Ethics")
    p.para(
        "The project involves no human participants beyond informal usability feedback, and "
        "collects no personal data. Addresses submitted for analysis are stored only to provide "
        "the user with a history; no browsing activity is monitored and no address is shared with "
        "a third party, because the system makes no outbound request when analysing a URL. "
        "Account passwords are stored as salted PBKDF2-SHA256 hashes. The phishing data used for "
        "training come from published feeds and contain addresses, not personal information. "
        "Because a verdict is probabilistic, the interface states explicitly that a result is an "
        "assessment and not a guarantee, so that a user does not treat the tool as a substitute "
        "for judgement.")

    p.h2("3.7 Summary")
    p.para(
        "This chapter set out the research approach, the iterative development model and the "
        "requirements, and presented the design at the context, process, use case, data and "
        "interface levels. Chapter Four describes how that design was implemented, tested and "
        "deployed.")

    if include_references:
        p.h1("REFERENCES", page_break=True)
        p.references(REFERENCES)


def main():
    p = Paper()
    body(p)
    p.page_numbers()
    path = os.path.join(OUT, "Chapter_Three_Methodology.docx")
    p.save(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
