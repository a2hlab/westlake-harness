# AonB D600 Verification Harness

This directory contains the automated D600 probe harness and standalone probe binaries for the AonB seamless-runtime route plan.

## Files

- `aonb_d600_probe.sh` — main harness implementing the probe order from `/opt/Bridge/archive/docs-superseded/aonb-d600-verification-plan.md` §5.
- `netprobe.c` — standalone socket-permission probe (G6/N2).
- `z01_native_window_probe.cpp` — standalone OHNativeWindow commit probe (G5).
- `build_probes.sh` — cross-compiles `netprobe` and `z01_native_window_probe` for D600.

## Usage

```bash
# Set environment (or rely on defaults)
export D600_SERIAL="D600XXXXXXXX"
export WORKDIR="/opt/Bridge/evidence/aonb-d600-phase5"
export APK_DIR="/path/to/signed/test/apks"

# Run all probes in dependency order
cd /opt/Bridge/src/adapter
bash verification/aonb_d600_probe.sh all

# Run a single probe
bash verification/aonb_d600_probe.sh g8
```

## Defaults

| Variable | Default |
|---|---|
| `D600_SERIAL` | First target returned by `hdc list targets` |
| `WORKDIR` | `<adapter-root>/out/aonb-d600-probe-evidence` |
| `APK_DIR` | `<adapter-root>/app/build/outputs/apk/debug` |

## Building the standalone probes

```bash
cd /opt/Bridge/src/adapter
export OH_ROOT=/data/oh61-wukong100
export AOSP_ROOT=/data/aosp-arm64-d600
bash verification/build_probes.sh
```

Preflight will fail early with a clear list if the OH build tree / toolchain / sysroot is missing. To inspect the build plan without compiling:

```bash
bash verification/build_probes.sh --dry-run
```

Output:

- `verification/out/netprobe`
- `verification/out/z01_native_window_probe`

## Evidence layout

Each probe writes to `${WORKDIR}/g<NN>/`:

- `MANIFEST.yaml` — gate, verdict, timestamp, device serial, fingerprints
- `*.log` — command outputs
- `hilog.txt` / `bm-dump.txt` / `proc-maps.txt` — as defined by the seamless definition §9
- `reviewer.md` — independent reviewer checklist template

## Probe order

1. `g11` — build provenance / device baseline
2. `g8` — raw APK install
3. `g9` — APK signature trust
4. `g10` — native library / boot image
5. `g7` — lifecycle spawn
6. `g13` — system-service stubbing
7. `g5` — graphics bridge
8. `g12` — input fidelity
9. `g6` — permissions / identity + eBPF socket grant
10. `g14` — resources / ContentProvider
11. `perf` — cold-start calibration

## Notes

- The harness requires `hdc`, `bm`, `aa`, and `hilog` to be available (host `hdc`; device-side `bm/aa/hilog`).
- Missing optional test APKs or probe binaries produce `BLOCK` verdicts, not fatal errors.
- The `perf` probe records host timestamps as a placeholder; accurate latency requires hilog timestamp parsing (documented as a known limitation).
