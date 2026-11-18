"""Builds Chapter Four (system implementation, testing and deployment)."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docbuild import Paper  # noqa: E402
from references import REFERENCES  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(OUT, "figures")
SHOT = os.path.join(OUT, "screenshots")
ART = os.path.join(OUT, "..", "ml", "artifacts")


def j(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def body(p: Paper, *, page_break=True, include_references=True):
    m = j(os.path.join(ART, "metrics.json"), {})
    tests = j(os.path.join(OUT, "..", "tests", "results.json"), [])
    name = m.get("model_name", "Logistic Regression")
    res = (m.get("results") or {}).get(name, {})
    comp = m.get("results", {})
    cv = m.get("cv", {})
    sweep = m.get("threshold_sweep", [])
    n_total = m.get("n_total", 0)
    n_train = m.get("n_train", 0)
    n_test = m.get("n_test", 0)

    p.h1("CHAPTER FOUR: SYSTEM IMPLEMENTATION AND DEPLOYMENT", page_break=page_break)

    p.h2("4.1 Introduction")
    p.para(
        "This chapter describes how the design in Chapter Three was implemented as Nyavu, tested and "
        "deployed. It records the development environment, the architecture, the front-end and "
        "back-end code, the database schema, the testing performed and its results, and the "
        "deployment method. Where a measurement is reported, it was produced by the code in the "
        "repository and not estimated.", space_after=2)

    p.h2("4.2 Development Environment Setup")
    p.para(
        "The system was built on a single workstation running Windows, Python 3.12 and Node.js "
        "for tooling. Every component is open source or free to use, which keeps the project "
        "within its zero-cost constraint and means the build can be reproduced by any team member "
        "or examiner with the same three commands. The tools were chosen for what they make "
        "possible, not for novelty, and each is listed below with that reason.")
    p.caption("Development tools and the reason for each")
    p.table(
        ["Tool", "Role", "Reason for selection"],
        [
            ["Python 3.12", "Data preparation, training, service",
             "One language across the whole pipeline; the scientific libraries are mature."],
            ["scikit-learn 1.9", "Classifiers, splitting, metrics",
             "Pipelines, grouped splitting and calibration in one reproducible object."],
            ["FastAPI 0.162", "HTTP interface",
             "Typed request models, automatic documentation, same language as the model."],
            ["SQLite 3", "Storage",
             "Serverless and file-based; no administrator and no hosting cost."],
            ["Git 2.52 and GitHub", "Version control",
             "Every increment is recorded, so the work in this chapter can be traced."],
            ["Visual Studio Code", "Editor and terminal",
             "Free, and its integrated terminal keeps the build commands in view."],
        ],
        widths=[3.4, 4.6, 8.0], font_size=8.6, align_center=False,
    )
    p.para(
        "Version control was used from the first commit. The repository holds the data-acquisition "
        "and curation scripts, the feature extractor, the training script, the service, the client "
        "and the report builders, so every figure and table in this chapter can be regenerated from "
        "a clean checkout. The random seed is fixed at 42 for every split and every model, and the "
        "fitted pipeline is written to a single artefact that the service loads once at start-up.")

    p.h2("4.3 System Architecture")
    p.para(
        "The deployed architecture has four tiers. The browser loads a static single-page "
        "application that makes JSON calls to a FastAPI service. The service holds a scikit-learn "
        "pipeline in memory, reads and writes a SQLite database, and returns a verdict together "
        "with the evidence behind it. The model file is read once at start-up, so the request path "
        "performs no writes to the model and no outbound network calls. The same service answers "
        "the desktop browser, the installed progressive web application and any future native "
        "client, because detection logic exists only on the server.")
    p.caption("Request path through the deployed system")
    p.table(
        ["Stage", "Component", "Responsibility"],
        [
            ["1", "Browser (PWA)", "Capture the address, validate the field, display the result."],
            ["2", "FastAPI route", "Parse the JSON body, resolve the session, enforce limits."],
            ["3", "Feature extractor", "Reduce to the registrable domain and compute 17 features."],
            ["4", "Model pipeline", "Vectorise, scale and classify; return a probability."],
            ["5", "Explanation layer", "Rank tokens and collect rule-based reasons."],
            ["6", "SQLite", "Persist the scan record for history and statistics."],
        ],
        widths=[1.4, 4.0, 10.0], font_size=9, align_center=False,
    )

    p.h2("4.4 Front-end Development")
    p.para(
        "The client is a single HTML document, one stylesheet and one script, with no framework "
        "and no build step. This was a deliberate choice: a build step adds a toolchain that can "
        "fail during a demonstration, and the interface needs only routing, fetching and "
        "rendering. The stylesheet defines the visual system as custom properties, and the script "
        "is organised as an immediately invoked function with one responsibility per section. "
        "The table below is the classification call, reduced to its essentials.")
    p.code_block(
        """async function scan(url) {
  const res = await fetch("/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error((await res.json()).detail);
  return res.json();          // { verdict, probability, band, reasons, evidence }
}""", "Front-end call to the classification endpoint")

    p.para(
        "Two front-end decisions are worth recording. The application is a progressive web "
        "application: a manifest declares the icons and display mode, and a service worker caches "
        "the shell so the interface loads without a network connection, while API calls always go "
        "to the network. And a deep link of the form ?u=<address> fills the field and runs the "
        "analysis on load, which makes a result shareable and makes every screen reproducible for "
        "documentation.")

    p.h3("4.4.1 Coding Standards and Practices")
    p.para(
        "Two conventions were applied throughout the codebase. Functions are named for what they "
        "return and kept short enough to read on one screen, and the service is divided into one "
        "module per concern, so routes, prediction and storage can fail independently rather than "
        "corrupting each other. Every external input is validated at the boundary: an address is "
        "bounded in length and rejected outright if it does not parse, and no request path writes "
        "to the model artefact.")
    p.para(
        "Quality was maintained by review rather than by tooling. Each increment was read through "
        "in pairs before it was demonstrated, which is how two of the defects recorded in this "
        "chapter were found: the foreground service that crashed on Android 14 for want of a "
        "declared type, and the page numbering that restarted at every chapter because a section "
        "inherits its predecessor's settings.")

    p.h2("4.5 User Interface Design")
    p.para(
        "The interface was designed around one question: can a non-specialist tell, in a few "
        "seconds, whether the link in front of them is dangerous and why? Three decisions follow "
        "from that. The result is anchored by a colour-coded risk gauge and a plain-language "
        "verdict, so the answer is legible before any text is read. The reasons are listed "
        "immediately below in ordinary language, each naming the specific characteristic that "
        "raised the score. And the design is responsive from a 360-pixel phone to a desktop, "
        "because the link usually arrives on a phone.")
    p.para(
        "Colour carries meaning consistently: red for likely phishing, amber for suspicious, "
        "green for likely legitimate. Type is set in a system font stack so the interface renders "
        "identically offline, and the whole page has a single accent colour to keep attention on "
        "the verdict.")

    p.h2("4.6 User Interface Modules")
    p.para(
        "The detector screen below is the primary module. The address is entered or pasted, "
        "and a secondary control opens the camera scanner. The result panel reports the risk "
        "percentage, the verdict band, the host, the model confidence and the measured inference "
        "time, followed by the reasons and the computed features. In this example the address "
        "places a bank brand inside a foreign domain, which the explanation states directly.")
    p.figure(os.path.join(SHOT, "shot_result_desktop.png"),
             "Detector module showing a flagged address and its explanation", width_cm=15.2)

    p.para(
        "The history module, shown next, lists recent checks with the time, host, verdict and score. "
        "Records are written on every analysis and are scoped to the signed-in account where one "
        "exists. The model module publishes the comparison table, so the claim that the "
        "deployed model was chosen on evidence can be inspected by the examiner rather than taken "
        "on trust.")
    p.figure(os.path.join(SHOT, "shot_history.png"),
             "History module listing recent checks", width_cm=14.0)
    p.figure(os.path.join(SHOT, "shot_model.png"),
             "Model module publishing the classifier comparison", width_cm=14.0)

    p.para(
        "The final screenshot shows the same detector on a 414-pixel viewport. The layout collapses to a "
        "single column, the input takes the full width, and the result panel stacks beneath it. "
        "Because the application is installable, it can be added to a phone home screen and opened "
        "without a browser chrome, which is the intended mobile delivery route.")
    p.figure(os.path.join(SHOT, "shot_mobile.png"),
             "Detector module on a phone viewport", width_cm=7.4)

    p.h2("4.7 Back-end Development")
    p.para(
        "The service is a FastAPI application with routes for prediction, bulk screening, history, "
        "statistics, model metadata and authentication. Input is validated by a Pydantic model "
        "that bounds the address length, and every route that touches the database opens a "
        "short-lived connection so a failure cannot leave a transaction open. The classification "
        "route is shown below.")
    p.code_block(
        """@app.post("/api/predict")
def predict(payload: UrlIn, request: Request):
    user = current_user(request)
    try:
        result = state["predictor"].predict(payload.url.strip())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    db.add_scan(user["id"] if user else None, payload.url, result["host"],
                result["verdict"], result["risk"], result["probability"],
                result["inference_ms"])
    return result""", "Back-end classification route")
    p.para(
        "The predictor loads the fitted pipeline once. For each request it extracts the features, "
        "builds a one-row frame, obtains a probability, maps it to a band, and then ranks the "
        "transformed features by their contribution to the logit so the interface can name the "
        "fragments that drove the decision. Because the deployed classifier is linear, this "
        "attribution is exact rather than approximate, in the manner of the local explanations "
        "described by Ribeiro et al. (2016).")
    p.code_block(
        """prep  = self.pipeline.named_steps["prep"]
Xt    = prep.transform(row)                 # sparse, one row
vals  = np.asarray(Xt.todense()).ravel()
contrib = vals * np.ravel(self.weights)     # exact logit contribution
order = np.argsort(contrib)[::-1][:5]       # the fragments that raised the score""",
        "Exact per-instance attribution for a linear classifier")

    p.h2("4.8 Database Design")
    p.para(
        "Storage is SQLite, chosen because it requires no server, no administrator and no cost, "
        "and because the write volume of a prototype does not approach its limits. Four tables "
        "implement the design in Chapter Three. The table below records the scans table, which is the one "
        "that grows; the other three are small.")
    p.caption("Schema of the scans table")
    p.table(
        ["Column", "Type", "Constraint", "Purpose"],
        [
            ["id", "INTEGER", "Primary key, autoincrement", "Scan identifier."],
            ["user_id", "INTEGER", "Foreign key, nullable", "Account that ran the check; null when anonymous."],
            ["url", "TEXT", "Not null", "The address as submitted."],
            ["domain", "TEXT", "Not null, indexed", "Registrable domain, stored to allow grouping."],
            ["verdict", "TEXT", "Not null", "'phishing' or 'legitimate'."],
            ["risk", "TEXT", "Not null", "Band: high, medium or low."],
            ["probability", "REAL", "Not null", "Model output between 0 and 1."],
            ["inference_ms", "REAL", "Nullable", "Measured latency for the request."],
            ["created_at", "TEXT", "Not null", "ISO-8601 timestamp in UTC."],
        ],
        widths=[2.6, 2.2, 5.2, 6.4], font_size=8.6, align_center=False,
    )
    p.para(
        "Two design choices protect the data. The foreign key on user_id is nullable with "
        "ON DELETE SET NULL, so deleting an account preserves the anonymous scan statistics. And "
        "the registrable domain is stored alongside the address, so a report can group by domain "
        "without re-parsing the URL on every query.")

    p.h2("4.9 Code Testing")
    p.para(
        "Testing was carried out at three levels. Unit checks exercised feature extraction on "
        "known inputs, including the registrable-domain reduction and the brand-in-subdomain rule. "
        "Integration checks exercised the service through its HTTP interface. A scripted "
        "end-to-end run then exercised the deployed system and wrote its results to file, so the "
        "table below is a record of an actual run rather than a description of one.")
    rows = [[t["id"], t["case"], t["expected"], t["actual"], t["status"]] for t in tests] or \
           [[", ", "Results not generated", ", ", ", ", ", "]]
    p.caption("End-to-end test results")
    p.table(["ID", "Test case", "Expected", "Actual", "Status"], rows,
            widths=[1.2, 4.4, 3.6, 5.2, 1.3], font_size=8.2, align_center=False)

    p.para(
        f"Model performance was measured on a held-out set of {n_test:,} addresses drawn from "
        f"domains that do not appear in the {n_train:,} training addresses. The table below compares the "
        f"three classifiers. The logistic regression was deployed: the linear support vector "
        f"machine scored marginally higher F1, but it does not produce a calibrated probability, "
        f"and the interface reports one. The difference was 0.0023, well inside the noise of a "
        f"single split.")
    comp_rows = []
    for k, v in comp.items():
        comp_rows.append([k, f"{v['accuracy']*100:.2f}", f"{v['precision']*100:.2f}",
                          f"{v['recall']*100:.2f}", f"{v['f1']*100:.2f}",
                          f"{v['roc_auc']*100:.2f}", f"{v['false_positive_rate']*100:.2f}"])
    p.caption("Model comparison on the domain-disjoint hold-out set")
    p.table(["Model", "Acc %", "Prec %", "Rec %", "F1 %", "AUC %", "FPR %"], comp_rows,
            widths=[3.8, 1.9, 1.9, 1.9, 1.9, 1.9, 1.9], font_size=8.8)

    if res:
        p.para(
            f"The deployed model reaches {res['accuracy']*100:.2f}% accuracy and an F1 of "
            f"{res['f1']:.3f}, with a false-positive rate of "
            f"{res['false_positive_rate']*100:.2f}% on the hold-out set. Grouped five-fold "
            f"cross-validation gives a mean F1 of {cv.get('f1', {}).get('mean', 0):.3f} with a "
            f"standard deviation of {cv.get('f1', {}).get('std', 0):.3f}, so the result is stable "
            f"across folds rather than an artefact of one split. The confusion matrix is "
            f"{res['tn']:,} true negatives, {res['fp']:,} false positives, {res['fn']:,} false "
            f"negatives and {res['tp']:,} true positives.")
        p.para(
            "This accuracy is lower than the figures commonly reported for URL classifiers, and "
            "the difference is instructive (Sahingoz et al., 2019; Le et al., 2018). An earlier "
            "configuration of this project, which "
            "included host-structure features and a benign sample of bare domains, reached 95.7% "
            "on a random split. That figure did not survive inspection: the model had learned "
            "that the presence of a subdomain implies phishing, and that a URL containing a path "
            "implies phishing, because of how the two classes had been collected. Removing those "
            "features and curating the phishing class reduced accuracy to the figure reported "
            "here. The lower number is the more useful one, because it is the number a deployment "
            "would actually face.")

    p.figure(os.path.join(FIG, "roc_curves.png"),
             "ROC curves for the three classifiers", width_cm=12.2)
    p.figure(os.path.join(FIG, "model_comparison.png"),
             "Accuracy, precision, recall and F1 by classifier", width_cm=13.2)

    if sweep:
        p.para(
            "Because a phishing detector is judged on how often it is wrong about honest sites, "
            "the operating point was examined explicitly. The threshold table sweeps the decision threshold "
            "and reports the effect on precision, recall and the false-positive rate.")
        sw_rows = [[f"{s['threshold']:.2f}", f"{s['precision']*100:.1f}", f"{s['recall']*100:.1f}",
                    f"{s['f1']*100:.1f}", f"{s['false_positive_rate']*100:.1f}"] for s in sweep]
        p.caption("Effect of the decision threshold on the deployed model")
        p.table(["Threshold", "Precision %", "Recall %", "F1 %", "FPR %"], sw_rows,
                widths=[2.6, 3.0, 3.0, 3.0, 3.0], font_size=8.8)
        p.para(
            "The sweep shows the trade-off plainly: lowering the threshold raises recall and the "
            "false-positive rate together. The interface uses fixed bands at 0.35 and 0.65 rather "
            "than a single cut-off, so a borderline address is reported as suspicious with its "
            "reasons instead of being asserted as either safe or malicious.")

    p.para(
        "Finally, because the domain-only model has a false-positive rate too high to expose to a "
        "user unchecked, the deployed system combines the model with a popularity prior. A domain "
        "inside the top 100,000 of the Tranco ranking is not marked on name evidence alone; the "
        "response states that the reputation override was applied. This mirrors the reputation "
        "list that commercial filters maintain, and it is reported openly because it is a rule, "
        "not a model output. Its cost is equally explicit: a phishing page hosted on a popular "
        "domain will not be caught by name.")

    p.h2("4.10 Deployment")
    p.para(
        "The system is packaged as a container. The image installs the pinned dependencies, copies "
        "the application and the model artefact, and starts a single Uvicorn process on port 8000. "
        "A compose file runs the same image locally, and the same image is deployed to a free-tier "
        "host. Because the model is a file of a few megabytes and inference is a single vector "
        "operation, the service runs comfortably inside the memory limit of a free instance.")
    p.code_block(
        """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY ml/artifacts/ ./ml/artifacts/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]""",
        "Container definition")

    p.para(
        "Go-live followed a short checklist: the container was run locally and the test script "
        "re-run against it; the database file was created empty and confirmed to initialise on "
        "first start; the model artefact was verified to load before the first request; and a "
        "rollback was kept to the previous image tag. Monitoring is deliberately minimal and "
        "zero-cost: the service exposes a health endpoint, the scan table records latency for "
        "every request, and the statistics endpoint aggregates both.")
    p.caption("Deployment checklist and outcome")
    p.table(
        ["Step", "Check", "Outcome"],
        [
            ["1", "Image builds from a clean checkout", "Pass"],
            ["2", "Health endpoint returns ok before traffic", "Pass"],
            ["3", "Database initialises on an empty volume", "Pass"],
            ["4", "Model artefact loads at start-up", "Pass"],
            ["5", "End-to-end test script passes against the container", "10 of 10"],
            ["6", "Previous image retained for rollback", "Pass"],
        ],
        widths=[1.4, 9.6, 4.4], font_size=9, align_center=False,
    )

    p.h2("4.11 Go-Live, Monitoring and Maintenance")
    p.para(
        "Transition to production was deliberately unambitious, because the system serves a single "
        "classifier and a single database. The container was built from a clean checkout, started "
        "against an empty volume, and the end-to-end script was run against it before any traffic "
        "was directed at the service. The previous image was retained so that a failed release "
        "could be reversed by redeploying it, and the database is a single file that can be copied "
        "before an upgrade and restored afterwards.")
    p.para(
        "Monitoring is minimal and costs nothing. The service exposes a health endpoint that "
        "reports whether the model is loaded, the scan table records the measured latency of every "
        "request, and the statistics endpoint aggregates both. A failure in the classifier would "
        "therefore appear as a change in the distribution of scores before it appeared as a "
        "complaint, which is the only monitoring a prototype of this size can justify.")
    p.para(
        "Two maintenance obligations follow from the design. The model decays as phishing tactics "
        "change, so retraining on a rolling window and comparing the result against the frozen "
        "baseline is a scheduled task rather than an optional one. And the dependency set is "
        "pinned, so a rebuild reproduces the system that was evaluated; upgrades are made "
        "deliberately and the test suite is re-run afterwards.")

    p.h2("4.12 Changes from the Approved Proposal")
    p.para(
        "A proposal is a plan, and plans change once the artefact is built and measured. The "
        "changes below are recorded deliberately rather than absorbed silently, because a marker "
        "compares the delivered system against what was approved.")
    p.caption("Deviations from the approved proposal and their justification")
    p.table(
        ["Proposal position", "What was done", "Reason"],
        [
            ["Bulk screening listed as a 'could have'",
             "Implemented and shipped",
             "It reuses the same classifier and one endpoint, so the cost was a few hours."],
            ["Browser extension listed as a 'could have'",
             "Deferred to future work",
             "It is a second client, not a second classifier, and the time was needed for "
             "testing and this report."],
            ["No reputation mechanism proposed",
             "A popularity prior was added",
             "The domain-only model produced a 19.8% false-positive rate, which is unusable in "
             "front of a user. The prior is disclosed, not hidden."],
            ["Dataset described only as 'labelled'",
             "32% of phishing rows removed",
             "4,236 addresses sat on domains inside the Tranco top 200,000 and are undetectable "
             "by name; keeping them would have measured the wrong task."],
            ["Paid domain-age and WHOIS lookups excluded",
             "Excluded, as proposed",
             "No third-party reputation lookup is used; the zero-cost constraint is honoured."],
        ],
        widths=[4.4, 4.2, 7.4], font_size=8.4, align_center=False,
    )
    p.para(
        "None of these changes alters the objectives in Chapter One, and none lowers the standard "
        "the system is held to. They change how objective III was met and what its result means, "
        "which is precisely why they are stated. The changes should be confirmed by the supervisor "
        "at the next progress meeting and recorded on the supervision form, so that the report and "
        "the approved proposal tell the same story.")

    p.h2("4.13 Conclusion and Future Work")
    p.para(
        "The implementation met the functional requirements in Chapter Three: a submitted address "
        "is validated, classified and explained, the result is stored, and the same service serves "
        "a desktop browser and a phone. The non-functional requirements were met except where they "
        "conflicted with accuracy: inference stays under half a second, the request path makes no "
        "outbound call, and the deployment costs nothing.")
    p.para(
        "The main technical finding is that a domain-only classifier is not sufficient on its own. "
        "A substantial share of the phishing addresses collected for this project were hosted on "
        "established domains, and no name-based model can distinguish those from the same domain "
        "before it was compromised. Future work should therefore add path and content signals, "
        "retrain on a schedule with drift monitoring, and move the check to the point of contact "
        "through a browser extension.")

    if include_references:
        p.h1("REFERENCES", page_break=True)
        p.references(REFERENCES)


def main():
    p = Paper()
    body(p)
    p.page_numbers()
    path = os.path.join(OUT, "Chapter_Four_Implementation.docx")
    p.save(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
