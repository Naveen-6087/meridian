"""
Drift experiment runner for P14.

For each scenario in corpus/scenarios.yaml:
  1. Run the `inject` shell commands against the live GCP project (real,
     out-of-band changes -- not through Terraform).
  2. Capture `terraform plan -json` from infra/ -- this IS the drift
     detection step: Terraform refreshes live state and reports the diff
     needed to bring reality back to the declared config.
  3. Save the raw plan (json + human-readable) to corpus/raw/.
  4. Run the `revert` shell commands, then `terraform apply -auto-approve`
     to reconcile any residual drift before the next scenario.

This produces one ground-truth-labelled drift detection per scenario,
with the real Terraform plan diff as the raw evidence.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
INFRA_DIR = ROOT / "infra"
CORPUS_DIR = ROOT / "corpus"
RAW_DIR = CORPUS_DIR / "raw"
TF = "terraform"  # installed globally via winget; on PATH in any shell

RAW_DIR.mkdir(parents=True, exist_ok=True)


def run(cmd: str, cwd: Path = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd, shell=True, cwd=str(cwd) if cwd else None,
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def terraform_plan_json(plan_json_path: Path, plan_text_path: Path) -> dict:
    rc, out, err = run(f'"{TF}" plan -no-color -out=drift.tfplan', cwd=INFRA_DIR)
    plan_text_path.write_text(out + "\n" + err, encoding="utf-8")
    rc2, out2, err2 = run(f'"{TF}" show -json drift.tfplan', cwd=INFRA_DIR)
    if rc2 != 0:
        plan_json_path.write_text(json.dumps({"error": err2}), encoding="utf-8")
        return {"error": err2}
    plan_json_path.write_text(out2, encoding="utf-8")
    return json.loads(out2)


def main():
    scenarios = yaml.safe_load((CORPUS_DIR / "scenarios.yaml").read_text())["scenarios"]
    log = []

    for sc in scenarios:
        sid = sc["id"]
        print(f"\n=== Scenario {sid}: {sc['description']} ===", flush=True)
        entry = {"id": sid, "category": sc["category"], "impact": sc["impact"],
                  "severity": sc["severity"], "description": sc["description"]}

        t0 = time.time()
        inject_results = []
        for cmd in sc["inject"]:
            rc, out, err = run(cmd)
            inject_results.append({"cmd": cmd, "rc": rc, "stdout": out[-2000:], "stderr": err[-2000:]})
            print(f"  inject rc={rc}: {cmd}")
        entry["inject_results"] = inject_results
        entry["inject_seconds"] = round(time.time() - t0, 2)

        # Detection: Terraform plan diff IS the drift evidence.
        plan_json_path = RAW_DIR / f"{sid}.plan.json"
        plan_text_path = RAW_DIR / f"{sid}.plan.txt"
        t1 = time.time()
        plan = terraform_plan_json(plan_json_path, plan_text_path)
        entry["detect_seconds"] = round(time.time() - t1, 2)
        entry["resource_changes"] = len(plan.get("resource_changes", []))
        entry["drift_detected"] = entry["resource_changes"] > 0

        print(f"  detected {entry['resource_changes']} changed resource(s) in {entry['detect_seconds']}s")

        # Revert.
        revert_results = []
        for cmd in sc["revert"]:
            rc, out, err = run(cmd)
            revert_results.append({"cmd": cmd, "rc": rc, "stdout": out[-1000:], "stderr": err[-1000:]})
            print(f"  revert rc={rc}: {cmd}")
        entry["revert_results"] = revert_results

        # Reconcile any residual drift via terraform apply before next scenario.
        rc, out, err = run(f'"{TF}" apply -auto-approve', cwd=INFRA_DIR)
        entry["reconcile_rc"] = rc
        if rc != 0:
            print(f"  WARNING: reconcile apply failed for {sid}: {err[-500:]}", file=sys.stderr)

        log.append(entry)

    out_path = CORPUS_DIR / "experiment_log.json"
    out_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
