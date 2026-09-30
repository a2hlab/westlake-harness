# B10 additive master landing

## What was wrong; what this establishes

The accepted B10 scanner was still branch-only. Copying its main directory alone
does not reproduce its contracts: feedback imports and frozen-input guards reach
sibling evidence trees. Eight historical ELF **text export lists** were also
silently excluded by `.gitignore:21` (`*.so.*`).

This handoff supplies **2,659 new destination paths**: **2,651 pinned Git files**
(111,503,520 bytes), plus **eight recovered inputs** (73,426 bytes). None exists
at the pinned master. There are **924**, not 915, tracked B10-directory files.
The rule is additive import plus explicit dependency closure, never wholesale
replacement of master files or retrospective alteration of frozen evidence.

**The gate is conditionally green, not the test suite.** Complete overlay with
master's existing seven exceptions returns **1**: 54 pass, nine fail, two
unexpected. Adding the two explicit proposals in `proposed-exceptions.json`
to a disposable registry returns **0**: the same 54 pass and nine fail, all nine
excepted. Outer adoption of both proposals is required before a default master
gate can reproduce that result. No exception has been approved on outer's behalf.

## Exact pins and artifacts

- Source: `322ef35a2065c62cda2304efc2e5b7ad5bbf2040`
  (`analysis/bms-route-study`, accepted native-scanner revision).
- Destination: `ce38611fed554d81a7699f0f604ba01ff4203f9a`.
- `paths.txt`: sorted complete scanner/dependency destination file list;
  SHA256 `bdcc348d0569783a803e4f4d03ada8503f15c0c964b686fc089195ea7ec69a96`.
- `lib-rs-additions.rs`: append to `tools/spec-checks/src/lib.rs`;
  SHA256 `8202bce469657d10eb2598488e2594145c952d0cbe77a1067a0c6eeef7e2e48e`.
- `results.json`: counts, eight recovery mappings and hashes, selector list,
  artifact hashes, preservation audit and actual gate results.
- `recovered-inputs/`: exact original ignored text bytes, matched against
  `benchmark/2026-09-30-v2-scanner-feedback/preserved-inputs.json` and the v2
  freeze. These eight files are **not** available from the pinned source Git
  tree; the handoff payload is mandatory. No symbol lists were regenerated.
- `evidence/{initial-gate,additive-gate,proposed-gate}.log`: complete raw gate
  outputs, including truthful Cargo failures. `evidence/lifecycle.json`:
  three passing landing-contract scenarios.

The manifest does not list this handoff directory or `specs/b10-landing/`:
land those new metadata directories too, separately from the 2,659 payload paths.
Do not import unrelated untracked spec-gate files from the lane worktree; master
already owns that gate. If master advances, recheck collisions and rerun; the
recorded result is only for the destination SHA above.

## Dependency closure

| Destination prefix | Files | Why imported |
| --- | ---: | --- |
| `benchmark/2026-09-29-static-wall-prediction/` | 924 | Entire B10 scanner, frozen matrices, native corpus and all ten top-level Python test modules |
| `benchmark/2026-09-30-r16-prospective/` | 298 | B10 t6 frozen forecast and scoring selectors |
| `benchmark/2026-09-30-r16-feedback/` | 109 | B10 t7 rule/matrix selectors |
| `benchmark/2026-09-30-v2-scanner-feedback/` | 159 | B10 t8 rules, matrix and immutable prior-input guard |
| `benchmark/2026-09-30-v3c-r17j-prospective/` | 616 | 608 Git files plus eight recovered exports; 490 prior-input SHA pins and v2 freeze checks |
| `benchmark/2026-09-30-background-start-prospective/` | 227 | `detector`, lifecycle/Activity helpers and manifest/DEX caches used by v2 and installer scanning |
| `benchmark/2026-09-30-r17op-prospective/` | 306 | Unified-audio frozen profiles plus `engine`/`audit_run` imports |
| `benchmark/2026-09-30-r17op-execution-revision/` | 7 | Unified scoring imports `profile_audit` |
| `benchmark/2026-09-30-r17p-61b-comparison/final/results.json` | 1 | Installer replay truth; do not import its other 429 files |
| `scripts/lab/jni_gate.py` | 1 | JNI negative gate exercised by B10 |
| `specs/bms-static-v3/` | 10 | Shared contract plus t1–t9 |
| `tools/spec-checks/tests/native_initialization.rs` | 1 | Three native initialization integration selectors |

The sibling roots retain their recorded dependency data as coherent trees; they
are not claimed to be byte-minimal. Their unrelated deployment/scoring selectors
are **not** added to master. There are no runtime binaries in the recovered
payloads.

## Selector and exception instructions

