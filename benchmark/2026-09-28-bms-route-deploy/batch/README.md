> Execution-lane adaptation for item 23: the original preparation notes follow below.
> The execution copy selects the BMS entry-module `mainAbility` (including Java nested-class names)
> instead of assuming the historical direct activity is the desktop alias. Three-board evidence
> and retained failed attempts live in the parent directory. `capture_existing.py` supplements
> missed captures only after matching a prior successful installation receipt and the current
> installed original-APK hash; it never reinstalls or relabels a failed reinstall successful.
> Current offline checks: 25 passing tests. Screenshot verdicts remain external.

# OH6.1 BMS batch runner — item 20

**Prepared offline; no board execution.** This runner consumes the R130+R155 baseline supplied by item 19. It installs original APK bytes through BMS, opens the exact SceneBoard icon, records foreground observations, and captures screenshots for the outer reviewer's visual verdict. It does not deploy a runtime or use the superseded T006/OH7 payload.

The old shortcut “install returned success / process alive = lit” is not accepted here. Each stage has separate evidence and screenshots always retain `pending_review`. Source precedent: `~/t006/t006_baseline.py:645-655,704-737`; R151D capture script `:42-60,63-83,85-136` (full identities in [sources.json](sources.json)).

## One command after item 19 is accepted

The execution lane must already own the exact board lock and have accepted item 19's baseline. Run from the Mac; the absolute worktree path is shared into the VM, while the APK inputs remain in the VM. Replace `BATCH` with this directory and `RUN` with a fresh run ID. The wrapper locates sibling `westlake-inputs/tools`; override `BMS_TOOLS` if needed.

```sh
BATCH="$(pwd)/benchmark/2026-09-28-bms-route-deploy/batch"
RUN="bms-$(date +%Y%m%dT%H%M%S)"
orb -m a2hlab bash "$BATCH/run-batch.sh" \
  --execute --serial 5ea34a4500000000000000001123012c --lane cx-t0 \
  --run-id "$RUN" --out /tmp/bms-batch-runs
```

This is an **unexecuted run recipe**. It uses VM `~/a2hlab/app-inputs/<key>/app-input.json`, Mac-forwarded `hdc_mac.sh`, and `mac board_note.sh held <serial>`. Output is on the VM under the supplied output root. Use an absolute VM output path when invoking from an uncertain working directory. For the first assigned canary pass, append `--keys aegis,wikipedia`; for separate cohorts use `--phase controls`, `blocked`, or `tail`. Entries retain manifest phase order even when `--keys` is supplied in another order. No extra confirmation prompt is introduced.

The executor acquires/releases its lock with the existing campaign `board_note.sh`; this script verifies the invoking `--lane` before every device command and never borrows or releases another lane's lock. It accepts the campaign's three full serials only. A missing lock, detached serial, changed boot ID or lost remote status marker stops the batch before later writes. A wrong OH version stops before APK installation. Missing R130 files/socket/observed runtime hashes are captured as read-only baseline evidence; **that record does not replace item 19's acceptance**.

## Offline plan and checks

```sh
python3 benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py
python3 -m unittest discover -s benchmark/2026-09-28-bms-route-deploy/batch -p 'test_*.py' -v
cargo test --manifest-path tools/spec-checks/Cargo.toml bms_batch_offline
```

Without `--execute`, planning reads only `apps.json` and does not call HDC, OrbStack, locks or subprocesses. These checks were run here with synthetic transport/APK/JPEG fixtures. Real VM metadata access was attempted once but OrbStack timed out starting the VM; consequently this task does not claim real-input parsing or a live desktop result.

## Manifest and identity

`apps.json` contains **66 distinct keys in launch order: 13 historical lit controls, 43 historical blocked, 10 tail**. The first 56 identities derive from the fixed T0 manifest. Tail order derives from the old 66-key file. Eight tail package/APK hashes are available from the input lock; **`x` and `noice` remain explicitly unresolved until their actual `app-input.json` is read**. No packages or hashes are guessed. All 66 get separate records; aliases such as noice/fd-noice and the burgerking label anomaly are not merged. Sources and SHA-256 pins are in `sources.json`.

Before a device write for an app, the runner reads `application.package`, `apk_sha256`, and optional `application.launch_activity`, verifies any fixed package/hash, and finds the unchanged `.apk` by its actual SHA-256. It also supports top-level `apk`, `apk_path`, and `source_apk` string paths. Multiple copies with identical bytes are interchangeable; it picks a deterministic path. It records current app-input metadata hash rather than demanding the old T0 metadata hash, since launch configuration may change while APK bytes stay fixed. Missing or mismatched APKs fail that app before device access.

The command is the requested **single-APK** `bm install -p`. No repack/resign or merged split APK is produced. Multi-APK inputs are recorded (`apk_candidates`, `split_hint`); base-only installation can therefore fail or lack split resources/native libraries. Treat that as a reported limitation for the later deployment lane, not a solved split-install route. The original corpus remains read-only.

## Per-app sequence and output

