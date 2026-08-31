"""Precision@k comparison chart with 95% CI error bars, for the report."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = ROOT / "eval"

data = json.loads((EVAL_DIR / "bootstrap_results.json").read_text())
budgets = [3, 5, 10]
methods = ["random_order_bootstrap", "rule_based", "logreg_loocv", "decision_tree_loocv"]
labels = ["Random order", "Rule-based scorer", "Logistic regression (LOOCV)", "Decision tree (LOOCV)"]
colors = ["#9aa5b1", "#2f9e44", "#e8590c", "#1971c2"]

fig, ax = plt.subplots(figsize=(8, 5))
x = np.arange(len(budgets))
width = 0.2

for i, (m, lab, col) in enumerate(zip(methods, labels, colors)):
    means = [data[m][f"precision_at_{k}"]["mean"] for k in budgets]
    lows = [data[m][f"precision_at_{k}"]["mean"] - data[m][f"precision_at_{k}"]["ci95_low"] for k in budgets]
    highs = [data[m][f"precision_at_{k}"]["ci95_high"] - data[m][f"precision_at_{k}"]["mean"] for k in budgets]
    ax.bar(x + (i - 1.5) * width, means, width, yerr=[lows, highs], capsize=3,
           label=lab, color=col)

ax.set_xticks(x)
ax.set_xticklabels([f"top-{k}\n(alert budget)" for k in budgets])
ax.set_ylabel("Precision@k (fraction of top-k that are truly dangerous)")
ax.set_title("Drift-ranking precision at fixed alert budgets\n(bootstrap 95% CI, n=16 corpus, 2000 resamples)")
ax.legend(loc="upper right", fontsize=8)
ax.set_ylim(0, 1.05)
ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8)
fig.tight_layout()
fig.savefig(EVAL_DIR / "precision_at_k.png", dpi=150)
print("Wrote", EVAL_DIR / "precision_at_k.png")
