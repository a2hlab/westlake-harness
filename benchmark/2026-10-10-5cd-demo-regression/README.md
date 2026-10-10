# Enforcing demo regression on 5cd

The t4 driver, identity hook, t3 adapter and supervisor previously assumed 61b. Changing only the top-level CLI would either reject 5cd downstream or silently inspect 61b. This change propagates an exact, three-board whitelist through the entire selected-board path; the default remains 61b. Identity assertions remain unchanged.

## Before any write

Read-only evidence `pre-lock-identity/identity.json`: 319 identities, empty diff, runtime `452447a4a0ba`, boot image `ee927db88a67`, init-owned parent PID 3858. Board boot: `900dd8cf-a384-4693-bb02-77b26c234636`; SELinux enforce readback: 1. `bundles-before.txt` and `inventory.json` establish 103 selected packages present and 25 absent.

Only the 25 absent APKs are installed using t3 `batch_adapter.install_one`: resolve pinned input, stage/read SHA, `bm install -r`, BMS readback, cold-stop. No runtime, label, service configuration, autostart, reboot or experimental overlay change is authorized. Existing installed APK bytes are not claimed to have been independently verified: their index records package presence and the resolved canonical input SHA separately from an installation receipt.

Toutiao and BoatAttack special slots remain disabled. Ordinary captures use the pinned shot tiers (121 ten-second, 7 twenty-second). Each board window is bounded by 45 minutes, with no new key after minute 35. Windows release the board after unchanged U13 identity readback.

## Verification

`tests-mac.txt` / `tests-vm.txt`: 14 comparator/driver tests, including selected serial propagation, unchanged default and rejecting an unlisted serial before filesystem/device work. `adapter-tests.txt` / `adapter-tests-vm.txt`: 10 adapter/supervisor tests, including no launch after failed installation, no uninstall/reinstall during captures, and exact ability fallback.

The comparator retains byte/fact `same/changed/missing` evidence and separately reports `same_class/suspect/missing` triage. Its changed contact sheet now contains **only suspect** images: a match to the outer-confirmed launcher body, or a nearly pure black/white body. Status/navigation bars are excluded, RGB is downsampled to 32×48, launcher mean absolute error is at most 22/255, and blank pixels cover at least 98%. These deliberately conservative thresholds can over-report. `same_class` is not a lighting verdict; an app may still show unrelated/error content, and other launcher wallpapers are not covered. Decode/reference/tool failure is suspect. No app-key whitelist participates.

Known answer `preview-01`: byte differences remain 9/9, semantic triage is 7 same_class / 2 suspect, and the sheet contains only LibreSudoku and Minesweeper, matching the outer readout. `launcher-body-reference.json` contains the tiny RGB reference and source SHA, not an inferred screenshot. Mac semantic suite: 17 tests OK; VM tooling/readback is recorded separately. The two suspected Enforcing regressions remain unconfirmed until their authorized post-full-run retries and first-fatal/AVC capture.

## Evidence / commands

Installation: `install-plan.json`, `install-window/runner/` (detached demo supervisor; APK-only mode).

Full capture preparation and final comparison are recorded below once the selected-board install receipts are available. Raw screenshots and logs remain in this workspace; no large binary evidence is committed.

## Initial single-key window and continuation

The initial two 64-key plans use the original driver unchanged after serial propagation. Live single-key invocations cost about 110 seconds between completed records. The existing 35-minute cutoff therefore determines the actual first-window prefix; no live plan is edited. `prepare_remaining.py` consumes only finished regular-shard records from safely finalized prior windows, schedules only the remaining canonical keys, and groups them by identical input root and exact shot tier. It uses the existing supervisor and adapter, preserving installation receipts, ability pins, screenshots and U13 hooks. A fresh aggregate is created after all canonical keys have finished; partial evidence is retained.

The first installation attempt failed before staging an APK because my generated manifest omitted the mandatory `phase` field. Its clean `before_unlock` result remains under `install-window/`. The second attempt uses the original `prepare_t3.plans()` normalization and successfully installed all 25 absent packages, with unchanged 319 identity readback.

The existing supervisor has a batch cutoff, but still invokes later single-key shards after it. `batch_adapter.py` now checks the cutoff before input loading or any device preflight: expired calls return without board access, leaving keys unknown. Known-answer test asserts neither `load_apps` nor the device batch runs. The first capture window finalized 20 regular keys / 40 captures with unchanged 319 identities. Tool changes are bound in a **fresh** continuation round; the original dispatched round and its source bindings are retained, not silently rewritten.
