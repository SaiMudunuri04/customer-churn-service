# Churn scoring

[Architecture](docs/architecture.md) · [Operations runbook](docs/operations.md) · [Helm chart](k8s/helm/customer-churn-service/) · [Argo CD application](k8s/argocd/application.yaml)

An independent service for scikit-learn pipeline and SageMaker training. This repository contains executable source, tests,
a container, Helm release, Argo CD application, and a CI workflow that builds an
immutable GHCR image after tests pass. It is a reference implementation; it has not
been deployed to a user's AWS account or Kubernetes cluster.

## Run

```sh
python -m pip install -e '.[test]'
python -m pytest -q
ruff check .
helm lint k8s/helm/customer-churn-service --strict
uvicorn service.app:app --reload
```

`/health/live` checks the process. `/health/ready` checks required local resources. Responses include a request ID and no-store/nosniff headers; JSON request logs omit bodies and query strings.
Configure data, model artifacts, and inference endpoints before serving traffic.

## Delivery

The workflow tests pull requests, then builds/pushes an image to GHCR on `main` and
updates the Helm image tag to the tested commit. Argo CD follows the single chart at [`k8s/helm/customer-churn-service/`](k8s/helm/customer-churn-service/).
Install `k8s/argocd/application.yaml` in a cluster with Argo CD, set environment-specific
Helm values, provide secrets through a cluster secret manager, and make the package
pullable by the cluster. Model/data volumes are configured through `volumes` and
`volumeMounts`; use `envFromSecretName` for credentials. The workflow does not
provision AWS or a cluster.

`.env.example` contains placeholders only. Never commit credentials or private data.

## Training data and model lifecycle

Input `churn.csv` requires `customer_id,observed_at,churned,tenure_months,monthly_spend,support_tickets,usage_hours`. Each customer appears once with a nonempty ID; `observed_at` is ISO 8601 and observed feature values must be nonnegative. Empty feature cells are imputed within the training pipeline. The code sorts by observation time, selects a threshold on validation only, and reports ROC-AUC, F1, precision, recall, and Brier score on the untouched test period.

```sh
python -m service.train --train-file /path/to/churn.csv --output artifacts
MODEL_PATH=artifacts/model.joblib uvicorn service.app:app --host 127.0.0.1
python -m pip install -e '.[aws]'
python scripts/launch_sagemaker.py --training-s3-uri s3://your-bucket/churn-training/
```

The SageMaker training channel must contain `churn.csv`. The launch script uses the `1.4-2` scikit-learn framework image and an IAM execution role. Put reviewed model artifacts on a read-only volume at `/models`; set `MODEL_PATH` via Helm. Never load joblib files from untrusted sources. There is no claimed business-data accuracy or live AWS training run.
