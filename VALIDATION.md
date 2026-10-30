# Verification receipt

Verified on 2026-10-30, America/Sao_Paulo.

## Published image

- Public package: `ghcr.io/guilycst/boinc-k8s-intel-n100`.
- OCI index: `sha256:6e027d800c8af22eb4996906a134a5f3a7c4389405f01f08ff4ef791f056cdbe`.
- Image source commit: `dbf1ca31b350f0bcb79810312849d2f489048af8`.
- [AMD64 image build](https://github.com/guilycst/boinc-k8s-intel-n100/actions/runs/41009713577)
  passed, including both executable patched-client fixtures in the Dockerfile.
- Manifest lookup and image pull succeeded with an empty Docker credential
  configuration, confirming anonymous registry access.
- OCI source/revision labels point to this public repository and source commit.

## Runtime and manifests

- `make check` passed: both guard self-tests, three unittest methods with CPU/GPU
  subcases, all three Kustomizations, XML parsing, workload security checks and
  the pilot's two-pod/two-PVC resource budget.
- `actionlint` accepted both workflows. The BOINC patch applies cleanly to the
  pinned upstream source. The article's CPU YAML was copied without changes.
- The published AMD64 image booted under local OrbStack emulation with UID/GID
  1000, read-only root, no capabilities, no network, two CPUs and a 2 GiB memory
  limit. Writable data/tmp were disposable tmpfs mounts.
- The portable bootstrap loaded its XML preferences, retained suspended apps,
  set the internal task RAM budget to 1.75 GiB using the host-memory percentage,
  and launched the unchanged CPU thermal guard. With no valid `coretemp` sensor,
  the guard selected permanent CPU mode `never` and became ready.
- SIGTERM stopped the client and supervisor cleanly with exit status 0. The
  disposable container and data were removed.

## Real Intel N100 deployment

The published digest replaced the GPU image in an existing GitOps installation
on 2026-10-30. This was an image-only rollout. The existing bootstrap and thermal
guard remained mounted, and the portable pilot manifests were not redeployed.

- Argo CD reached `Synced/Healthy` at the deployment commit. The replacement GPU
  pod became ready with zero restarts. The CPU-only pod kept its original UID.
- All three existing 8 GiB PVCs kept their UIDs and volume bindings. Controller
  specifications, `ResourceQuota` and `LimitRange` matched the baseline except
  for the GPU image reference.
- GPU limits remained two CPUs, 2 GiB RAM and one `gpu.intel.com/i915` allocation.
  CPU request remained `25m`, memory request 2 GiB, and the BOINC task RAM budget
  1.75 GiB. The live cgroups reported the same CPU and memory ceilings.
- `clinfo` and BOINC both detected Intel UHD Graphics on the physical N100,
  using Intel OpenCL driver `23.43.027642` and the host i915 device.
- A short OpenCL kernel ran inside the deployed container on that GPU. It
  transformed 4,096 integers with `a[i] = a[i] * 2 + 1`. Every returned value
  matched, checksum was `16777216`, and that process recorded `69160 ns` of
  `drm-engine-render` activity through i915.
- The existing NumberFields GPU task loaded its saved CPU-time checkpoint of
  `2556.809` seconds. Its CPU time later reached `2602.871` seconds. Thermal
  pause/resume retained PID 69; observed decisions included pause at 85 degrees
  Celsius and resume at 78 or 79 degrees. Thresholds remained 85/80 degrees.
- CPU tasks in the GPU client were suspended for a three-minute diagnostic
  window, then restored. The separate CPU client was left running. No thermal
  override, resource increase or additional persistent scientific client was used.

## Initial rollout coverage

The OpenCL kernel verifies device execution and returned data for this exact
image and host. The NumberFields task's reported fraction remained `0.860106`,
and its own i915 engine counter stayed at zero during the observed window.
Its GPU calculation, completion, upload and project validation were not proven.
Thermal pauses limited the available execution time. No OOM events or pod
restarts were observed during the rollout checks.

The earlier CPU smoke test used AMD64 emulation. The portable pilot bootstrap
and manifests still need validation together on their selected physical nodes.

## Scientific GPU task follow-up

A follow-up observation on 2026-10-30 confirmed execution by the existing
NumberFields application on the physical GPU. This observation made no workload,
account, scheduling, volume, resource-limit or thermal-policy changes.

The same task, `wu_sf6_DS-16x10_Grp19870932of20000000_0`, remained PID 69 with
i915 DRM client 51 throughout these samples:

| Time, UTC | Reported fraction complete | Application i915 render time | Saved CPU-time checkpoint |
| --- | --- | --- | --- |
| 06:33:48 | 0.860108 | 27.764212272 s | 2662.669 s |
| 06:34:39 | 0.860109 | 36.744937944 s | 2662.669 s |
| 06:35:42 | 0.860110 | 43.923278724 s | 2664.509 s |

The scientific process accumulated another 16.159 seconds on the GPU engine in
113.774 seconds of wall time. Both reported progress and its saved checkpoint
advanced. These counters belong to the scientific application itself, separate
from the earlier diagnostic OpenCL kernel.

### Why it looked stalled

The initial rollout window ended with the application's log still at GPU lookup
and no application-sized GPU buffers or engine time. Its later log contains successful OpenCL
program compilation, kernel creation, buffer allocation and checkpoint loading.
This supports initialization and compilation as the explanation for that first
zero-engine observation. The exact compilation duration was not instrumented.
The [project developer describes runtime OpenCL compilation](https://numberfields.asu.edu/NumberFields/forum_thread.php?id=494&postid=3795#3795)
as an initial cost of each application run.

Thermal pauses explain much of the slow progress after initialization. Between
06:25:12 and 06:35:12 UTC, the unchanged supervisor authorized GPU work for
80.210 of 600 seconds, about 13.37 percent. Individual run intervals were mostly
two to four seconds. Pauses occurred at 85 degrees Celsius or higher and resume
decisions at 80 degrees or lower. CPU and integrated GPU share that package.

The container recorded only 9.402 ms of CPU-quota throttling over its lifetime
at the check, with zero memory cgroup OOM events. This does not support quota
exhaustion or an OOM as the cause of the observed stall. No restart, image swap,
GPU concurrency increase, thermal override or task suspension was needed for
this follow-up.

Both pod UIDs, all PVC UIDs and volume bindings, controller specifications,
resource policies, mounted guards and BOINC preferences were preserved. Task
completion, upload and server-side result validation remain outside this check.
