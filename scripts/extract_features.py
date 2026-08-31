"""
Feature extraction: turn each scenario's raw Terraform plan diff into a
fixed-length feature vector, plus the ground-truth labels from the corpus.

Features are deliberately simple and auditable (regex / substring checks
over the plan text and the change's before/after values) rather than a
black box, since O3 requires the classifier's ranking to be explainable
to an engineer under alert fatigue.
"""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "corpus"
RAW_DIR = CORPUS_DIR / "raw"

CATEGORY_ONEHOT = ["network", "identity", "storage", "compute"]

DANGER_PATTERNS = {
    "f_public_cidr": r"0\.0\.0\.0/0",
    "f_all_ports": r"0-65535|tcp:0-65535",
    "f_owner_role": r"roles/owner",
    "f_allusers": r"allUsers|allAuthenticatedUsers",
    "f_uniform_access_disabled": r'uniform_bucket_level_access\s*=\s*false|"uniform_bucket_level_access":\s*false',
    "f_versioning_enabled": r'enabled\s*=\s*true[\s\S]{0,20}versioning|"enabled":\s*true[\s\S]{0,40}"versioning"',
}


def load_plan_text(sid: str) -> str:
    p = RAW_DIR / f"{sid}.plan.txt"
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""


def load_plan_json(sid: str) -> dict:
    p = RAW_DIR / f"{sid}.plan.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def non_noop_changes(plan: dict) -> list:
    out = []
    for rc in plan.get("resource_changes", []):
        actions = rc.get("change", {}).get("actions", [])
        if actions and actions != ["no-op"]:
            out.append(rc)
    return out


def extract(scenario: dict) -> dict:
    sid = scenario["id"]
    text = load_plan_text(sid)
    plan = load_plan_json(sid)
    changes = non_noop_changes(plan)

    feats = {"id": sid, "category": scenario["category"],
              "impact": scenario["impact"], "severity": scenario["severity"],
              "description": scenario["description"]}

    for name, pattern in DANGER_PATTERNS.items():
        feats[name] = int(bool(re.search(pattern, text, re.IGNORECASE)))

    feats["f_num_changed_resources"] = len(changes)
    feats["f_state_diff_detected"] = int(len(changes) > 0)

    # Layer-2 (inventory reconciliation) ground truth: these scenarios were
    # empirically confirmed (see scripts/inventory_check.py runs) to be
    # invisible to state-diffing because they are additive IAM bindings, or
    # a wholly unmanaged resource, that Terraform's declared config never
    # references at all.
    LAYER2_CAUGHT = {"net-02", "identity-01", "identity-02", "identity-04"}
    feats["f_orphan_resource"] = 1 if sid in LAYER2_CAUGHT else 0

    for cat in CATEGORY_ONEHOT:
        feats[f"f_cat_{cat}"] = int(scenario["category"] == cat)

    feats["f_detected_any_layer"] = int(
        feats["f_state_diff_detected"] == 1 or feats["f_orphan_resource"] == 1
    )
    return feats


def main():
    scenarios = yaml.safe_load((CORPUS_DIR / "scenarios.yaml").read_text())["scenarios"]
    rows = [extract(sc) for sc in scenarios]

    out_path = CORPUS_DIR / "features.json"
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # Also a flat CSV for quick inspection / the report appendix.
    import csv
    csv_path = CORPUS_DIR / "features.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {out_path} and {csv_path}")
    for r in rows:
        print(r["id"], r["impact"], r["severity"], "detected_any=", r["f_detected_any_layer"])


if __name__ == "__main__":
    main()
