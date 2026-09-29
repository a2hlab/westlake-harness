# OH6.1 BMS batch runner — items 20 / 57

The earlier one-off runners duplicated reinstall, log capture and screenshot logic, lost x/noice when the manifest package was null, and could collide with a pre-created app directory. These capabilities now use **one `bms_batch.py` entry point**, retaining the master launcher/sandbox/identity gates. This revision was developed and tested offline: **50 FakeBoard tests**, no device execution. Sources and preserved master baseline are recorded in [task57-source-baseline.json](task57-source-baseline.json).

## Usage

Offline plan (no HDC, lock, OrbStack, subprocess or APK reads):

```sh
python3 benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py \
  --keys x,noice --reinstall --hilog 15 --shots 5,20 --focus-check
```

Execution recipe for the assigned lane **after it owns the full serial's lock and has accepted the OH6.1 R130+R155 baseline**:

```sh
BATCH="$(pwd)/benchmark/2026-09-28-bms-route-deploy/batch"
RUN="bms-$(date +%Y%m%dT%H%M%S)"
orb -m a2hlab bash "$BATCH/run-batch.sh" \
  --execute --serial 5ea34a4500000000000000001123012c --lane cx-t0 \
  --run-id "$RUN" --out /tmp/bms-batch-runs \
  --keys aegis,wikipedia --reinstall --hilog 15 --shots 5,20 --focus-check
```

This is an unexecuted recipe. Use the merged master copy after outer-loop review/commit. The Mac path is shared into the VM; inputs default to VM `~/a2hlab/app-inputs`. `BMS_TOOLS` can override the sibling `westlake-inputs/tools` location. The wrapper passes `hdc_mac.sh` and `mac board_note.sh`; all options reach `bms_batch.py`. The runner never acquires, borrows or releases another lane's lock.

| Parameter | Default | Behavior |
|---|---|---|
| `--execute` | off | Enables device operations; otherwise prints the manifest selection and options only. |
| `--manifest PATH` | sibling apps.json | Frozen 66-key corpus. |
| `--phase all/controls/blocked/tail` | all | Selects cohort while preserving phase order. |
| `--keys a,b` | all selected | Unique keys; aliases remain separate records. |
| `--input-root PATH` | ~/a2hlab/app-inputs | Reads `<key>/app-input.json` and hash-matched original APK bytes at execution. |
| `--serial SERIAL` | required for execution | One of the three full campaign serials; no prefix matching. |
| `--lane NAME` | required for execution | Must match the current lock holder before every device command. |
| `--out PATH`, `--run-id ID` | explicit out, generated ID | Fresh `<out>/<run-id>/<serial>`; app directories are created before any per-app output. |
| `--wait SECONDS` | 15 | Final process observation offset, finite 3–300 seconds. Legacy screenshots remain t+3 and t+wait unless `--shots` is set. |
| `--reinstall` | off | Query installed target, cold-stop its identified UID, uninstall it, then install original APK. An explicitly absent target skips uninstall. Unknown query/uninstall failure fails that app. |
| `--hilog [SECONDS]` | off | Snapshot fault filenames and `hilog -r` before launch; at the given offset, `hilog -x` to a unique remote file, receive it and newly named faultlog files. Bare `--hilog` uses `--wait`. Offset must be finite, >0 and ≤300. |
| `--shots 5,20` | legacy t3/final | 1–32 strictly increasing unique finite offsets in (0,300]; enables strict focus checking before **each** requested image. |
| `--focus-check` | off | Also requires target focus for every legacy/default screenshot. Does not weaken the mandatory launcher focus gate. |
| `--hdc-cmd`, `--lock-cmd` | hdc, campaign board_note.sh | Command prefixes, normally supplied by run-batch.sh inside the VM. |

All offsets are measured from completion of the desktop click, using a monotonic clock. HDC/guard latency can make a capture late; both requested and actual offsets are recorded. The batch waits through the latest requested screenshot, diagnostic or final observation before stopping the app. It does not sleep each full offset successively. `--reinstall` intentionally uninstalls the selected package; it is only enabled by that explicit option.

## Per-app behavior and evidence

