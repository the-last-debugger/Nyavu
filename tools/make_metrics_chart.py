"""
The classifier comparison chart for the report.

The figure it replaces had a y-axis running from 86 to 100 while every value sits between 68
and 78, so the bars were clipped out of sight and the chart was blank. This one reads the
numbers from the artefact rather than from memory, and draws bars from zero so the comparison
is honest about how much of the scale each metric occupies.

Run: python tools/make_metrics_chart.py
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS = os.path.join(ROOT, "ml", "artifacts", "metrics.json")
OUT = os.path.join(ROOT, "docs", "figures", "model-comparison.png")

ORDER = ["Logistic Regression", "Random Forest", "Linear SVM"]
METRICS_SHOWN = [("accuracy", "Accuracy"), ("precision", "Precision"),
                 ("recall", "Recall"), ("f1", "F1")]


def build():
    data = json.load(open(METRICS, encoding="utf-8"))
    results = data["results"]

    labels = [label for _, label in METRICS_SHOWN]
    positions = range(len(labels))
    width = 0.26

    figure, axes = plt.subplots(figsize=(11, 5.2), dpi=132)
    for offset, name in enumerate(ORDER):
        values = [results[name][key] * 100 for key, _ in METRICS_SHOWN]
        bars = axes.bar([p + (offset - 1) * width for p in positions], values, width,
                        label=name)
        axes.bar_label(bars, fmt="%.1f", padding=2, fontsize=8)

    axes.set_xticks(list(positions))
    axes.set_xticklabels(labels)
    axes.set_ylabel("Percent")
    axes.set_ylim(0, 100)
    axes.set_title("Accuracy, precision, recall and F1 on the domain-disjoint hold-out set")
    axes.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.0))
    axes.grid(axis="y", alpha=0.25)
    axes.set_axisbelow(True)
    figure.tight_layout()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    figure.savefig(OUT)
    print("wrote", OUT, f"{len(ORDER)} classifiers, {len(METRICS_SHOWN)} metrics")


if __name__ == "__main__":
    build()
