"""Static architecture diagram (boxes + arrows) for embedding in Word docs,
since Mermaid does not render outside Notion/Markdown viewers."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "docs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(9, 7))
ax.set_xlim(0, 10)
ax.set_ylim(0, 12)
ax.axis("off")


def box(x, y, w, h, text, color="#e7f5ff", edge="#1971c2", fontsize=9, bold=False):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.12",
                        linewidth=1.4, edgecolor=edge, facecolor=color)
    ax.add_patch(b)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            fontweight="bold" if bold else "normal", wrap=True)
    return (x + w / 2, y, x + w / 2, y + h)


def arrow(p_from, p_to, label=None):
    a = FancyArrowPatch(p_from, p_to, arrowstyle="-|>", mutation_scale=14,
                         linewidth=1.2, color="#495057")
    ax.add_patch(a)
    if label:
        mx, my = (p_from[0] + p_to[0]) / 2, (p_from[1] + p_to[1]) / 2
        ax.text(mx + 0.25, my, label, fontsize=7.5, style="italic", color="#495057")


# Row 1: Terraform + GCP
box(0.5, 10, 3, 1.4, "Terraform\n(infra/main.tf)", color="#fff3bf", edge="#e8590c", bold=True)
box(4.2, 10, 5.3, 1.4,
    "GCP project: p14-drift-ranking (us-central1)\nCompute · Network · Storage · Identity\n(all Always-Free tier)",
    color="#d3f9d8", edge="#2f9e44", bold=True)
ax.annotate("", xy=(4.2, 10.7), xytext=(3.5, 10.7),
            arrowprops=dict(arrowstyle="-|>", color="#495057", lw=1.2))

# Row 2: corpus + injector
box(0.5, 8, 3, 1.3, "corpus/scenarios.yaml\n16 labelled drift scenarios", color="#eef2ff", edge="#4263eb")
box(4.2, 8, 3.2, 1.3, "scripts/run_experiment.py\n(drift injector, gcloud)", color="#fff0f6", edge="#c2255c", bold=True)
ax.annotate("", xy=(4.2, 8.65), xytext=(3.5, 8.65), arrowprops=dict(arrowstyle="-|>", color="#495057", lw=1.2))
ax.annotate("", xy=(6, 10), xytext=(6, 9.3), arrowprops=dict(arrowstyle="<|-", color="#495057", lw=1.2))
ax.text(6.2, 9.5, "out-of-band\ngcloud command", fontsize=7.5, style="italic", color="#495057")

# Row 3: two detection layers
box(0.5, 6, 4.2, 1.3, "Layer 1: terraform plan -json\n(state-diff detection)", color="#fff3bf", edge="#e8590c", bold=True)
box(5.2, 6, 4.3, 1.3, "Layer 2: scripts/inventory_check.py\n(live-inventory reconciliation)", color="#d3f9d8", edge="#2f9e44", bold=True)
ax.annotate("", xy=(2.6, 8), xytext=(2.6, 7.3), arrowprops=dict(arrowstyle="-|>", color="#495057", lw=1.2))
ax.annotate("", xy=(6.5, 8), xytext=(6.5, 7.3), arrowprops=dict(arrowstyle="-|>", color="#495057", lw=1.2))

# Row 4: features
box(2.5, 4.3, 5, 1.2, "scripts/extract_features.py\n(danger features from plan diff + Layer-2 findings)",
    color="#eef2ff", edge="#4263eb", bold=True)
ax.annotate("", xy=(3.5, 6), xytext=(3.5, 5.5), arrowprops=dict(arrowstyle="-|>", color="#495057", lw=1.2))
ax.annotate("", xy=(6.5, 6), xytext=(6.5, 5.5), arrowprops=dict(arrowstyle="-|>", color="#495057", lw=1.2))

# Row 5: ranking methods
box(0.3, 2.5, 2.9, 1.2, "Rule-based\nseverity scorer", color="#d3f9d8", edge="#2f9e44", bold=True)
box(3.5, 2.5, 2.9, 1.2, "Logistic\nregression (LOOCV)", color="#ffe8cc", edge="#e8590c")
box(6.7, 2.5, 2.9, 1.2, "Decision tree\n(LOOCV)", color="#e7f5ff", edge="#1971c2")
for cx in [1.75, 4.95, 8.15]:
    ax.annotate("", xy=(cx, 4.3), xytext=(5, 3.7), arrowprops=dict(arrowstyle="-", color="#495057", lw=0.001))
ax.annotate("", xy=(1.75, 3.7), xytext=(5, 4.3), arrowprops=dict(arrowstyle="-|>", color="#495057", lw=1))
ax.annotate("", xy=(4.95, 3.7), xytext=(5, 4.3), arrowprops=dict(arrowstyle="-|>", color="#495057", lw=1))
ax.annotate("", xy=(8.15, 3.7), xytext=(5, 4.3), arrowprops=dict(arrowstyle="-|>", color="#495057", lw=1))

# Row 6: evaluation
box(1.5, 0.4, 7, 1.3,
    "eval/evaluate.py + eval/bootstrap_ci.py\nprecision@k, mean rank, vs unranked / random baselines (95% CI)",
    color="#fff0f6", edge="#c2255c", bold=True)
for cx in [1.75, 4.95, 8.15]:
    ax.annotate("", xy=(5, 1.7), xytext=(cx, 2.5), arrowprops=dict(arrowstyle="-|>", color="#495057", lw=1))

ax.set_title("Figure A0 — P14 System Architecture", fontsize=13, fontweight="bold", pad=14)
fig.tight_layout()
fig.savefig(FIG_DIR / "architecture.png", dpi=180)
print("Wrote", FIG_DIR / "architecture.png")
