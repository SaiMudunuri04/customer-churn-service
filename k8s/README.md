# Kubernetes delivery

[`helm/customer-churn-service/`](helm/customer-churn-service/) is the **only** Helm chart and source of Kubernetes workload definitions in this repository. It contains Deployment, Service, ServiceAccount, PodDisruptionBudget, HorizontalPodAutoscaler, and NetworkPolicy templates. [`argocd/application.yaml`](argocd/application.yaml) tracks the chart path in this repository.

Before deploying, review `values.yaml` for the image tag, non-secret environment config (`config`, rendered into a ConfigMap for `MODEL_PATH`), artifact/data mounts, secrets, image pull access, resource sizing, health probes, and termination timing. `autoscaling.enabled` and `networkPolicy.enabled` are off by default; enable them only after the target cluster’s metrics, ingress peers, DNS, and external inference egress are understood. The default NetworkPolicy peer allows pods in the same namespace only. A PDB with `minAvailable: 1` assumes at least two replicas.

## Manifest map

The rendered workload definitions live under [`helm/customer-churn-service/templates/`](helm/customer-churn-service/templates/): `deployment.yaml`, `service.yaml`, `serviceaccount.yaml`, `configmap.yaml`, `pdb.yaml`, `hpa.yaml`, and `networkpolicy.yaml`. `helm/customer-churn-service/values.yaml` supplies configuration for those templates. There is intentionally no committed `secret.yaml`: credentials must be created in the cluster or injected by a secret manager, then referenced with `envFromSecretName`.

```sh
helm lint k8s/helm/customer-churn-service --strict
helm template customer-churn-service k8s/helm/customer-churn-service --namespace customer-churn-service
helm template customer-churn-service k8s/helm/customer-churn-service --namespace customer-churn-service --set autoscaling.enabled=true --set networkPolicy.enabled=true
```

See [architecture](../docs/architecture.md) and the [operations runbook](../docs/operations.md). The chart is a reference release definition; this repository does not claim a live cluster deployment.
