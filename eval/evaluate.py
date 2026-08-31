"""
Evaluation: precision@k and mean-rank-of-most-dangerous-item for each
ranking method, against the unranked and random baselines.

Random baseline is computed analytically (expectation under a uniformly
random permutation, hypergeometric) rather than from a single shuffle,
since a single random draw is exactly the kind of one-run noise this
project's methodology elsewhere insists on avoiding.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "corpus"
EVAL_DIR = ROOT / "eval"


def precision_at_k(order: list, k: int, is_positive) -> float:
    top_k = order[:k]
    hits = sum(1 for item in top_k if is_positive(item))
    return hits / k


def mean_rank_of(order: list, predicate) -> float:
    ranks = [i + 1 for i, item in enumerate(order) if predicate(item)]
    return sum(ranks) / len(ranks) if ranks else float("nan")


def expected_precision_at_k_random(n_total: int, n_positive: int, k: int) -> float:
    # E[hits in top-k under random order] = k * n_positive / n_total, so
    # E[precision@k] = E[hits]/k = n_positive / n_total (constant in k).
    return n_positive / n_total


def expected_mean_rank_random(n_total: int) -> float:
    # Expected rank of a uniformly random single item among n is (n+1)/2.
    return (n_total + 1) / 2


def main():
    rows = json.loads((CORPUS_DIR / "features_scored.json").read_text())
    n = len(rows)
    n_dangerous = sum(1 for r in rows if r["impact"] == "dangerous")
    n_severity5 = sum(1 for r in rows if r["severity"] == 5)

    is_dangerous = lambda r: r["impact"] == "dangerous"
    is_top_severity = lambda r: r["severity"] == 5

    methods = {
        "unranked_corpus_order": lambda rows: list(rows),  # order items were detected in
        "rule_based": lambda rows: sorted(rows, key=lambda r: -r["score_rule"]),
        "logreg_loocv": lambda rows: sorted(rows, key=lambda r: -r["score_logreg_loocv"]),
        "decision_tree_loocv": lambda rows: sorted(rows, key=lambda r: -r["score_tree_loocv"]),
    }

    results = {"n_total": n, "n_dangerous": n_dangerous, "n_harmless": n - n_dangerous,
               "n_severity_5": n_severity5}

    for name, order_fn in methods.items():
        order = order_fn(rows)
        results[name] = {
            "precision_at_5": round(precision_at_k(order, 5, is_dangerous), 3),
            "precision_at_10": round(precision_at_k(order, 10, is_dangerous), 3),
            "mean_rank_of_severity5_items": round(mean_rank_of(order, is_top_severity), 3),
            "ranked_ids_desc": [r["id"] for r in order],
        }

    results["random_baseline_expected"] = {
        "precision_at_5": round(expected_precision_at_k_random(n, n_dangerous, 5), 3),
        "precision_at_10": round(expected_precision_at_k_random(n, n_dangerous, 10), 3),
        "mean_rank_of_severity5_items": round(expected_mean_rank_random(n), 3),
    }

    out_path = EVAL_DIR / "results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Markdown summary table for the reports.
    lines = [
        "| Method | Precision@5 | Precision@10 | Mean rank of severity-5 items |",
        "|---|---|---|---|",
    ]
    for name in ["random_baseline_expected", "unranked_corpus_order", "rule_based",
                 "logreg_loocv", "decision_tree_loocv"]:
        r = results[name]
        lines.append(f"| {name} | {r['precision_at_5']} | {r['precision_at_10']} | {r['mean_rank_of_severity5_items']} |")
    (EVAL_DIR / "results_table.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(results, indent=2))
    print("\n" + "\n".join(lines))


if __name__ == "__main__":
    main()
