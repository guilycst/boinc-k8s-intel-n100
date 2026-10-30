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

## Coverage

The OpenCL kernel verifies device execution and returned data for this exact
image and host. The NumberFields task's reported fraction remained `0.860106`,
and its own i915 engine counter stayed at zero during the observed window.
Its GPU calculation, completion, upload and project validation were not proven.
Thermal pauses limited the available execution time. No OOM events or pod
restarts were observed during the rollout checks.

The earlier CPU smoke test used AMD64 emulation. The portable pilot bootstrap
and manifests still need validation together on their selected physical nodes.
