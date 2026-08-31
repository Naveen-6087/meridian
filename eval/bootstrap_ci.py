"""
Statistical soundness for Review 3: since detection/ranking on a fixed
16-item labelled corpus is deterministic (unlike a stochastic load-test
measurement), repeating the *identical* experiment three times would not
produce meaningful variance -- it would just reproduce the same numbers.
The statistically appropriate technique here is bootstrap resampling of the
labelled corpus itself: draw 16 items with replacement, recompute the
ranking and precision@k on the resampled set, repeat 2000 times, and report
the mean and a percentile 95% confidence interval. This also serves as the
project's three "workloads" for Review 3 -- three alert-budget operating
points (top-3 / top-5 / top-10), matching the SOC alert-fatigue framing from
the literature review (an analyst reviews a fixed number of items per day).
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "corpus"
EVAL_DIR = ROOT / "eval"

N_BOOTSTRAP = 2000
BUDGETS = [3, 5, 10]

RULE_WEIGHTS = {
    "f_public_cidr": 3, "f_all_ports": 2, "f_owner_role": 3, "f_allusers": 3,
    "f_uniform_access_disabled": 2, "f_versioning_enabled": 1, "f_orphan_resource": 2,
}


def rule_score(r):
    return sum(RULE_WEIGHTS.get(k, 0) * r.get(k, 0) for k in RULE_WEIGHTS)


def precision_at_k(order, k):
    top = order[:k]
    return sum(1 for r in top if r["impact"] == "dangerous") / k


def percentile(values, p):
    values = sorted(values)
    idx = int(round(p / 100 * (len(values) - 1)))
    return values[idx]


def main():
    rows = json.loads((CORPUS_DIR / "features_scored.json").read_text())
    n = len(rows)
    rng = random.Random(42)

    # NOTE: "unranked" under bootstrap resampling reduces to a random-order
    # estimate, because resampling with replacement destroys the original
    # corpus's natural detection order. The true fixed-order unranked
    # baseline (point estimate, no resampling) is reported separately in
    # eval/results.json / results_table.md.
    methods = {
        "random_order_bootstrap": lambda sample: list(sample),
        "rule_based": lambda sample: sorted(sample, key=lambda r: -rule_score(r)),
        "logreg_loocv": lambda sample: sorted(sample, key=lambda r: -r["score_logreg_loocv"]),
        "decision_tree_loocv": lambda sample: sorted(sample, key=lambda r: -r["score_tree_loocv"]),
    }

    results = {}
    for method_name, order_fn in methods.items():
        results[method_name] = {}
        for k in BUDGETS:
            samples = []
            for _ in range(N_BOOTSTRAP):
                sample = [rng.choice(rows) for _ in range(n)]
                order = order_fn(sample)
                samples.append(precision_at_k(order, k))
            mean_val = sum(samples) / len(samples)
            lo = percentile(samples, 2.5)
            hi = percentile(samples, 97.5)
            results[method_name][f"precision_at_{k}"] = {
                "mean": round(mean_val, 3),
                "ci95_low": round(lo, 3),
                "ci95_high": round(hi, 3),
            }

    out_path = EVAL_DIR / "bootstrap_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    lines = ["| Method | Budget | Mean precision@k | 95% CI |", "|---|---|---|---|"]
    for method_name in methods:
        for k in BUDGETS:
            r = results[method_name][f"precision_at_{k}"]
            lines.append(f"| {method_name} | top-{k} | {r['mean']} | [{r['ci95_low']}, {r['ci95_high']}] |")
    (EVAL_DIR / "bootstrap_table.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(results, indent=2))
    print("\n" + "\n".join(lines))


if __name__ == "__main__":
    main()