1. Create a fresh local `<out>/<run-id>/<serial>/<key>/` and unique device directory. Transfer the hash-matched APK, check its device readback, run `bm install -p`, preserve remote return code and output. Remove only this runner's transferred temporary APK after the install command returns.
2. Run `bm dump -n <package>`, preserve raw JSON/output, confirm package identity and derive a unique UID from BMS. A previous BMS record alone cannot override a failed installer result.
3. Cold-stop only this package (`aa force-stop`). If a child remains, require the unique root/PPID1 appspawn-x parent, the observed BMS UID and matching child parent/name before terminating it. Recheck UID/PPID immediately before the targeted kill. No broad appspawn kill, hardcoded app UID, data clear or uninstall. If cold state cannot be verified, retain failure and move on.
4. Wake, Home, dump UI hierarchy, handle the known USB dialog/unlock screen, then search bounded desktop pages in both directions. Click only one actionable SceneBoard node whose ID exactly matches `AppIconCommonView_<package>.<activity>`. If activity is absent, require a unique exact package-prefix icon. Ambiguous/invisible/missing icons fail explicitly. There is **no `aa start` fallback**. The bounds are read from hierarchy; no fixed screen coordinates are borrowed.
5. Capture one early JPEG and one final JPEG (default final wait at least 15 seconds after click; command latency can extend it). Every capture removes only its unique destination first, requires successful `snapshot_display`, records device stat/hash, receives into a nonexistent local path, checks JPEG magic and byte hash. Save process table and WMS dump; foreground is confirmed only when its focused window PID belongs to the observed target UID. Neither that confirmation nor a valid JPEG is a visual light-up verdict.
6. Stop only the collected package after the successful path; retain installed apps and evidence for review. App failures are recorded and the batch continues. Transport/lock/boot failures stop it, save remaining keys as `not_run`, and perform no speculative cleanup writes. Before the next app, a known installed UID is cold-stopped again and verified; cleanup uncertainty stops the batch for inspection.

`record.json` includes key, phase, serial/boot ID, package, original APK hash, input metadata hash, installer return/text path, BMS query result/UID, launch method, selected icon/click, cold-stop result, observed PIDs, foreground evidence, screenshot paths/hashes and `review: pending_review`. `summary.json` retains completed/failed records and unattempted keys. `commands/` saves intended argv plus raw stdout/stderr and exit status. Unique run IDs and local `exist_ok=False` prevent overwriting evidence. Device staging/screenshot files remain under this run's namespace; cleanup or uninstallation is intentionally an operator decision after review.

Exit status: `0` means the selected entries reached collection with foreground confirmation; **it does not mean LIT**. `1` means at least one app failed or foreground remained unconfirmed. `2` means the batch was interrupted/refused by identity/transport checks. No image-based auto-classification is implemented.

## Source adaptations and limits

- Installation provenance: `~/workspace/hanbin_adapter/memory/project_bm_install_progress.md:12-29` describes the `.apk` BMS branch. Its April 2026 ARM32 paths, permissive SELinux and chmod workarounds are historical and are **not copied**.
- Exact icon selector/desktop settling: `00.Workspace/tests/instrumentation/cts_entry_launch.py:24-178`. Adapted locally to avoid importing its deployment/CTS machinery; added bounded multi-page search. No OH7 fullname/BCP admission rules were copied.
- Cold-start identity and recording: `01.OH61AOSP16/real-work/.state/zigzag-longtask-r6i-r151d-device-stage/run-r151d.sh:63-83,85-136`. Target UID is derived from BMS, and its `aa start` is replaced by the requested SceneBoard click. Global hilog reset/privacy toggles and automatic game touches are not needed for this batch.
- Screen timeout is not changed; wake is repeated at UI/capture boundaries. A lock-screen image still remains possible and requires human review. Native app errors, dialogs, split loading and aliases remain measured outcomes.

R2: **verified** offline tests/manifest shape; **unverified** real-board installation, foreground matching, visual success and OH6.1 launcher layout compatibility. The old T006 driver is a source reference only. No real device command was executed during preparation.

Validation: 19 offline tests passed; known-answer suite 69 ran / 2 skipped / 0 failed; agent-spec lint score 100%, lifecycle 2 pass / 0 fail; Bash syntax and default offline-plan checks passed. These are host/synthetic results only. See `results.json` and `lifecycle.json`. The outer reviewer committed the previous #15 report as `637afe4`; #20 remains a separate change set.

Local staging/commit is blocked in this sandbox: creation of the parent repository Git `index.lock` returns `Operation not permitted`. #20 files are ready in this worktree for the outer reviewer to stage and commit; no #20 commit hash is claimed and nothing was pushed.

## Post-install sandbox preparation (B1)

`prepare_sandbox.sh` preserves HelloWorld restore lines 291–294 exactly and takes package/UID parameters. Both fresh installation and `capture_existing.py` run it after BMS identity/cold-stop checks and before clicking. Failure is `sandbox_prep_failed`, with command, return code and output retained. See [intervention report](../sandbox-prep/README.md): preparation fixes the stock sandbox failure, but Wikipedia still exits on unresolved DefaultIcon; the broader rerun remains gated.
