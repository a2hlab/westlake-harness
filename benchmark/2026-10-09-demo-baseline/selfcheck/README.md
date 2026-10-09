# Read-only demo selfcheck (t5 helper)

Evidence: the actual `demo_selfcheck.sh` CLI passes 13 known-answer tests on both
Mac and a2hlab, including a mocked transport success and missing remote-status
marker rejection. No board was contacted by these tests. See
[evidence/tests-mac.txt](evidence/tests-mac.txt),
[evidence/tests-vm.txt](evidence/tests-vm.txt) and
[evidence/rust-test.txt](evidence/rust-test.txt).

The mistake this helper prevents is treating a saved fingerprint or successful
fixture comparison as proof of the live demo board. Offline comparison prints
`OFFLINE_MATCH`; only a complete successful read from the selected serial prints
`PASS`. Neither status proves that an app renders content: that requires the
outer review of `snapshot_display` evidence.

## Scope and contract status

This is the selfcheck portion of t5, prepared before the final demo manifest and
sealed board snapshot. It does not seal a board, restore a board, change AGENTS,
or implement the final demonstration runbook. The `demo_baseline_selfcheck`
Rust selector invokes the Python known answers. It deliberately does not use
the shared `demo_baseline_seal` selector, whose restore/runbook scenarios remain
pending. See [evidence/lifecycle-t5.txt](evidence/lifecycle-t5.txt).

## Input and execution

The future sealing step must supply a complete `demo-seal/v1` snapshot, not the
app-install manifest. Required fields are:

| Field | Meaning |
| --- | --- |
| `serial` | Exact whitelisted connect key of the sealed board |
| `files.runtime` | Board path to full SHA256 for every runtime identity member |
| `files.boot` | Board path to full SHA256 for every boot identity member |
| `files.overlays` | Board path to full SHA256 for every effective overlay; may be empty |
| `files.installation` | Both installation-service paths and other sealed installation identities |
| `system_params` | Parameter name to expected full value, including system version |
| `packages` | Objects with `package`, `version_code`, installed `apk_path`, `apk_sha256` |
| `inventories` (optional) | Exact path lists plus safe glob patterns to detect added runtime files |

The file groups compare effective bytes, not the origin of a bind mount. If a
sealed snapshot needs to reject additional files, include the corresponding
inventory. The script does not invent an authoritative snapshot from current
board state. Complete membership and overlay provenance belong to the sealing
receipt.

```bash
bash scripts/lab/demo_selfcheck.sh \
  --seal "$DEMO_SEAL" --serial "$DEMO_SERIAL" --out "$FRESH_RECEIPT"
```

Live reads are limited to `sha256sum`, `param get`, `bm dump -n`, and the boot ID
before/after. Mac runs HDC through `orb -m a2hlab`; inside the VM it uses the same
`hdc_mac.sh` wrapper directly. The serial must match both the seal and repository
whitelist. There are no installs, starts, screenshots, configuration writes or
lock operations. `--out` writes a fresh host-side receipt only.

Each result prints `EQUAL` or `DRIFT`, the path, expected value, and actual value.
Exit codes: 0 = exact comparison, 1 = drift/read failure, 2 = rejected input.
A missing file, package identity, system version, status marker, inventory
member, or unstable boot fails closed. The script does not retry a failure into
a success. To compare a recorded observation without contacting a device:

```bash
bash scripts/lab/demo_selfcheck.sh \
  --seal "$DEMO_SEAL" --serial "$DEMO_SERIAL" \
  --observed "$RECORDED_OBSERVATION" --out "$FRESH_RECEIPT"
```

Observation fields are `serial`, `boot_before`, `boot_after`, `files`,
`system_params`, `packages` (package-name mapping to `version_code`),
`inventories` (one sorted path list per sealed inventory), and `errors`.
This mode returns `OFFLINE_MATCH`, never a live `PASS`.

## Known answers

The suite covers exact identity, changed SHA with both values printed, absent
file, changed package version and APK SHA, changed system version, boot change,
wrong serial, unsafe path, added inventory member, incomplete seal, recorded
read error, full transport parsing, and lost status marker. The transport tests
substitute a local executable, assert the read-only command list, and make no
real HDC call.

```bash
python3 benchmark/2026-10-09-demo-baseline/selfcheck/test_selfcheck.py -v
cargo test --manifest-path tools/spec-checks/Cargo.toml \
  --test demo_baseline demo_baseline_selfcheck -- --nocapture
```
