"""
Layer 2 detection: live-inventory reconciliation.

`terraform plan` only diffs resources already present in Terraform state.
A resource created entirely outside Terraform (e.g. a debug firewall rule
that was never `terraform import`-ed) never appears in the plan at all --
Section "Detection" of this project's writeup documents this as a real
limitation discovered empirically (scenario net-02).

This script closes that gap for the network category by listing the live
firewall rules on the project's custom VPC and diffing that list against
`terraform state list`, flagging any live resource with no Terraform
address as an orphan / unmanaged resource.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TF = "terraform"  # installed globally via winget; on PATH in any shell
INFRA_DIR = ROOT / "infra"


def run(cmd: str, cwd=None) -> str:
    proc = subprocess.run(cmd, shell=True, cwd=str(cwd) if cwd else None,
                           capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"WARN: {cmd} -> rc={proc.returncode} {proc.stderr[-300:]}", file=sys.stderr)
    return proc.stdout


def check_iam_orphans():
    """Layer 2, identity category: Terraform's google_project_iam_member only
    tracks the exact (project, role, member) triple it declares. An
    out-of-band `add-iam-policy-binding` for a DIFFERENT role on the same
    member -- or any binding on the bucket, which Terraform does not manage
    IAM for at all -- is invisible to `terraform plan`. Reconcile against the
    live IAM policy directly instead."""
    app_sa = "serviceAccount:p14-app-sa@p14-drift-ranking.iam.gserviceaccount.com"
    declared_roles = {"roles/storage.objectViewer"}

    proj_policy = json.loads(run("gcloud projects get-iam-policy p14-drift-ranking --format=json") or "{}")
    live_roles_for_sa = {
        b["role"] for b in proj_policy.get("bindings", []) if app_sa in b.get("members", [])
    }
    extra_project_roles = live_roles_for_sa - declared_roles

    bucket_policy = json.loads(
        run("gcloud storage buckets get-iam-policy gs://p14-drift-ranking-p14-baseline-bucket --format=json") or "{}"
    )
    public_members = set()
    for b in bucket_policy.get("bindings", []):
        for m in b.get("members", []):
            if m in ("allUsers", "allAuthenticatedUsers"):
                public_members.add((b["role"], m))

    return {
        "app_sa_extra_project_roles_untracked_by_terraform": sorted(extra_project_roles),
        "bucket_public_bindings_untracked_by_terraform": sorted(str(x) for x in public_members),
    }


def main():
    tf_state = run(f'"{TF}" state list', cwd=INFRA_DIR).strip().splitlines()
    managed_firewalls = {
        line.split(".")[-1] for line in tf_state if line.startswith("google_compute_firewall")
    }
    # Map terraform resource names to actual GCP resource names via state show.
    managed_live_names = set()
    for addr in [l for l in tf_state if l.startswith("google_compute_firewall")]:
        out = run(f'"{TF}" state show -no-color {addr}', cwd=INFRA_DIR)
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("name") and "=" in line:
                managed_live_names.add(line.split("=", 1)[1].strip().strip('"'))
                break

    live = run('gcloud compute firewall-rules list --filter="network:p14-baseline-net" --format="value(name)"')
    live_names = {n.strip() for n in live.splitlines() if n.strip()}

    orphans = live_names - managed_live_names
    missing = managed_live_names - live_names

    iam = check_iam_orphans()

    result = {
        "managed_in_terraform_state": sorted(managed_live_names),
        "live_on_vpc": sorted(live_names),
        "orphan_resources_untracked_by_terraform": sorted(orphans),
        "resources_missing_from_live_but_in_state": sorted(missing),
        **iam,
    }
    print(json.dumps(result, indent=2))
    out_path = ROOT / "corpus" / "raw" / "inventory_check.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
