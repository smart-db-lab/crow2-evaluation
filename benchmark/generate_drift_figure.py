"""Regenerates fig_temporal_drift.png from results_aug12_baseline.csv and
results_nov15.csv -- the 95-day unmodified re-run of the original benchmark.
Not derived from results.csv (which holds the benchmark-construction numbers
only); this script is the one place the Aug-vs-Nov comparison is computed.
"""
import csv, os
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = os.path.dirname(__file__)

CAT_LABELS = {
    "biomedical_search": "Biomedical\nsearch",
    "clinical": "Clinical\nregistries",
    "protein": "Protein\nknowledge-\nbases",
    "genomic": "Genomic\nrepositories",
    "disease": "Disease\ndatabases",
}
CAT_ORDER = ["biomedical_search", "clinical", "protein", "genomic", "disease"]


def category_recall(path):
    rows = list(csv.DictReader(open(path)))
    tp = defaultdict(int)
    fn = defaultdict(int)
    for r in rows:
        tp[r["category"]] += int(r["true_positive"])
        fn[r["category"]] += int(r["false_negative"])
    return {c: 100 * tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) else 0 for c in CAT_ORDER}


def main():
    aug = category_recall(os.path.join(BASE, "results_aug12_baseline.csv"))
    nov = category_recall(os.path.join(BASE, "results_nov15.csv"))

    cats = [CAT_LABELS[c] for c in CAT_ORDER]
    aug_recall = [aug[c] for c in CAT_ORDER]
    nov_recall = [nov[c] for c in CAT_ORDER]

    x = np.arange(len(cats))
    w = 0.34
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    b1 = ax.bar(x - w / 2, aug_recall, w, label="Benchmark construction", color="#2b6cb0")
    b2 = ax.bar(x + w / 2, nov_recall, w, label="Unmodified re-run, 95 days later", color="#ed8936")

    for b, v in zip(b1, aug_recall):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}", ha="center", fontsize=8.5)
    for b, v in zip(b2, nov_recall):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}", ha="center", fontsize=8.5,
                 color="#c05621" if v < 50 else "black", fontweight="bold" if v < 50 else "normal")

    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=9.3)
    ax.set_ylabel("Recall (%)")
    ax.set_ylim(0, 112)
    ax.legend(loc="lower left", fontsize=8.5, framealpha=0.9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.annotate("17/20 NCBI Gene queries\nreturned a reCAPTCHA\nchallenge page, not data",
                xy=(3 + w / 2, nov["genomic"]), xytext=(3.15, 45),
                fontsize=8, ha="left", color="#c05621",
                arrowprops=dict(arrowstyle="->", color="#c05621", lw=1.2))
    ax.set_title("Same unchanged wrappers, 95 days apart", fontsize=11)
    plt.tight_layout()
    out = os.path.join(BASE, "fig_temporal_drift.png")
    plt.savefig(out, dpi=300, facecolor="white")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
