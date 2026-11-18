# Report review against Chapter One

Checked on 19 November against `docs/Team_Project_Chapters_1-5.docx`, the version that
includes Chapter Five. This is the comparison between what the report promises and what the
artefact now does, with the corrections that follow from it.

## The objectives, one at a time

### General objective
"To develop a machine-learning-based web and mobile application that assesses submitted URLs
for phishing and communicates the basis of that assessment."

**Met, with one wording problem.** The web application is delivered and has grown well past
the sketch: bulk screening, history, optional accounts, a printable verdict. Mobile delivery
by progressive web application is exactly what the report claims, and it is true. But the
repository now also contains a **browser extension** and a **native Android application**,
and section 1.7 says the study "does not implement browser or operating-system integration".
That sentence is no longer true. Either the artefacts are described as beyond-scope work
appended to the study, or the scope paragraph changes. The report cannot say both.

### Specific objective I: feature set and dataset preparation
**Met.** Seventeen domain-level features and character n-grams of the host; a labelled
dataset assembled from public feeds and popularity rankings; a domain-disjoint partition.
Chapter Four describes it, and `ml/artifacts/metrics.json` records it: 17,730 addresses,
8,865 of each class, 16,185 distinct registrable domains.

### Specific objective II: implement and compare classifiers, select the best
**Met, and better supported than the report says.** Three classifiers were compared and the
logistic regression was deployed with the reason stated: the linear SVM scored marginally
higher but produces no calibrated probability. What the report does not yet mention is the
calibration check that was actually run. Platt scaling and isotonic regression both left the
Brier score unchanged at 0.1674 to four decimal places, which is the evidence for the claim
"it produces calibrated probabilities". That belongs in 4.9, because at present the claim is
asserted where it could be shown.

### Specific objective III: accuracy **and clarity of explanation to non-expert users**
**Half met.** Accuracy is measured thoroughly. Clarity is not evaluated: section 5.6 admits
"the informal feedback used here" and proposes "a formal usability study" as future work,
while 5.5 states that "all four specific objectives were met".

Both halves of that are wrong. There are **three** specific objectives, not four. And the
third one promises an evaluation of explanation clarity that has not been carried out.
As written, the report makes a claim the evidence does not support, which is the single
most exposed sentence in the document.

Two ways to close it, and only one of them is honest quickly:

1. **Run the evaluation.** Eight to ten non-experts, five addresses each spanning the three
   bands, three questions per address: what is the verdict, what is the reason, what would
   you do. Report comprehension as a proportion and the time taken. An afternoon of work,
   and it turns a soft claim into a measured one
2. **Weaken the claim.** State that clarity was assessed by design review and informal
   feedback, that it was not measured with representative users, and mark objective III as
   partially met. Defensible, but it invites the question of why the one objective about
   communication was not tested

The recommendation is the first, with the second as the fallback if no participants can be
found before submission.

## Numbers that do not agree

| claim | where | what the artefact says |
| --- | --- | --- |
| "26,202 addresses" | 5.5 | 17,730 (14,157 train, 3,573 hold-out) |
| "all four specific objectives" | 5.5 | three objectives |
| "does not implement browser or OS integration" | 1.7 | an extension and a native app exist |
| "browser extension ... would move the check" as future work | 5.6 | already built |

The first is a stale figure from an earlier dataset and must be corrected, not explained:
a report that contradicts its own Chapter Four in the conclusions is the kind of thing a
marker reads first.

## Chapter Five moves into Chapter Four

The instruction from the supervisor is that Chapter Five's content belongs in Chapter Four.
Reading the two, this is mostly a de-duplication rather than a move, because Chapter Four
already covers most of it:

| Chapter Five | Where it belongs |
| --- | --- |
| 5.1 Introduction | deleted; 4.1 already introduces |
| 5.2 Proposed technology and reasons | folds into 4.2 Development Environment |
| 5.3 Summary of modules | overlaps 4.6 User Interface Modules; keep the module table, drop the prose |
| 5.4 Test regime | merges with 4.9 Code Testing, which already reports the same runs |
| 5.5 Conclusions | becomes 4.13, which already exists under that name |
| 5.6 Recommendations | becomes the future-work half of 4.13 |

After the merge the report ends at Chapter Four, as instructed, and one set of numbers is
stated once.

## Order of work

1. ~~Merge Chapter Five into Chapter Four and renumber~~ **done** in
   `docs/Team_Project_Chapters_1-4_v2.docx`: 5.2 became 4.2.1, 5.3 became 4.6.1, 5.4 became
   4.9.1, and 5.5/5.6 became 4.13.1 and 4.13.2 under the existing conclusion. The Chapter
   Five shell and its introduction were removed, and the document now ends at Chapter Four
2. ~~Correct the contradictions~~ **partly done**: the dataset figure now reads 17,730 and the
   conclusions no longer claim all objectives were met. Still to change: section 1.7, which
   says the study does not implement browser or operating-system integration, and 5.6's
   listing of an extension as future work, which now exist
3. Add the calibration evidence to 4.9: Brier 0.1674, unchanged by Platt scaling and by
   isotonic regression, which is why no calibrator ships
4. Run the explanation-clarity test, or state the limitation plainly. The merged conclusions
   currently state it plainly
5. Confirm the corrected changes list at the next supervision meeting
