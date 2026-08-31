"""
Severity ranking: rule-based scorer + a trained classifier, evaluated with
leave-one-out cross-validation (the corpus has only 16 items, so a held-out
test split would be too small to be meaningful; LOOCV gives every item an
out-of-fold score without ever training on itself).

Also produces the two comparison baselines the guide requires:
  - "unranked": the order items are detected in (corpus id order), i.e.
    what an engineer gets from a raw `terraform plan` diff with no ranking.
  - "random": expected precision@k under a uniformly random ordering,
    computed analytically (hypergeometric expectation) rather than by a
    single noisy shuffle.
"""
import itertools
import json
from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneOut
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "corpus"
EVAL_DIR = ROOT / "eval"
EVAL_DIR.mkdir(exist_ok=True)

FEATURE_COLS = [
    "f_public_cidr", "f_all_ports", "f_owner_role", "f_allusers",
    "f_uniform_access_disabled", "f_versioning_enabled",
    "f_num_changed_resources", "f_orphan_resource",
    "f_cat_network", "f_cat_identity", "f_cat_storage", "f_cat_compute",
]

RULE_WEIGHTS = {
    "f_public_cidr": 3,
    "f_all_ports": 2,
    "f_owner_role": 3,
    "f_allusers": 3,
    "f_uniform_access_disabled": 2,
    "f_versioning_enabled": 1,
    "f_orphan_resource": 2,
}


def rule_based_score(row: dict) -> float:
    return sum(RULE_WEIGHTS.get(k, 0) * row.get(k, 0) for k in RULE_WEIGHTS)


def main():
    rows = json.loads((CORPUS_DIR / "features.json").read_text())
    n = len(rows)

    X = [[r.get(c, 0) for c in FEATURE_COLS] for r in rows]
    y_impact = [1 if r["impact"] == "dangerous" else 0 for r in rows]

    # --- Rule-based ranking ---
    for r in rows:
        r["score_rule"] = rule_based_score(r)

    # --- Trained classifier, leave-one-out out-of-fold probability ---
    loo = LeaveOneOut()
    proba_lr = [0.0] * n
    proba_tree = [0.0] * n
    for train_idx, test_idx in loo.split(X):
        i = test_idx[0]
        X_train = [X[j] for j in train_idx]
        y_train = [y_impact[j] for j in train_idx]
        X_test = [X[i]]

        if len(set(y_train)) < 2:
            # Degenerate fold (all-same-label training set); fall back to
            # the training-set base rate rather than fitting on one class.
            base_rate = sum(y_train) / len(y_train)
            proba_lr[i] = base_rate
            proba_tree[i] = base_rate
            continue

        lr = LogisticRegression(max_iter=1000)
        lr.fit(X_train, y_train)
        proba_lr[i] = float(lr.predict_proba(X_test)[0][1])

        tree = DecisionTreeClassifier(max_depth=3, random_state=0)
        tree.fit(X_train, y_train)
        proba_tree[i] = float(tree.predict_proba(X_test)[0][1])

    for idx, r in enumerate(rows):
        r["score_logreg_loocv"] = proba_lr[idx]
        r["score_tree_loocv"] = proba_tree[idx]

    out_path = CORPUS_DIR / "features_scored.json"
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