Append `lib-rs-additions.rs` **once**, without changing existing functions.
It contains 29 verbatim source-branch bodies (14 b10, three b85, six b90,
four r16, two v2), plus two new B10-only whole-module bridges:
`b10_installer_background` and `b10_unified_r17r`. The latter's eight Python
cases pass. The native integration file supplies three more selectors; do not
duplicate them in lib.rs. Total added selectors: **34 = 32 pass + two fail**.

The four `r16_*` bodies are included because imported B10 t6/t7 contracts bind
them, not because all branch selectors should be copied. No B1/B4/B5/B7,
white-window, U4, image-building or unrelated runtime selector is imported.

| Proposed selector | Category | Evidence and removal condition |
| --- | --- | --- |
| `b10_build_silent_skip_fails` | `open-acceptance` | Pinned master `bms/src/adapter/build/inner/compile_oh_adapter_bridge.sh:448` uses `[ -f "$src" ] || continue`; unchanged `test_static.py:112` observes `0 == 0` after removing a required manifest JNI source. This is a real missing fail-closed fix, not missing evidence. Outer must separately review the source-branch build-script changes, then require all missing-source cases to fail correctly and remove the exception. |
| `b10_installer_background` | `baked-path` | Unchanged `test_installer_background.py:55` compares the regenerated matrix to absolute checkout paths in the historic matrix. All 66 rows differ; 457 structural differences are exactly 392 input-key additions/removals and 65 manifest-source values. Replacing **only** the checkout prefix in memory makes the entire documents equal, including input hashes. Four rule/evaluation cases pass; inventory fails. Remove only after an approved path-portable comparison passes in another checkout without rewriting the frozen observations or skipping coverage. |

`proposed-exceptions.json` gives full reasons, repository-relative evidence and
removal conditions. Preserve the seven existing entries. After explicit outer
adoption, append only these two entries to the real registry and record approval;
do not replace its whole document with the simulation registry. An EXCEPTED
verdict never means the underlying acceptance passed. If either selector starts
passing, the gate reports STALE and the corresponding entry needs review/removal.

## Disposable reproduction

Use bash and the existing lab environment. This only creates a new temporary
master export; it does not touch the shared master worktree.

```bash
source "$HOME/orca/workspaces/westlake-inputs/env-mac.sh"
export SOURCE_WT="$PWD"
export LANDING="$SOURCE_WT/benchmark/2026-10-01-b10-landing"
export DEST="$(mktemp -d /tmp/westlake-b10-replay.XXXXXX)"
python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path
import subprocess

source = Path(os.environ["SOURCE_WT"])
landing = Path(os.environ["LANDING"])
destination = Path(os.environ["DEST"])
receipt = json.loads((landing / "results.json").read_text())
paths = (landing / "paths.txt").read_text().splitlines()
source_revision = receipt["source_commit"]
master_revision = receipt["master_commit"]

def names(revision):
    output = subprocess.check_output(
        ["git", "ls-tree", "-rz", "--name-only", revision], cwd=source)
    return set(output.decode().rstrip("\0").split("\0"))

def extract(revision, selected=()):
    archive = subprocess.Popen(
        ["git", "archive", revision, *selected], cwd=source,
        stdout=subprocess.PIPE)
    try:
        subprocess.run(["tar", "-xf", "-", "-C", str(destination)],
                       stdin=archive.stdout, check=True)
    finally:
        archive.stdout.close()
    assert archive.wait() == 0

assert not any(destination.iterdir()), "destination must be empty"
assert len(paths) == len(set(paths)) == 2659
assert not set(paths) & names(master_revision), "existing master path collision"
recovered = {item["destination"]: item for item in receipt["recovered_inputs"]}
tracked = [name for name in paths if name not in recovered]
assert len(tracked) == 2651 and set(tracked) <= names(source_revision)
assert set(recovered) <= set(paths)
for item in recovered.values():
    data = (landing / item["payload"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == item["sha256"]
extract(master_revision)
extract(source_revision, tracked)
for name, item in recovered.items():
    target = destination / name
    assert not target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((landing / item["payload"]).read_bytes())
bridge = destination / "tools/spec-checks/src/lib.rs"
bridge.write_bytes(bridge.read_bytes() + b"\n" +
                   (landing / "lib-rs-additions.rs").read_bytes())
registry = json.loads(
    (destination / "knowledge/gates/spec-check-exceptions.json").read_text())
assert len(registry["exceptions"]) == 7
registry["exceptions"].extend(
    json.loads((landing / "proposed-exceptions.json").read_text()))
registry["approved_by"] = "NOT APPROVED: disposable staging simulation"
registry["approval"] = "B10 proposals still require explicit outer adoption"
(destination / "proposed-registry.json").write_text(
    json.dumps(registry, indent=2) + "\n")
PY
export WORKSPACES="$(dirname "$SOURCE_WT")"
export CARGO_TARGET_DIR="$DEST-cargo"
export CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc

# Control: expected exit 1 with the unchanged seven-entry master registry.
python3 "$DEST/scripts/lab/spec_checks.py"
# Conditional staging gate: expected exit 0, NOT nine passing acceptances.
python3 "$DEST/scripts/lab/spec_checks.py" \
  --exceptions "$DEST/proposed-registry.json"
```