1. Create the app directory with `exist_ok=True` before writing anything. An existing **empty** directory is supported; nonempty evidence is refused, and the run root must be fresh. Resolve `application.package` and `apk_sha256` from app-input before any device access, so null manifest packages such as x/noice work in reinstall as well as install. Validate fixed pins and find the unchanged original APK by SHA-256; missing/mismatched input fails locally. Shell identifiers are validated/quoted. The corpus is read-only.
2. Send the original APK and verify its remote hash. With `--reinstall`, require a valid BMS target or an explicit absence response; an installed target is cold-stopped by its observed UID before `bm uninstall -n`. Preserve query, uninstall and install text/return codes. **rc=0 alone never passes:** both operations require their positive `install/uninstall bundle successfully` receipt without error/failure text. Post-install `bm dump` must identify the package; an old bundle record cannot override an install error.
3. Cold-stop only that package. Any surviving child must match a unique root appspawn-x parent and the target UID/name; recheck kernel UID/PPID before targeted kill. Run the already accepted master `prepare_sandbox.sh` recipe and retain command/hash/return receipt. Its body is unchanged; failure prohibits launch. BMS entry-module `mainAbility` overrides stale direct-launch activities, including aliases/nested Java class names.
4. The launcher gate wakes/Home and verifies the focused WMS PID is SceneBoard. Unknown/missing focus rows get at most three attempts; an identified foreign owner stops immediately. Search bounded desktop pages for one visible/enabled/clickable exact package/activity icon. No `aa start` fallback or hardcoded icon coordinates.
5. Before every screenshot, wake the display and refresh target-UID process IDs plus WMS focus. WMS row parsing accepts names with spaces and negative Z order; missing/ambiguous/unknown owner is unconfirmed. With `--shots` or `--focus-check`, failed ownership saves a **rejected probe and takes no image** at that offset; later offsets still run. A live process or focus merely leaving the desktop is insufficient. Default legacy collection still records ownership for each shot, with final focus determining collection status.
6. Capture to a fresh per-run path; verify remote SHA, local JPEG magic and matching received hash. A **36627-byte known black frame** is retained with `known_black_frame: true`, `accepted: false`, and `capture_rejected` status. Other sizes are **not proof of a non-black image**; visual verdict remains `pending_review`. Capture rejection never becomes a LIT result.
7. With `--hilog`, retain `hilog-reset.txt`, `hilog.txt`, `diagnostics.json`, fault listings before/after, and `faultlogs/<new-name>` plus hashes. Only names absent before launch are pulled. Faults are from the board-wide interval; no automatic causal attribution to the target app. Overwritten existing fault filenames are outside this new-file comparison. A capture/app error attempts available diagnostics before cleanup; lock/boot/transport loss performs no speculative cleanup or further writes.
8. Stop the target after evidence collection; cleanup uncertainty stops the batch. Per-app errors retain records and continue; batch identity/transport failures retain `not_run` keys and stop. Boot ID, full serial and lock holder are checked before every shell/send/receive. Empty rc=0 lock/target output gets one bounded retry, while a different holder/serial or changed boot is refused.

Files include `record.json`, install/uninstall receipts, bundle JSON, `sandbox-*`, per-shot `processes-<tag>.txt` and `windows-<tag>.txt`, images, diagnostics, run-level `summary.json` and raw command stdout/stderr. A rejected focus probe has `captured: false` without an image path. Screenshot records retain focus window ID/PID, observed app PIDs, scheduled/actual time, hash/size and acceptance separate from visual review.

Exit status: `0` means collection gates passed; `1` means app failure, rejected image or unconfirmed foreground; `2` means batch identity/transport refusal. **None means LIT.** Real screenshot review is still required. No runtime deployment, installer-library swap or ROM changes are implemented by this task.

## Corpus and source lineage

The manifest has **66 keys: 13 controls, 43 blocked, 10 tail**. `x` and `noice` have no guessed package/hash; execution resolves actual app-input. Multiple copies with identical APK bytes are interchangeable. Split inputs are recorded as `split_hint`; this remains a single-original-APK install route, not a split merge/repack/signing tool. The original source derivation and pins remain in [sources.json](sources.json).

Master `a5259c0e` provides alias selection, sandbox preparation, launcher gating and lock empty-output retry. #38 `rerun956_61b.py` supplies reinstall/output adjudication lessons; #48 `probe_unknown22.py` supplies per-app log timing; #51 `alive16_shots.py` supplies multiple capture times and WMS rows with spaces. Its weak fallback (process alive and focus left SceneBoard) was **not** carried into strict ownership checks. No one-off runner is executed or extended here. `capture_existing.py` is the unchanged master compatibility helper needed by the inherited regression tests.

## Offline verification

```sh
python3 -m unittest discover \
  -s benchmark/2026-09-28-bms-route-deploy/batch -p 'test_bms_batch.py' -v
cargo test --manifest-path tools/spec-checks/Cargo.toml bms_batch_offline
```

`test_bms_batch.py` uses FakeBoard transport, synthetic APK/JPEG/log bytes and a fake monotonic clock. It covers positive/negative install text, missing inputs/packages, reinstall ordering, empty/stale directories, exact aliases, sandbox failure, screenshot timing and per-shot focus, known-black rejection, new-fault selection, mid-diagnostics detach, lock/boot checks, bounded retries and malformed CLI timing. Results and lifecycle evidence: `task57-results.json`, `task57-tests.log`, `task57-lifecycle.json`. R2: offline behavior **verified**; real device timing/diagnostic availability and on-screen result **unverified**. Outer loop owns commit; no commit or push is performed by this lane.

## B4 three-board rerun preparation (#59)

See [b4-rerun-plan.md](b4-rerun-plan.md) for the 22/22/22 shard commands, explicit artifact directories and current-round v4 aggregation. [b4-rerun-shards.json](b4-rerun-shards.json) pins the accepted runner and full 66-key coverage; `b4_rerun.py plan` is offline only. FakeBoard results are labeled synthetic, with no real v4 outcomes claimed.
