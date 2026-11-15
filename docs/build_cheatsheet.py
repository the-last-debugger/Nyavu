"""Builds the review cheat sheet in plain language, with a glossary."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docx.shared import Pt  # noqa: E402
from docbuild import Paper  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))

CRITICAL = [
    ("What does your system do?",
     "You give it a link, and it tells you whether the link looks like phishing, gives a score "
     "out of 100, and lists the reasons. It never opens the website, so it is safe to use before "
     "you click."),
    ("Why machine learning instead of a blocklist?",
     "A blocklist is a list of bad links that people have already found. A brand-new phishing "
     "link is on no list yet. Our model looks at the shape of the address itself, so it can judge "
     "a link nobody has reported."),
    ("You got 75%, the papers say 97%. Why the gap?",
     "Most papers get 97% by accident. Their safe websites were written as bare domains and their "
     "phishing links as full long addresses, so the model learned 'long and messy means bad' "
     "instead of learning phishing. We removed that shortcut, and 75.4% is what was honestly "
     "left."),
    ("What were your objectives?",
     "One, decide what to measure in a link and prepare the data. Two, build and compare models "
     "and choose the best. Three, check how accurate it is and how clear the explanation is. "
     "Three objectives, three matching research questions."),
    ("How do you know it works?",
     "We tested on 3,573 links the model had never seen, from websites it was never trained on. It "
     "got 75.4% right. Ten out of ten end-to-end tests also pass."),
    ("What is your false-positive rate, and is that acceptable?",
     "About 20 out of every 100 safe websites were wrongly flagged. That is too many, so we added "
     "a rule: the 100,000 most popular websites are never flagged on the name alone. The cost is "
     "that a scam hosted on a popular site is missed, and we say so in the report."),
    ("What is new here? Why should this score well?",
     "Three things. We found the mistake that makes published scores look better than they are, "
     "and reported the honest number. Our app explains every answer instead of just saying 'bad'. "
     "And it runs at zero cost on free data."),
    ("Can you show us?",
     "Yes. Paste a link, show the score, show the reasons, then show the 'did you mean' line. "
     "Have the demo open before the question is asked."),
]

IMPORTANT = [
    ("Why this model and not a bigger one?",
     "It gives a real percentage, and it can show which part of the address pushed the score up. "
     "The stronger model scored 0.2% better but could not explain itself, so it was not usable."),
    ("Why seventeen things to measure?",
     "All seventeen can be read from the address alone - length, digits, hyphens, the ending, "
     "whether a brand name appears. No internet lookup, so an answer takes milliseconds."),
    ("Why do you look only at the registered domain?",
     "Because a person registers a name like example.co.ke, and everything before it is free to "
     "invent. Our safe list held bare domain names while our phishing list held full addresses, "
     "so comparing the whole address would have been unfair."),
    ("How did you split the data?",
     "By website, not by link. If the same website appeared in both training and testing, the "
     "score would be fake - the model would be recognising something it had already seen."),
    ("What did you throw away?",
     "About a third of the phishing links sat on real, popular websites that had been hacked. From "
     "the address alone those look exactly like the honest site, so no name-based system can catch "
     "them. We removed them and explained why."),
    ("Why did you work in weekly steps?",
     "Because the answers changed the plan. We rebuilt the features twice, and re-trained when the "
     "results said our data was misleading us. A single big build would have hidden that."),
    ("How did you handle ethics?",
     "No personal data, no opening of websites, no watching of browsing. We also refused "
     "permission to read notifications, because reading every message on a phone is far more "
     "access than the benefit deserves."),
]

USEFUL = [
    ("Why these tools?",
     "One language, Python, for the data, the model and the service. A free database with no "
     "administrator. And a website with no build step, so nothing can fail while we demonstrate."),
    ("Does it scale?",
     "One scan is about 250 bytes, so a million scans is roughly 250 MB. The plan is to keep 90 "
     "days of full records and daily totals beyond that."),
    ("What is the biggest weakness?",
     "It judges names, not pages. Hacked real websites defeat it, and it will get weaker as "
     "attackers change tactics."),
    ("What would you do next?",
     "Add what the page contains, retrain on a schedule, and move the check into the browser so it "
     "warns at the moment of the click."),
    ("Why is Chapter Three longer than the guidelines allow?",
     "It holds five full-page diagrams - context, data flow, use case, database and the wireframe. "
     "The marking scheme asks for them, and shrinking them would cost more marks than the page "
     "limit saves."),
]

GLOSSARY = [
    ("Phishing", "A fake message or website that pretends to be a real company, to steal a "
                 "password or money."),
    ("URL", "The address of a page on the internet, for example https://example.co.ke/login."),
    ("Registrable domain", "The part somebody actually buys and owns, such as example.co.ke. "
                           "Everything before it can be invented for free."),
    ("Feature", "One measurable thing about a link - its length, its number of digits, its "
                "ending. We use seventeen."),
    ("Model", "The part of the program that has learned from examples and gives the score."),
    ("Classifier", "A model that puts things into groups - here, phishing or safe."),
    ("Training data", "The examples the model learns from."),
    ("Test data", "Examples kept back and hidden from the model, used only to check it."),
    ("Leakage", "When the test data is too similar to the training data, so the score looks "
                "better than reality. Our biggest lesson."),
    ("False positive", "A safe website flagged as phishing. Annoying and damaging to trust."),
    ("False negative", "A phishing link allowed through. Dangerous."),
    ("Precision", "Of the links we flagged, how many really were phishing."),
    ("Recall", "Of all the real phishing links, how many we caught."),
    ("F1 score", "One number balancing precision and recall. Being good at one and bad at the "
                 "other gives a low F1."),
    ("ROC-AUC", "A single number for how well the model separates the two groups. 0.5 is "
                "guessing, 1.0 is perfect. Ours is 0.83."),
    ("Logistic regression", "A simple, well-understood model that gives a real percentage and can "
                            "explain which input mattered. That is why we chose it."),
    ("Reputation prior", "A rule outside the model: the most popular websites are not flagged on "
                         "the name alone."),
    ("API", "The doorway the app uses to ask the server for an answer."),
]

NUMBERS = [
    ["Links in the data", "17,730 - half phishing, half safe"],
    ["Phishing links removed", "4,236 (32%) - they sat on hacked real websites"],
    ["Links kept for testing", "3,573, from websites never seen in training"],
    ["Accuracy / F1 / ROC-AUC", "75.4% / 0.740 / 0.829"],
    ["False-positive rate", "19.8% alone; almost none on popular sites with the rule"],
    ["Cross-check", "Five separate splits, F1 0.727 - the result is stable"],
    ["Tests", "10 of 10 end-to-end tests pass"],
    ["Speed", "20-130 milliseconds per link"],
    ["Cost", "KSh 0 - free data, free tools, free hosting"],
]

STEPS = [
    "Keep only the registered domain, so www. and the page path are ignored.",
    "Turn that domain into seventeen numbers: length, digits, hyphens, ending, brand name and so on.",
    "The model turns those numbers into a score between 0 and 1.",
    "The score becomes a band - likely safe, suspicious, or likely phishing.",
    "The reasons are written out from the same numbers that raised the score.",
    "The scan is stored so the history page can show it later.",
]

TRAPS = [
    "Do not say the 97% figures are wrong. Say they are measured on data with a flaw.",
    "Do not say blocklists are useless. Say they are always one step behind, and we complement them.",
    "Do not promise it catches everything. Say it judges the name, and name is not the whole story.",
    "If you do not know, say so, then say how you would find out - name the test or the file.",
]


CHAPTERS = [
    ("One", "Shows the gap: lists only know links already reported, so we build a system that "
            "judges an unreported link and explains itself."),
    ("Two", "Reviews what others built, names their weaknesses, and states the gap we fill - "
            "honest evaluation plus explanation."),
    ("Three", "The plan: requirements, feasibility, the development model, and the five design "
              "diagrams."),
    ("Four", "The build: architecture, code, database, tests and deployment, with the real "
             "numbers and the changes we made to the plan."),
    ("Five", "What we recommend, what we would do next, and what the project concludes."),
]

DEMO = [
    "Open the app and paste http://safaricom-secure-login.tk/verify - show the red band and the reasons.",
    "Paste https://www.google.com/ - show it passes, and point out the 'established domain' label.",
    "Paste http://equitybankk.co.ke/ - show the 'did you mean equitybank.co.ke' line.",
    "Open the History page - show the scans were stored.",
    "Open the Model page - show the comparison table and the false-positive column.",
    "Say the sentence: 'it never opened any of those sites.'",
]

CONFUSION = [
    ("Safe links judged safe", "1,442"),
    ("Safe links wrongly flagged", "355"),
    ("Phishing links caught", "1,252"),
    ("Phishing links missed", "524"),
]

ASK_HIM = [
    "Four chapters as the guidelines say, or five as the marking scheme says?",
    "Is Chapter Three's length acceptable given the five required diagrams?",
    "Should each chapter keep its own reference list, or share one at the end?",
]


def small(p: Paper, text: str, *, bold=False, size=10, space_after=2):
    para = p.para(text, bold=bold, align="left", space_after=space_after)
    for r in para.runs:
        r.font.size = Pt(size)
    return para


def qa(p: Paper, q: str, a: str, n: int):
    para = p.para(f"{n}.  {q}", align="left", space_after=1)
    for r in para.runs:
        r.bold = True
        r.font.size = Pt(10.5)
    body = p.para(a, align="left", space_after=7)
    for r in body.runs:
        r.font.size = Pt(10.5)


def main():
    p = Paper()
    p.doc.styles["Normal"].paragraph_format.line_spacing = 1.15

    p.para("REVIEW CHEAT SHEET", bold=True, align="center", size=15, space_after=2)
    p.para("Nyavu - COMP324 Team Project - Kabarak University - November 2026",
           align="center", size=10, space_after=10)

    p.para("If you freeze, say these three things", bold=True, size=12, space_after=3)
    for t in ("1.  It judges a link from the address alone, explains why, and costs nothing to run.",
              "2.  Our 75.4% is the honest number once the usual data mistake is removed.",
              "3.  Next we would add page content and move the check to the moment of the click."):
        small(p, t, size=10.5, space_after=2)

    p.para("How it works, in sixty seconds", bold=True, size=12, space_after=3, space_before=8)
    for i, s in enumerate(STEPS, 1):
        small(p, f"{i}.  {s}", size=10.5, space_after=1)

    p.para("CRITICAL - expect these", bold=True, size=12, space_after=4, space_before=10)
    for i, (q, a) in enumerate(CRITICAL, 1):
        qa(p, q, a, i)

    p.para("IMPORTANT - likely", bold=True, size=12, space_after=4, space_before=8)
    for i, (q, a) in enumerate(IMPORTANT, 1):
        qa(p, q, a, i)

    p.para("USEFUL - if there is time", bold=True, size=12, space_after=4, space_before=8)
    for i, (q, a) in enumerate(USEFUL, 1):
        qa(p, q, a, i)

    p.para("Numbers to have on the tip of your tongue", bold=True, size=12, space_after=4,
           space_before=10)
    for label, value in NUMBERS:
        para = p.rich([(f"{label}: ", {"bold": True}), (value, {})], space_after=2)
        for r in para.runs:
            r.font.size = Pt(10)

    p.para("Things not to say", bold=True, size=12, space_after=3, space_before=10)
    for t in TRAPS:
        small(p, f"-  {t}", size=10.5, space_after=2)

    p.para("Words you should be able to define in one line", bold=True, size=12, space_after=3,
           space_before=10)
    for term, meaning in GLOSSARY:
        para = p.rich([(f"{term} - ", {"bold": True}), (meaning, {})], space_after=2)
        for r in para.runs:
            r.font.size = Pt(10)

    p.para("What each chapter says, in one line", bold=True, size=12, space_after=3,
           space_before=10)
    for n, line in CHAPTERS:
        para = p.rich([(f"Chapter {n}: ", {"bold": True}), (line, {})], space_after=2)
        for r in para.runs:
            r.font.size = Pt(10)

    p.para("The demo, in order", bold=True, size=12, space_after=3, space_before=10)
    for i, step in enumerate(DEMO, 1):
        small(p, f"{i}.  {step}", size=10.5, space_after=1)

    p.para("If they push on the numbers", bold=True, size=12, space_after=3, space_before=10)
    for label, value in CONFUSION:
        para = p.rich([(f"{label}: ", {"bold": True}), (value, {})], space_after=2)
        for r in para.runs:
            r.font.size = Pt(10)
    small(p, "Out of 3,573 held-out links: 2,694 correct, 879 wrong. Precision 77.9%, recall "
             "70.5%. Recall is the weaker half - we miss about three phishing links in ten.",
          size=10, space_after=4)

    p.para("Questions to put to the panel", bold=True, size=12, space_after=3, space_before=10)
    for q in ASK_HIM:
        small(p, f"-  {q}", size=10.5, space_after=2)

    path = os.path.join(OUT, "Team_Project_Review_Cheat_Sheet.docx")
    p.save(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
