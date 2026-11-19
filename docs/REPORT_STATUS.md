# Status report

As things stand, for review and presentation. Every figure here is read from the artefacts in
this repository, not recalled: `ml/artifacts/metrics.json`, `docs/Team_Project_Chapters_1-4_v2.docx`,
and the running service.

## 1. What the project set out to do

| | |
| --- | --- |
| **General objective** | develop a machine-learning-based web and mobile application that assesses submitted URLs for phishing and communicates the basis of that assessment |
| **Specific I** | design a lexical and structural feature set, with a dataset preparation procedure, that captures what distinguishes phishing addresses |
| **Specific II** | implement and compare classifiers, and select the best-performing for deployment |
| **Specific III** | evaluate the accuracy of the classifier **and the clarity of the explanations it presents to non-expert users** |

## 2. Do we meet them

| objective | verdict | evidence |
| --- | --- | --- |
| General | **met for the web application**, with a caveat on "mobile" below | live service, four screens, verdict explained in the same response |
| Specific I | **met** | 17 domain-level features and character n-grams of the host; 17,730 labelled addresses across 16,185 registrable domains, partitioned by domain so no domain appears in both halves |
| Specific II | **met** | three classifiers trained and compared; the logistic regression deployed for calibrated probabilities, with its F1 within 0.002 of the best |
| Specific III | **half met**, and this is the honest weak point | accuracy is measured; the clarity of the explanations to non-expert users is **not** evaluated. The report's conclusions now say so |

**On "mobile":** the general objective says web *and mobile*. What is delivered is a
progressive web application that installs on a phone and is styled for it. A native Android
application exists but is **work in progress** and is excluded from this report.

## 3. The model, measured

Evaluated on a hold-out of 3,573 addresses drawn from domains that do not appear in the
14,157 training addresses.

| classifier | accuracy | F1 | precision | recall | ROC-AUC | false positive rate |
| --- | --- | --- | --- | --- | --- | --- |
| **Logistic Regression** (deployed) | **0.754** | **0.740** | 0.779 | 0.705 | 0.829 | **19.8%** |
| Linear SVM | 0.756 | 0.742 | 0.781 | 0.708 | 0.827 | 19.6% |
| Random Forest | 0.713 | 0.681 | 0.761 | 0.617 | 0.783 | 19.1% |

The linear SVM scores 0.002 higher on F1, which is inside the noise of a single split. The
logistic regression was chosen because it produces a calibrated probability, and the interface
reports one.

**Calibration was checked, not assumed.** Brier score 0.1674 raw; Platt scaling 0.1674;
isotonic regression 0.1675. The calibrators add nothing, so none ships.

**Reputation prior.** An address on a domain inside the Tranco top 100,000 is held at a
ceiling of 15 and reported as an established domain, because name-level evidence is not enough
to flag a site that is demonstrably used. The response states that this was applied. Its cost
is stated too: a phishing page hosted on a popular domain will not be caught by name.

## 4. What is delivered

| surface | state |
| --- | --- |
| Detector with the address examination | live |
| Verdict with dissection, score, reasons and folded working | live, printable |
| Bulk screening, CSV upload | live, up to 200 addresses |
| History, optional Google account | live and verified end to end |
| Model page with the comparison above | live |
| Learn pages, About | live |
| Progressive web application | installable, offline shell |

The service runs on Render with Neon Postgres. Automated checks in `tests/run_tests.py` cover
input validation, the reputation ceiling, the dissection, and the bulk path.

## 5. What is not done, stated plainly

1. **Explanation clarity is not evaluated.** Specific objective III asks for it. We have design
   review and informal feedback, not a study with representative users. The fix is an afternoon
   with eight to ten people and a printed form; it has not happened.
2. **The native Android application is work in progress** and is excluded from this report.
   A React Native port has the examination, the verdict sheet and the shell; it has not been
   run on a device and is not distributed.
3. **Measurement is undecided.** There is no analytics, because "we never see your links" and
   "we track everything" cannot both be true, and the second needs a decision that has not been
   taken.
4. **The real device pass is outstanding** for the web application too: the seven-second
   examination, the scroll after a scan and the card at true size have been checked in
   headless browsers, not on a phone in a hand.

## 6. The corrections already made to the report

- Chapter Five has been merged into Chapter Four, as directed: 5.2 became 4.2.1, 5.3 became
  4.6.1, 5.4 became 4.9.1, and 5.5/5.6 became 4.13.1 and 4.13.2
- the dataset figure now reads 17,730, where the conclusions said 26,202
- the conclusions no longer claim all objectives were met; they state that accuracy was
  measured and clarity was not
- `docs/Team_Project_Chapters_1-4_v2.docx` is the merged document; the original is untouched

Still to change in Chapter One, and worth saying aloud at the defence: section 1.7 says the
study does not implement browser or operating-system integration, while this repository now
contains a browser extension and an Android application. Either the scope sentence changes or
those are described as beyond-scope work.
