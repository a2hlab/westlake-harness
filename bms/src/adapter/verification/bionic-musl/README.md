# M05 Bionic/Musl Independent Verifier

This directory is the M05-owned verifier authority for the
`Bionic -> typed bridge -> Musl` reliability boundary. It contains no product
implementation and defines no product ABI.

## Boundary

- Offline entry: an integrator-approved `NativeGenerationReceiptV1` for the
  unchanged APK, its four Unity DSOs, the exact loader, Musl runtime, typed
  bridge, recursive providers, build inputs and tools. This receipt proves only
  the offline generation.
- Runtime-attach entry: a separate `ChildRuntimeReadyReceiptV1` bound to
  `SpawnBirthReceiptV1`, pid, startSeq, generation and epoch.
- Exit: a fail-closed M05 verdict for those exact bytes. The verdict may deny or
  admit those bytes to a later device run; it never proves Unity, first frame,
  rendering, interaction or product stability.
- Evidence labels are limited to `stub`, `build_pass`, `real_impl` and
  `device_verified`.

The current branch starts with no M04 candidate. The canonical bootstrap named
by the lane contract and the existing 22-gate runtime-generation red-team source
are also absent from this worktree. Consequently
[`baselines/current.json`](baselines/current.json) is a valid fail-closed report,
not a candidate PASS.

## First-round artifacts

- [`RISK_REGISTER.md`](RISK_REGISTER.md) is the risk and stop-line ledger.
- [`var/evidence/INTEGRATION_REQUEST.md`](var/evidence/INTEGRATION_REQUEST.md) lists the
  minimal current-byte facts M05 needs without defining a cross-module schema.
- [`schema/reliability-baseline.v1.schema.json`](schema/reliability-baseline.v1.schema.json)
  is an M05-private normalized evidence schema.
- `adapter/scripts/ci/bionic_musl_validate_baseline.py` applies the semantic
  fail-closed gates that JSON Schema alone cannot express.
- `tests/` contains a local synthetic positive and single-variable mutants. A
  synthetic pass is always `device_admission=false`.

## Local verification

```sh
python3 adapter/scripts/ci/bionic_musl_validate_baseline.py \
  adapter/verification/bionic-musl/baselines/current.json
python3 -m unittest discover \
  -s adapter/verification/bionic-musl/tests -p 'test_*.py' -v
```

Use `--require-offline-ready` for the exact-current offline gate,
`--require-runtime-ready` for the separate child/spawn attach gate, and
`--require-admission` only for the full target reliability verdict. The
checked-in current report must fail all three at the first missing-input gate.

## Promotion stop-lines

- A previous generation's PASS never transfers.
- A self-test, host sanitizer run, QEMU run, process-alive observation or
  successful `dlopen` never becomes `device_verified`.
- Missing bootstrap/S1-S7 mapping, missing current receipt, fewer than 22
  imported red-team gates, wrong generation token, unresolved strong UND,
  ambient provider, unsealed FD, resource slope or timeout all deny admission.
- `NativeGenerationReceiptV1` never satisfies the runtime-ready gate. Attach is
  forbidden until the separate child/spawn/pid/startSeq/generation/epoch binding
  is verified.
- HP-9 is not a usable input until its source is frozen into this project; the
  02d sibling is forbidden. OH system-service patches are read-only unless an
  integrator approves an exact-file request.
- Shared receipt/schema ownership remains with the integrator. M05 only
  normalizes and verifies an approved receipt.
