# OH 6.1 BMS deployment and 66-key sweep

**66/66 keys have terminal execution records across three boards; 62 keys have a successful original-APK installation receipt and 62 selected records have a desktop click.** Machine outcomes: {'foreground_unconfirmed': 62, 'app_failed': 4}. These are execution outcomes, not a count of apps with visible UI. Every visual verdict remains `pending_review`.

The original desktop selector was wrong for Android launcher aliases: Wikipedia registers `DefaultIcon`, Termux registers `HomeActivity`, and nested Java activity names can contain `$`. The execution copy now uses the unambiguous BMS entry-module `mainAbility`, retaining the historical direct-launch activity separately. APK bytes and the runtime were not changed.

## Evidence and comparison

- [results.json](results.json): exactly 66 keys, assigned full serial, per-key September 27 comparison, all installation attempts, selected record, PID/window observations, image paths and hashes.
- [SCREENSHOTS.md](SCREENSHOTS.md): every archived batch screenshot (126 images), with selected captures and earlier attempts distinguished.
- [BASELINE.md](BASELINE.md) and [baseline-results.json](baseline-results.json): separate HelloWorld + ZigZag three-board evidence and its bounded-stability limitations.
- [Original historical report](historical/README.md): 66 launches, 15 LIT launch records, 13 distinct apps. `burgerking` is a mislabeled McDonald's key; `noice` duplicates `fd-noice`. They remain separate keys rather than being counted as independent app wins.

| Board | Assigned keys | Historical controls | Selected machine outcomes |
|---|---:|---:|---|
| `5ea34a4500000000000000001123012c` | 22 | 5 | {'foreground_unconfirmed': 22} |
| `61b0657200000000000000000324012c` | 22 | 4 | {'foreground_unconfirmed': 19, 'app_failed': 3} |
| `5cd1e3dd00000000000000000923012c` | 22 | 4 | {'foreground_unconfirmed': 21, 'app_failed': 1} |

## Execution and failures

The 66-key manifest was split round-robin in controls → blocked → tail order, 22 keys per board with 5/4/4 controls. All device commands ran through the VM wrapper. Each board held the cx-t0 lock; run IDs include the serial prefix and concurrent starts were staggered by at least two seconds. The copied [batch runner](batch/README.md) checks the lock, full target serial and boot identity before every command. No flashing, new runtime deployment, APK modification, uninstall, or push was performed in this sweep.

Early alias-selection failures and interrupted attempts were retained. Repeating `bm install -p` on already installed packages returned `9568260 install internal error`; those results remain failures in the installation history. The supplementary capture command performs no installation: it requires an exact successful prior receipt and verifies the installed `android/base.apk` SHA against the original input before clicking the BMS entry. Its record names the prior receipt and explicitly has `install: null`.

Occasional `mac held` / `hdc list targets` commands returned exit 0 with empty stdout. The guard stopped immediately. Fresh read-only checks confirmed the real lock and device remained present with unchanged boot identity; a new run ID resumed the remaining keys. No identity guard was weakened, and no board had concurrent app jobs.

Final failure records:

| Key | Failure | Installation / screenshot consequence |
|---|---|---|
| fd-seal | bm dump has no JSON record | Install return/output and BMS readback retained; no selected app screenshot |
| toutiao | bm dump has no JSON record | Install return/output and BMS readback retained; no selected app screenshot |
| subwaysurfers | pinned identity changed: apk_sha256 | Rejected before device installation; original pin retained |
| x | bm dump has no JSON record | Install return/output and BMS readback retained; no selected app screenshot |

For fd-seal, toutiao and x, `bm install` printed `9568260 install internal error` despite process return code 0, and BMS had no JSON bundle record. Subway Surfers failed the frozen APK identity check before installation. Split hints and original inputs remain in the records; no replacement APK was substituted.

cx-t0 visually inspected the selected Aegis, OONI and markor final images: each showed the OH desktop, not app UI. This observation is limited to those three images. The remaining captures require the outer review; neither installed status, a process nor `foreground_unconfirmed` establishes visible UI.

## Verification and reproducibility

[Execution contract](../../specs/bms-route-execution/t1-execute.spec.md) lint score: 100%. Offline runner checks: 25 passed. Negative controls cover wrong serial/package/hash, missing lock, disconnected target, boot change, ambiguous/hidden icon, stale/corrupt screenshot and a mismatched installed APK. Repository known-answer tests: 69 run, 67 passed, 2 skipped.

Run `python3 benchmark/2026-09-28-bms-route-deploy/verify_batch_results.py` to verify all 66 terminal outcomes, shard membership and every archived artifact hash. `agent-spec lifecycle specs/bms-route-execution/t1-execute.spec.md --code tools/spec-checks --format json` provides the final scene verdicts in [checks/lifecycle.json](checks/lifecycle.json). Final lifecycle: alias/identity scenario `pass`; 66-key evidence scenario `pass`; screenshot review scenario `pendingreview` (2 pass, 0 fail, 1 pending review). Screenshot judgment is a human-review scenario, never an automatic LIT assertion.

Raw VM command receipts remain under `/home/zhaoyue/a2hlab/board/bms-batch-runs`; each exported run includes a hash-and-path command provenance index. Original failures and interruptions remain in `runs/` and `results.json`. R2: **partially** — execution and artifact integrity are verified; independent visual acceptance, broad app compatibility and long-duration stability are not established. Local commits only; no push.
