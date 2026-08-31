# P14 — Risk-Ranked Detection and Remediation of Configuration Drift in IaC

BCSE408L Cloud Computing project. Detects configuration drift on a real,
minimal, Always-Free-tier GCP deployment using a two-layer detector
(Terraform state-diff + live-inventory reconciliation), then ranks detected
drift by severity using a rule-based scorer compared against trained
classifiers, evaluated on a 16-item labelled corpus.

See `report/final-report.md` for the full writeup and `docs/review-{1,2,3}.md`
for the per-review evidence mapping.

## Reproduce end to end

Requires: `gcloud` (authenticated, billing-enabled project), Terraform
(installed globally, e.g. `winget install Hashicorp.Terraform`), Python 3
with `pyyaml`, `scikit-learn`, `matplotlib`.

```bash
# 1. Provision the real GCP baseline (compute, network, storage, identity)
cd infra
terraform init
terraform apply -auto-approve

# 2. Run the 16-scenario drift corpus (inject -> detect -> revert -> reconcile)
cd ..
python scripts/run_experiment.py

# 3. Feature extraction, scoring, evaluation
python scripts/extract_features.py
python classifier/rank.py
python eval/evaluate.py
python eval/bootstrap_ci.py
python eval/plot_results.py

# 4. Layer-2 spot check (live demo script)
python scripts/inventory_check.py
```

## Repository structure

```
infra/        Terraform for the free-tier GCP baseline
corpus/       Drift scenario definitions, raw plan diffs, extracted features
scripts/      Injector (run_experiment.py), Layer-2 detector (inventory_check.py),
              feature extraction
classifier/   Rule-based scorer + trained classifiers (LOOCV)
eval/         Precision@k evaluation, bootstrap CIs, plots
docs/         Problem statement, literature survey, architecture, protocol,
              threats to validity, per-review evidence mapping
report/       Final 6-8 page report
```

## Cost and safety

All provisioned resources are Always-Free-tier eligible: one `e2-micro` VM,
one small Cloud Storage bucket, one custom VPC + firewall rule, one service
account + IAM binding. A GCP billing budget alert (`p14-drift-budget`, $5,
50%/100% thresholds) is set on the project regardless. No console
interaction is required anywhere in this pipeline — provisioning, drift
injection/revert, detection, and analysis are all CLI/script-driven.

To tear down completely: `cd infra && terraform destroy -auto-approve`.
