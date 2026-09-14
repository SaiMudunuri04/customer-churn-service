# Customer churn scoring architecture

## Request and model path

CSV observations → chronological split → imputed/scaled logistic regression → validation-only threshold → held-out evaluation → joblib artifact → FastAPI scoring

## Boundaries

- **Input:** `churn.csv` with unique customer IDs, timestamps, binary labels, and nonnegative features. Missing feature cells are imputed inside the training pipeline.
- **Runtime:** `MODEL_PATH` points to a reviewed local joblib artifact. `/predict` validates four nonnegative finite features and returns a probability and threshold decision.
- **Failure behavior:** A missing or schema-incompatible artifact makes readiness and prediction return 503. Joblib deserialization is unsafe for untrusted files.

The FastAPI process exposes `/health/live` for process liveness and `/health/ready` for local prerequisites. Each HTTP response carries a generated `X-Request-ID`, `Cache-Control: no-store`, and `X-Content-Type-Options: nosniff`. JSON request logs record method, path, status, request ID, and duration, never request bodies, query strings, credentials, or user data. Logs are local process telemetry, not a claim of production monitoring.

The [single Helm chart](../k8s/helm/customer-churn-service/) provides rolling updates, probes, resource bounds, security contexts, optional HPA and NetworkPolicy, and a PDB. [Argo CD](../k8s/argocd/application.yaml) points to that chart. Values need environment review before deployment, especially image pull access, ingress peers, external inference egress, and artifact mounts.

## Limits

The repository contains no customer data, measured business accuracy, drift monitor, or live SageMaker deployment.
