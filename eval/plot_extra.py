"""Additional figures for the reports: corpus composition, detection
coverage (Layer 1 vs combined), and mean-rank-of-severity-5 comparison."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "corpus"
EVAL_DIR = ROOT / "eval"
FIG_DIR = ROOT / "docs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

# --- Figure: corpus composition ---
scenarios = yaml.safe_load((CORPUS_DIR / "scenarios.yaml").read_text())["scenarios"]
categories = ["network", "identity", "storage", "compute"]
dangerous_counts = [sum(1 for s in scenarios if s["category"] == c and s["impact"] == "dangerous") for c in categories]
harmless_counts = [sum(1 for s in scenarios if s["category"] == c and s["impact"] == "harmless") for c in categories]

fig, ax = plt.subplots(figsize=(7, 4.2))
x = np.arange(len(categories))
width = 0.35
ax.bar(x - width / 2, dangerous_counts, width, label="Dangerous", color="#c92a2a")
ax.bar(x + width / 2, harmless_counts, width, label="Harmless", color="#2f9e44")
ax.set_xticks(x)
ax.set_xticklabels([c.capitalize() for c in categories])
ax.set_ylabel("Number of scenarios")
ax.set_title("Figure A1 — Drift Corpus Composition (16 scenarios, 4 categories)")
ax.set_ylim(0, 3)
for i, (d, h) in enumerate(zip(dangerous_counts, harmless_counts)):
    ax.text(i - width / 2, d + 0.05, str(d), ha="center", fontsize=9)
    ax.text(i + width / 2, h + 0.05, str(h), ha="center", fontsize=9)
ax.legend()
fig.tight_layout()
fig.savefig(FIG_DIR / "corpus_composition.png", dpi=180)
plt.close(fig)

# --- Figure: detection coverage ---
fig, ax = plt.subplots(figsize=(7, 4.2))
labels = ["Layer 1 only\n(terraform plan)", "Layer 1 + Layer 2\n(+ inventory reconciliation)"]
values = [12, 16]
colors = ["#e8590c", "#2f9e44"]
bars = ax.bar(labels, values, color=colors, width=0.5)
ax.set_ylim(0, 18)
ax.set_ylabel("Scenarios detected (out of 16)")
ax.set_title("Figure A2 — Detection Completeness by Layer")
ax.axhline(16, color="gray", linestyle="--", linewidth=0.8)
for bar, v in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width() / 2, v + 0.3, f"{v}/16 ({v/16*100:.0f}%)",
            ha="center", fontsize=10, fontweight="bold")
fig.tight_layout()
fig.savefig(FIG_DIR / "detection_coverage.png", dpi=180)
plt.close(fig)

# --- Figure: mean rank of severity-5 items ---
results = json.loads((EVAL_DIR / "results.json").read_text())
methods = ["random_baseline_expected", "unranked_corpus_order", "rule_based", "logreg_loocv", "decision_tree_loocv"]
labels2 = ["Random", "Unranked", "Rule-based", "LogReg\n(LOOCV)", "Decision Tree\n(LOOCV)"]
mean_ranks = [results[m]["mean_rank_of_severity5_items"] for m in methods]
colors2 = ["#9aa5b1", "#495057", "#2f9e44", "#e8590c", "#1971c2"]

fig, ax = plt.subplots(figsize=(7.5, 4.2))
bars = ax.bar(labels2, mean_ranks, color=colors2)
ax.set_ylabel("Mean rank of the 3 severity-5 items (lower = better)")
ax.set_title("Figure A3 — Mean Rank of Most-Dangerous Items by Ranking Method")
ax.invert_yaxis()
for bar, v in zip(bars, mean_ranks):
    ax.text(bar.get_x() + bar.get_width() / 2, v + 0.3, f"{v:.2f}", ha="center", fontsize=9)
fig.tight_layout()
fig.savefig(FIG_DIR / "mean_rank_comparison.png", dpi=180)
plt.close(fig)

print("Wrote:")
for f in ["corpus_composition.png", "detection_coverage.png", "mean_rank_comparison.png"]:
    print(" -", FIG_DIR / f)
