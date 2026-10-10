# 5cd SELinux icon-click A/B

The earlier 89-key Enforcing preview cannot be resumed across reboot: the board returned with boot `707ef9d2-038c-48e1-8036-f0d9e50eb5c2`, not `900dd8cf-a384-4693-bb02-77b26c234636`. The 39 unmeasured keys remain unmeasured. This is a separately authorized observation, not continuation or promotion.

Outer authorized the 26 suspect keys under both modes on 5cd: Enforcing → Permissive → restored Enforcing, at most 45 minutes. Both modes use the same pinned 128-app manifest/install receipts and historical screenshot tiers, the same demo adapter/master BMS launcher, and exact desktop icon clicks. No ability fallback, reinstall, sandbox repair, installer, reboot or runtime swap is performed. Existing BMS logging/capture preflight and exact-UID cold stop are retained.

`--launch-only` in the existing BMS runner still calls sandbox preparation and native sidecar assembly. `batch_readonly_prep.py` replaces only those two mutation steps with `not_modified` receipts for this experiment; all icon lookup/input, collection and cleanup functions are unchanged. This honors the explicit no-sandbox-change condition, rather than treating `--launch-only` as proof of no preparation writes. Known-answer tests verify those overrides issue no board call.

`driver.py` is a detached Mac coordinator using explicit VM HDC and `mac board_note.sh` lock forwarding. Its initial identity check allows the explicitly observed init ondemand parent to be absent while still requiring all 319 bytes, both U13 fingerprints, and the exact new boot. After the first launch, final identity requires the normal parent-present gate. Restore `setenforce 1` and readback execute in `finally`; failed restoration/identity retains the lock. The first attempt (`window1/`) stopped before app launch or mode change because the VM lock query looked in the wrong home. Its zero-write evidence is preserved; the corrected experiment is `window2/`.

`readout.py` assembles separate raw facts and last-scheduled-shot contact sheets, plus `comparison.json`/`.tsv`. CANTOPEN counts are log-line occurrences, not distinct failures. Target PID attribution uses recorded PIDs and exact-package AppMS spawn evidence; zero with no spawn/log is unknown, not successful database opening. Handled MUSL-SIGCHAIN SIGSEGV lines are excluded from first-fatal classification. Each row also reports raw `already existed in array` hits, target-package hits and original lines, to expose repeated-launch WMS-session artifacts separately from database exceptions. No screenshot lighting verdict is emitted.

The order is not randomized. Repeated package/window lifecycles can retain OH WMS sessions; the separately collected 61b window6 documents that spawn can complete without app content appearing. Consequently the raw launch chain, CANTOPEN and screenshot evidence must be evaluated separately. No session repair or reboot is introduced into this experiment.

Large run directories, screenshots and raw hilog stay at the persistent workspace path; the compact readout, source and tests are handed off separately. The result and restoration receipt will be reported after the window closes.

## User steering at 18:55

The first ten completed Permissive keys are published immediately by `intermediate.py`: completion-time order, raw facts, last-slot contact sheet, raw/target CANTOPEN and WMS counts. Two known-answer tests cover nine finished plus one in-flight (no report), and first-ten selection from eleven completed records. The remaining VM capture continues during publication.

The user superseded the earlier UNLOCK instruction: restore Enforcing and the 319-member baseline, **retain the same cx-t0 lock**, then execute the installer-free Boat layer checklist and full demo regression. The paused original host coordinator was replaced only after its live VM shard finished; no app capture or device process was interrupted. Resume accepts only fully wrapped existing groups, keeps the original 45-minute deadline, and does not replay completed Enforcing samples. A resume preflight initially reused an existing output directory and printed `fresh output required`; it did not write the board. The current source uses a fresh `resume-identity` directory. Each subsequent Board operation still verifies the exact lane and boot.

The full A/B report and raw record paths must state any keys omitted by the bounded cutoff as unknown; no count is inferred from the requested list. All screenshot lighting judgments remain outer-owned.

## Closed bounded observation

`results.json` records **26 Enforcing and 21 Permissive completed records**, not 52 results and not a lighting count. Five Permissive keys were not started before the bounded cutoff; they remain unknown. Raw facts total 52/52 and 42/42 captured screenshots respectively. Target-PID CANTOPEN appears for 25 Enforcing keys and zero of the 21 completed Permissive keys. This is a log observation, not proof that every database operation succeeded. The per-key first-fatal and raw/target WMS-session counts are in `window2-readout/comparison.json` and `.tsv`.

`restoration/final319.json` proves 319 targets with `diff={}`, unchanged boot, runtime `452447a4a0ba` and boot-image `ee927db88a67`; `enforce-readback.txt` reads `1`. The user explicitly retained the lock for the following Boat task. `raw-evidence-index.json` pins the persistent original records, logs, process tables and screenshots. The two complete contact sheets remain outer-reviewed evidence. Mac and VM known-answer runs each passed six tests; no images are machine-signed as lit.