Do not add shell `set -e` across the expected failing control command. Do not
promote the tested export wholesale: import the pinned blobs and recovered
payloads into a separately checked destination. The original test helpers can
write diagnostic evidence; the recorded run's post-test audit found **zero**
changed imported blobs and preserved all **6,582** original master files except
the exact lib.rs append. The real registry and build scripts stayed unchanged.

For the real landing, use the same collision checks and payload map, append the
bridges, insert the README rows below, and merge the two registry entries **only
after outer approval**. Stage only listed payload and handoff paths, not a broad
branch merge or `git add .`. The eight destination `*.so.exports.txt` paths
need `git add -f` because of the existing ignore rule. Keep the recovered
payloads in this handoff for independent verification.

## Root README Layout rows

Insert only absent rows into the existing Layout table; do not replace README.
The comparison truth is a single dependency file, not a full imported benchmark,
so it intentionally has no new standalone Layout claim.

```markdown
| **`benchmark/2026-10-01-b10-landing/`** | **Pinned additive B10 import: 2,659 paths, 31 lib.rs bridges plus three native selectors, eight recovered frozen inputs, and an explicit two-exception staging gate.** |
| **`benchmark/2026-09-29-static-wall-prediction/`** | **B10 v3: AOSP JNI ownership, 134 startup risk rows, 32-APK class availability, task85 five-family detectors and frozen/fatal backtests; task90 66-key r15c successor, dual-layer network shortlist, full-batch evaluator and 224-row feedback scan; native NOLOAD/JNI initialization-order rules with four source replays; unresolved methods keep the gate closed.** |
| **`benchmark/2026-09-30-v2-scanner-feedback/`** | **Post-v2 B10 secondary-Activity and boot-provider detectors, 66-key calibration, and runtime-only EGL discriminator; frozen forecasts preserved.** |
| **`benchmark/2026-09-30-r16-prospective/`** | **Frozen 66-key r16 lighting/first-wall forecasts, immutable scoring policy, and separate outcome-blind/pre-click evaluation.** |
| **`benchmark/2026-09-30-r16-feedback/`** | **Post-r16 eight-family service/provider/JNI requirement scan: 32 APKs, 256 rows, no retrospective score inflation.** |
| **`benchmark/2026-09-30-r17op-execution-revision/`** | **Separate hwui rollback notice and actual-fingerprint strata; changed native components and unforecast JARs excluded from v3 same-profile scoring.** |
| **`benchmark/2026-09-30-r17op-prospective/`** | **Frozen v3 66-key r17o/r17p paired forecasts, exact 5ea hwui/installer profile and evidence-gated per-JAR scoring.** |
| **`benchmark/2026-09-30-v3c-r17j-prospective/`** | **Frozen v2 66-key forecast for exact v3c/r17j/installer inputs, with board-specific future scoring.** |
| **`benchmark/2026-09-30-background-start-prospective/`** | **Frozen 66-key background-Activity permission forecast, DEX transition witnesses and evidence-gated prospective scoring.** |
```

## Validation boundary

| Run | Passed | Failed | Excepted | Unexpected | Wrapper exit |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initial incomplete dependency overlay | 51 | 10 | 7 | 3 | 1 |
| Complete additive overlay, original registry | 54 | 9 | 7 | 2 | 1 |
| Same overlay, proposed registry via --exceptions | 54 | 9 | 9 | 0 | 0 |

All full runs used unfiltered `cargo test --no-fail-fast` through
`scripts/lab/spec_checks.py`; original Cargo exit was 101 in all three.
The landing contract lint is 100%; lifecycle and explain against the temporary
master's `tools/spec-checks` give **3 pass, 0 fail, 0 skip**.
The README extraction recipe was independently rerun in a second fresh export:
again 54 pass, nine fail, nine excepted, wrapper exit 0. The repository known-answer
suite also passes: 69 run, two skipped, zero failures (see `evidence/known-answer.log`).

This is **verified on this lab host**, not a hermetic fresh-clone claim. Existing
scans/tests still depend on local generation packages
`westlake-generation-6cb40cd6` and `westlake-generation-v3-74d1d6d4`, the r8
runtime overlay, Android build-tools/dexdump, AOSP source snapshots and original
absolute-path fixture pins. The lab environment supplies Python dependencies.
Moving to a host without those artifacts can add infrastructure failures; do
not subtract them under these two exceptions. No board operation, runtime build,
shared master write or push was performed.
