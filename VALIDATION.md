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

## Coverage

The CPU smoke test used AMD64 emulation, not an Intel N100 GPU. No new scientific
account or task was attached. No production workloads or cluster settings were
changed. Real i915/OpenCL device compatibility and GPU scientific applications
must be checked on the selected physical nodes. Existing guard behavior and
the published client's hardware-free scheduling fixtures are separate evidence.
