# BOINC resource queries

Replace `boinc` with `boinc-pilot` for the root pilot, or `boinc-example` for the
CPU-only example. These queries use kubelet/cAdvisor series collected by Prometheus.

CPU usage in cores, averaged over five minutes:

```promql
sum by (pod) (
  rate(container_cpu_usage_seconds_total{namespace="boinc",container="boinc"}[5m])
)
```

Memory working set in bytes:

```promql
sum by (pod) (
  container_memory_working_set_bytes{namespace="boinc",container="boinc"}
)
```

The Grafana dashboard `Kubernetes / Compute Resources / Namespace (Pods)` from
kube-prometheus-stack can display these resources per pod. Filter its namespace
to your installation. Observe host temperature and existing service latency
alongside these metrics; GPU-driver memory may be accounted differently.
