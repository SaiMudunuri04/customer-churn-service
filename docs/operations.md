# Customer churn scoring operations

This is a deployment runbook for an operator to adapt. No AWS account or Kubernetes cluster has been connected by this repository.

## Before a rollout

1. Review the [architecture](architecture.md), tests, image tag, and [Helm values](../k8s/helm/customer-churn-service/values.yaml).
2. Prepare `MODEL_PATH` and, for training, the CSV input path. Supply the artifact on a read-only volume.
3. Provide image pull credentials if GHCR is private. Set resource limits to match measured model and traffic needs. Confirm the namespace's NetworkPolicy peers and egress before enabling it.
4. Render both chart modes locally: `helm lint k8s/helm/customer-churn-service --strict`, `helm template customer-churn-service k8s/helm/customer-churn-service`, and `helm template customer-churn-service k8s/helm/customer-churn-service --set autoscaling.enabled=true --set networkPolicy.enabled=true`.

## Verify

- Check `kubectl -n customer-churn-service rollout status deployment/customer-churn-service` and inspect `/health/live` and `/health/ready` through the Service.
- Use the `X-Request-ID` response header to locate a matching JSON request log. Watch status and duration trends in the operator's logging system; no alert thresholds are prevalidated here.
- A readiness failure indicates local prerequisites such as model artifact, catalog, or document files. A liveness failure indicates an unhealthy process. Check the container's logs before restarting it.

## Recover

- If a new image is faulty, revert the Git commit or pin the previous reviewed image tag in the chart and let Argo CD sync it. Do not edit live resources as the lasting fix.
- If a model or data mount is missing, restore the read-only volume or secret and verify readiness before routing traffic.
- If HPA is enabled, confirm metrics-server availability and CPU requests. If NetworkPolicy is enabled, verify allowed ingress peers and any external inference/DNS egress.

## Known limits

The repository contains no customer data, measured business accuracy, drift monitor, or live SageMaker deployment.
