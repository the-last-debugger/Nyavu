"""Builds the Chapter Two submission (literature review, due 3 November 2026)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docbuild import Paper  # noqa: E402
from references import REFERENCES  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(OUT, "figures")


def body(p: Paper, *, page_break=True, include_references=True):
    p.h1("CHAPTER TWO: LITERATURE REVIEW", page_break=page_break)

    p.h2("2.1 Introduction")
    p.para(
        "This chapter reviews the literature and the existing systems that inform the project. "
        "It examines the tools currently used against phishing and where they fail, then reviews "
        "what is known about each of the four objectives in turn: the URL characteristics that "
        "separate phishing from legitimate addresses, the datasets used to train and test "
        "detectors, the classification models that have been applied to the problem, and the "
        "question of how a detection result should be communicated to a non-expert. The chapter "
        "closes with a concept map and a statement of the gap the project addresses.",
        space_after=2)

    p.h2("2.2 Review of Similar Systems and Their Weaknesses")
    p.para(
        "Four families of system are in current use, and each was designed for a different "
        "purpose. Blocklists and safe-browsing services collect addresses that have been reported, "
        "verify them, and publish them for browsers and mail gateways to check against. They are "
        "accurate on the addresses they contain, but their coverage is bounded by reporting. Sheng "
        "et al. (2009) evaluated several public blacklists and found that they missed a "
        "substantial proportion of live phishing pages and that detection lagged behind the life "
        "of the page. Moore and Clayton (2007) reached a similar conclusion from the other "
        "direction: because a phishing page is typically short-lived, a list can only ever "
        "describe yesterday's campaign. The weakness is structural rather than a matter of list "
        "size.")
    p.para(
        "Aggregator and reputation services such as VirusTotal and Netcraft combine many engines "
        "and add crawling, blocklist and registration data. They achieve broad coverage but "
        "return a verdict without a usable explanation, require a network round trip and, in the "
        "commercial tiers, a subscription. Content-based filters analyse the rendered page; they "
        "catch convincing imitations, but they must fetch the destination, which exposes the user "
        "to the page being judged and adds seconds of latency.")
    p.para(
        "Jain and Gupta (2022) survey the detection literature and reach a similar conclusion. "
        "Academic work has established that the address alone carries enough signal for practical "
        "classification. Sahingoz et al. (2019) extracted lexical features from 73,575 URLs and "
        "compared seven classifiers, reporting accuracies around 97% with a random forest. Le et "
        "al. (2018) applied character-level convolutional and recurrent networks to the raw URL "
        "string and reported comparable or better results without hand-engineered features. Both "
        "demonstrate feasibility; neither reports a false-positive rate that a user could act on, "
        "and neither ships an interface that explains its decision. The table below summarises "
        "the comparison.", space_after=2)

    p.caption("Comparison of existing approaches to phishing URL detection")
    p.table(
        ["System type", "Approach", "Strength", "Weakness"],
        [
            ["Blocklist / safe browsing",
             "Report, verify, publish; browser checks each request.",
             "Very low false positives on listed addresses.",
             "Reactive; blind to unreported addresses; no explanation."],
            ["Reputation and aggregator services",
             "Many engines plus crawl and registration data.",
             "Broad coverage; fast lookup.",
             "Cost, network dependency, opaque verdict."],
            ["Content-based filters",
             "Fetch and analyse the rendered page.",
             "Catches convincing visual imitations.",
             "Exposes the user to the page; latency; unusable offline."],
            ["Academic ML classifiers",
             "Lexical or character-level features with a trained model.",
             "Generalises to unseen addresses; fast.",
             "Accuracy reported without false-positive rate; often no interface."],
        ],
        widths=[3.3, 4.4, 4.0, 4.6], font_size=8.5, align_center=False,
    )

    p.para(
        "Taken together, the surveys of phishing detection agree that no single defensive layer "
        "is sufficient. Alkhalil et al. (2021) and Chiew et al. (2018) show that attacks adapt "
        "faster than lists are updated, Gupta et al. (2018) classify the countermeasures and note "
        "that each addresses only part of the lifecycle, and Jain and Gupta (2022) conclude that "
        "address-level models generalise furthest because they do not depend on prior reporting.")
    p.h2("2.3 URL Characteristics that Distinguish Phishing Addresses")
    p.para(
        "The features used by published detectors fall into three groups. Lexical features "
        "describe the string itself: its length, the number of dots, hyphens and digits, the depth "
        "of subdomain nesting, the length of the top-level domain and the presence of an IP "
        "address in place of a domain name. Host-level features describe the name that was "
        "registered, including its similarity to a well-known brand. Contextual features, such as "
        "domain age, certificate issuer or hosting network, require external lookups.")
    p.para(
        "Typosquatting is the best documented host-level signal. Agten et al. (2015) monitored "
        "popular domains over seven months and found that typo variants were registered in large "
        "numbers, many of them resolving to monetised or malicious content. Character substitution "
        "extends the same idea across alphabets: a Cyrillic character rendered beside Latin text "
        "is visually identical to the brand it imitates (Chiew et al., 2018). Brand names placed "
        "in a subdomain rather than the registered domain are a third variation, and are common "
        "where free hosting allows arbitrary subdomains.")
    p.para(
        "Contextual features improve accuracy but break the properties this project needs. "
        "Looking up domain age or certificate data requires network calls, adds latency, fails "
        "offline and introduces a dependency on third-party services that may rate-limit or "
        "disappear. The review therefore supports a design decision: the deployed model uses only "
        "features that can be computed from the address in a single pass, and treats contextual "
        "signals as future work.")

    p.h2("2.4 Datasets for Training and Evaluation")
    p.para(
        "Phishing corpora are usually built from community feeds. PhishTank collects submissions "
        "that volunteers verify, OpenPhish distributes a curated feed, and aggregators such as "
        "Phishing.Database merge several feeds into a single list. Legitimate addresses are drawn "
        "from traffic rankings. The Alexa Top Sites list that earlier studies relied on was "
        "withdrawn, and Pochat et al. (2019) showed that such rankings can be manipulated; their "
        "Tranco list addresses this by aggregating several providers over a rolling window and is "
        "now the usual choice for research.")
    p.para(
        "Three methodological problems recur. Class imbalance is common and inflates apparent "
        "accuracy if it is not handled. Label noise is inherent in community reporting, since a "
        "page can be taken down, re-registered or reported in error. Most importantly, related "
        "addresses leak across splits: a single phishing campaign may contribute dozens of URLs "
        "that share a domain, so a random split places near-duplicates in both training and test "
        "sets and produces accuracy figures that do not survive deployment. Splitting by "
        "registrable domain, and separating the two classes before sampling so that no host "
        "appears in both, avoids the leak. This project adopts both practices.")

    p.h2("2.5 Classification Models")
    p.para(
        "Published comparisons consistently find that the choice of model matters less than the "
        "quality of the features and the honesty of the evaluation. Sahingoz et al. (2019) found "
        "random forest and support vector machines at the top of a seven-model comparison, with "
        "naive Bayes and k-nearest-neighbours behind them. Deep models remove the feature "
        "engineering step: Le et al. (2018) learn directly from character sequences and report "
        "accuracy comparable to engineered-feature baselines, at the cost of training time, model "
        "size and interpretability.")
    p.para(
        "That last cost is decisive here. A linear model over character n-grams and scaled "
        "numeric features exposes a weight for every input, so the contribution behind a single "
        "verdict can be read directly from the coefficients. A tree ensemble gives feature "
        "importances but not per-instance reasons without additional machinery, and a neural "
        "network gives neither without an attribution method. The review therefore motivates "
        "comparing a linear model against a tree ensemble and a linear support vector machine, "
        "and preferring the linear model where the difference in F1 is small.")

    p.para(
        "Across these studies the consensus is that feature quality and evaluation discipline, "
        "rather than the model family, determine reported performance (Sahingoz et al., 2019; "
        "Le et al., 2018; Jain & Gupta, 2022). A model that is evaluated on a random split, or on "
        "negatives that are structurally unlike the positives, will report an accuracy that does "
        "not survive deployment.")
    p.h2("2.6 Communicating a Detection Result")
    p.para(
        "A verdict that cannot be explained is difficult to act on and easy to ignore. Work on "
        "interpretable machine learning argues that explanations should state which inputs drove a "
        "prediction, not merely how confident the model is (Ribeiro et al., 2016; Lundberg & Lee, "
        "2017). Security warnings face a further problem: users habituate to warnings that are "
        "frequent, vague or wrong, so a tool that flags ordinary sites quickly loses credibility. "
        "For a phishing detector, precision therefore matters as much as recall, and the false "
        "positive rate belongs in the evaluation rather than in a footnote. Presenting the "
        "specific characteristics that raised a score, in language a non-specialist can follow, "
        "is a practical application of both findings.")

    p.h2("2.7 Concept Map")
    p.para(
        "The concept map below relates the variables of the study. The independent variables are the URL "
        "characteristics and the quality of the labelled data. They feed a three-stage system: "
        "feature extraction, classification and explanation. The dependent variables are "
        "classification accuracy, false-positive rate, and the clarity of the explanation, which "
        "together determine whether a user trusts and acts on a verdict. Phishing tactics evolving "
        "over time moderate the relationship, which is why the model is evaluated on held-out "
        "domains rather than on a random split.")
    p.figure(os.path.join(FIG, "fig_concept_map.png"),
             "Concept map relating the study's independent and dependent variables", width_cm=15.5)

    p.h2("2.8 Summary and Research Gap")
    p.para(
        "The literature establishes that URL-level machine learning works, that blocklists are "
        "structurally reactive, and that both feature quality and split discipline determine how "
        "much of a reported accuracy is real. It also shows what is usually missing. Published "
        "detectors tend to report accuracy without a false-positive rate, to evaluate on splits "
        "that leak near-duplicate URLs, to depend on paid or network-bound data, and to stop "
        "before the point at which a user has to understand the output. The gap this project "
        "addresses, through the system named Nyavu, is a reproducible, zero-cost detector that is "
        "evaluated on domain-disjoint "
        "data, reports the false-positive rate as a first-class result, explains each verdict, "
        "and is usable from a phone. The project does not claim to outperform the published "
        "models; it demonstrates that a small, transparent model can be built, evaluated and "
        "deployed honestly within an undergraduate budget.")

    if include_references:
        p.h1("REFERENCES", page_break=True)
        p.references(REFERENCES)


def main():
    p = Paper()
    body(p)
    p.page_numbers()
    path = os.path.join(OUT, "Chapter_Two_Literature_Review.docx")
    p.save(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
