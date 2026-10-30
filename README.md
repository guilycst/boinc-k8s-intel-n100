# BOINC on Kubernetes with an Intel N100

Manifests, thermal supervisors and the patched Intel OpenCL image used by the
[Guigoes BOINC guide, in preview](https://feat-boinc-science-guide-guigoes-v2.guilycst.workers.dev/blogs/boinc-ciencia-cpu-gpu-kubernetes/).
This repository contains a portable adaptation of that installation, with
node/storage placeholders and interactive Science United account attachment.

| Artifact | Location |
| --- | --- |
| CPU-only example from the guide, using the official BOINC image | [examples/cpu/boinc-cpu.yaml](examples/cpu/boinc-cpu.yaml) |
| CPU and Intel GPU pilot, with independent thermal guards | [kustomization.yaml](kustomization.yaml), [manifests/](manifests/) |
| Thermal supervisors and bootstrap | [runtime/](runtime/) |
| BOINC patch, Dockerfile and executable image checks | [image/](image/) |
| Intel GPU device plugin, pinned to 0.37.1 with 10 shared slots | [device-plugin/](device-plugin/) |
| PromQL from the guide | [monitoring.md](monitoring.md) |
| Editable Mermaid diagrams from the guide | [diagrams/](diagrams/) |

The CPU-only example uses native Kubernetes resources and starts BOINC directly.
It has no thermal supervisor. The separate pilot runs Python supervisors and
requires Intel `coretemp` sensors. The GPU guard controls GPU work; CPU work in
that same GPU client keeps its configured budget. The CPU-only pilot client has
its own CPU guard on another node.

## Requirements

- Kubernetes 1.32 or newer, Linux AMD64 nodes, `kubectl`, and permission to create
  namespaces and cluster-scoped PriorityClasses.
- A StorageClass supporting 8 GiB ReadWriteOnce claims, UID/GID 1000 and `fsGroup`.
- Internet access to Science United and participating projects.
- For the GPU pilot: an Intel N100 iGPU, host i915 driver, a compatible Intel
  OpenCL runtime and Intel GPU device plugin. On Talos, install the matching
  [official extensions](https://github.com/siderolabs/extensions#readme)
  for the OS version. Verify hardware support before scheduling scientific work.
- A Science United account. Account files and project credentials belong only
  on each client's private PVC.

## Start with CPU

Download [boinc-cpu.yaml](examples/cpu/boinc-cpu.yaml), replace
`REPLACE_WITH_NODE`, `REPLACE_WITH_STORAGE_CLASS`, and both BOINC RAM percentages.
The defaults allocate one CPU, 1 GiB RAM and an 8 GiB PVC. The example's 4.6875%
RAM preference assumes a 16 GiB host and leaves 256 MiB for the BOINC client.

```sh
kubectl --context YOUR_CONTEXT apply -f examples/cpu/boinc-cpu.yaml
kubectl --context YOUR_CONTEXT -n boinc-example rollout status statefulset/boinc
```

Follow account attachment below with namespace `boinc-example`, pod `boinc-0`.

## Intel N100 pilot

The root Kustomization creates namespace `boinc-pilot`, a one-replica GPU
StatefulSet and a one-replica CPU Deployment. Each requests 25m CPU and 2 GiB RAM,
with limits of two CPUs and 2 GiB RAM and its own 8 GiB PVC. The GPU client
advertises one CPU to BOINC; the CPU client advertises two. The quota permits two
pods, four CPUs, 4 GiB RAM, one Intel allocation and two PVCs totaling 16 GiB.
The article's older installation retains one additional historical PVC.

1. Replace `REPLACE_WITH_GPU_NODE`, `REPLACE_WITH_CPU_NODE` and
   `REPLACE_WITH_STORAGE_CLASS` in `manifests/`. Use two different nodes.
2. Check an existing Intel plugin before installing another instance. If needed,
   label the selected GPU node and install the supplied plugin:

   ```sh
   kubectl --context YOUR_CONTEXT label node YOUR_GPU_NODE gpu.intel.com/has-gpu=true
   kubectl --context YOUR_CONTEXT apply -k device-plugin
   ```

   The plugin needs host device paths and kubelet sockets in its own privileged
   namespace. BOINC runs in a separate restricted namespace without hostPath
   mounts. Ten plugin slots share the device; an allocation is access to the
   GPU, not an exclusive utilization or power fraction.
3. Render and inspect the resources before applying:

   ```sh
   kubectl kustomize .
   kubectl --context YOUR_CONTEXT apply -k .
   kubectl --context YOUR_CONTEXT -n boinc-pilot rollout status statefulset/boinc
   kubectl --context YOUR_CONTEXT -n boinc-pilot rollout status deployment/boinc-cpu-1
   kubectl --context YOUR_CONTEXT -n boinc-pilot get pods,pvc
   ```

The bootstrap converts the container memory limit minus 256 MiB into a percentage
of host RAM, as BOINC 8.0.4 reads host memory. It preserves account-manager files
and configures suspended applications to remain resident. Each guard starts
conservatively, pauses at 85 C and resumes at 80 C. Invalid/missing sensors pause
work. A failed attempted RPC command terminates BOINC. Startup failure handling
precedes application execution: CPU delay/retry budget 30/20 seconds, GPU 90/60,
with four-second RPC timeouts. This is cooperative control, not a physical
temperature ceiling.

## Attach Science United interactively

Open a shell in each client. For the pilot, the GPU pod is `boinc-0`; find the CPU
pod with `kubectl --context YOUR_CONTEXT -n boinc-pilot get pods`.

```sh
kubectl --context YOUR_CONTEXT -n YOUR_NAMESPACE exec -it YOUR_POD -- /bin/bash
```

Inside the container:

```sh
read -r -p "Science United email: " BOINC_EMAIL
read -r -s -p "Password: " BOINC_PASSWORD
printf '\n'
boinccmd --join_acct_mgr https://scienceunited.org/ "$BOINC_EMAIL" "$BOINC_PASSWORD"
unset BOINC_EMAIL BOINC_PASSWORD
exit
```

Account association persists on the PVC. Check tasks and uploads with:

```sh
kubectl --context YOUR_CONTEXT -n YOUR_NAMESPACE logs YOUR_POD
kubectl --context YOUR_CONTEXT -n YOUR_NAMESPACE exec YOUR_POD -- boinccmd --get_tasks
```

For GitOps installations, apply lifecycle changes through their Git owner.
Maintain one writer per PVC; a restart recovers the last application checkpoint.
The CPU Deployment uses Recreate. StatefulSet claims use explicit Retain policy.
Let pending work finish, upload and report before permanently removing a client.

## Image and source

The container is published as
`ghcr.io/guilycst/boinc-k8s-intel-n100`, for `linux/amd64`.
The GPU manifest pins the published OCI index digest
`sha256:6e027d800c8af22eb4996906a134a5f3a7c4389405f01f08ff4ef791f056cdbe`.
The build is tagged `sha-dbf1ca31b350f0bcb79810312849d2f489048af8`; anonymous
pulls are supported. See the [container package](https://github.com/users/guilycst/packages/container/package/boinc-k8s-intel-n100).
The image build uses:

- Official BOINC 8.0.4 base digest
  `a9629c767fcaab695401a2a4a6a34befe087f6cc59a41c51539531eff645e6e2`.
- BOINC source commit
  [`ef335f4614477b53879af8c1a59f3621f80bdd55`](https://github.com/BOINC/boinc/tree/ef335f4614477b53879af8c1a59f3621f80bdd55).
- [single-gpu-task.patch](image/single-gpu-task.patch), which reserves at least one
  whole GPU per application version, including app_config overrides, and honors
  `leave_apps_in_memory` during GPU suspension.

This is a modified BOINC client, not an official BOINC image. The patch bounds
concurrency inside this client; other pods can still share the physical GPU.
The image's build tests exercise the real patched client without GPU hardware:
fractional allocations, app_config overrides and same-process GPU pause/resume.
APT package versions are resolved at build time. The published digest identifies
the built bytes; the Dockerfile is not a promise of bit-for-bit rebuilds.

```sh
make image
```

## Development checks

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
make check
```

Checks render all Kustomizations, parse XML, inspect workload isolation and
budgets, and exercise hysteresis, startup RPC failure and configuration handling.
See [VALIDATION.md](VALIDATION.md) for the public image and runtime test receipt.
CI builds the image on AMD64. Local unit/manifest checks do not prove iGPU driver
compatibility or scientific-task availability; those depend on the target host
and project. The CPU tutorial was previously reproduced on Kubernetes 1.35;
the portable pilot's hardware behavior must be checked on its selected nodes.

## License

GNU LGPL 3.0 or later. See [LICENSE](LICENSE), [COPYING.LESSER](COPYING.LESSER),
[COPYING](COPYING) and the upstream [COPYRIGHT](COPYRIGHT) notice. BOINC remains
copyright its authors; the source commit and local patch are available above.
Intel's device-plugin image is distributed separately by its upstream project.
