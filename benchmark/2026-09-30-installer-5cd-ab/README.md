# 5cd installer / graphics interaction experiment

The proposed deterministic `background installer × graphics 32df` AntennaPod failure did not reproduce: after the accepted installer pair, a recovery reboot, original 32df replay and r17q restoration, AntennaPod still displays its welcome/home page. Its complete captured hilog contains no `NullPointerException` or `J_invokeStaticMain_main_threw`. This observation does not establish a board-specific root cause: compare_runs identifies two cross-board variables, board identity and carried-over application data on the 5ea reference.

## Evidence and constraints

- Exact accepted service bytes copied from the completed 61b transaction (commit 82fc1c00); only serial and transaction directories changed. libbms 6aadb8b4 / libapk_installer 7048c7c5, system and platformsdk copies verified through foundation root/maps.
- Baseline native package is graphics 30f63ef7, runtime 32dfac83, JAR r17q 94424d60. `original.json` captures the actual lock-time two-layer JAR receipt. Same-board comparison: 117 fingerprint paths, only the installer pair changed. Six-package test inputs and launch entries retained where an A record exists.
- Foundation restart caused a black screenshot. Explicit recovery reboot changed boot a42f2d6c → 9192be3a. USB recovered automatically. The exact original package replayed without --upgrade on the new boot; no missing ZigZag prerequisites needed copying. Deployer verified SHA/maps/single ART/bridge, then r17q was restored. Reboot is an experimental covariate, not silently ignored.
- Six keys, master batch, --reinstall --hilog 20 --shots 5,20 --focus-check. All background requests granted; matching later-activation WMS allows for AntennaPod, FileManager and Tusky, zero matching denials. HW/Thunderbird/K9 have no matching later activation observed.
- No arbitrary native or graphics repair in the installer phase. Afterward the user explicitly requested runtime 32df → 9e14 and JAR r17q → r17r, followed by a separate HW smoke. That final phase is not part of the installer A/B.

## Visual observations (outer sign-off pending)

| Key | t20 screenshot | Observation |
|---|---|---|
| helloworld | [t20](evidence/helloworld/t20.jpeg) | Full Hello World lifecycle/actions UI |
| antennapod | [t20](evidence/antennapod/t20.jpeg) | Home welcome, five tabs, no subscriptions |
| fd-android | [t20](evidence/fd-android/t20.jpeg) | Updating database title and status, completion not established |
| fd-k9 | [t20](evidence/fd-k9/t20.jpeg) | Updating database title and status, completion not established |
| fd-tusky | [t20](evidence/fd-tusky/t20.jpeg) | Login form with instance input and explanatory text |
| fd-filemanager | [t20](evidence/fd-filemanager/t20.jpeg) | Search toolbar, three tabs, add button, empty content area |

## Attribution

[compare-same-board.txt](compare-same-board.txt) and [compare-crossboard.txt](compare-crossboard.txt) are unedited output from the current master `scripts/lab/compare_runs.py`. The same-board pair varies reboot and installer. Cross-board references have identical runtime bytes but also differ in application-data preparation. Neither is a single-variable causal proof. A universal deterministic interaction is contradicted by this successful sample; the particular 5ea state remains unresolved. No same-profile outcome flip occurred here, so no unrelated three-run stability batch was added.

## Reproduction, validation and rollback

[HANDOFF.md](HANDOFF.md) gives exact package paths and pair rollback. The original four libraries remain backed up; rollback does not reverse already issued per-package ATM grants. Known-answer tests: 69 run, 2 skipped, OK. No compilation of new native code. Source recipes, manifests, fingerprints, records and screenshots accompany this report; full logs remain under runs on Mac. Flutter's offline two-board missing-dependency observations are retained in flutter-deferred-precheck.json and are not part of this experiment.

## Installer-phase facts (verbatim)

```text
RUNTIME fingerprint=a67405af9c16 files=117 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
antennapod           shots 2/2  alive t5=yes t20=yes  child_hilog=32466  foreground_unconfirmed
fd-android           shots 2/2  alive t5=yes t20=yes  child_hilog=65149  foreground_unconfirmed
fd-filemanager       shots 2/2  alive t5=yes t20=yes  child_hilog=45498  foreground_unconfirmed
fd-k9                shots 2/2  alive t5=yes t20=yes  child_hilog=63482  foreground_unconfirmed
fd-tusky             shots 2/2  alive t5=yes t20=yes  child_hilog=61525  foreground_unconfirmed
helloworld           shots 2/2  alive t5=yes t20=yes  child_hilog=5689  foreground_unconfirmed
TOTAL keys=6 screenshots_captured=12/12 alive_t5=6 alive_t20=6
```

## Final baseline and handoff

5cd released after restoring runtime 9e14bf20, overlay r17r dd4f0eae and retaining the accepted background installer. Final declared package: `/Users/zhaoyue/orca/workspaces/westlake-runtime-return-9e14-5cd`, SHA `668e4f7c74bfe635c57ca7133e1373acb0c675959d5953a20708e70293d27107`. [Final HW t20](final-evidence/helloworld/t20.jpeg) shows the full UI. This verifies 5cd only; no assertion about the other boards' live state.

```text
RUNTIME fingerprint=0aa9f6ecf29e files=117 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
helloworld           shots 2/2  alive t5=yes t20=yes  child_hilog=5858  foreground_unconfirmed
TOTAL keys=1 screenshots_captured=2/2 alive_t5=1 alive_t20=1
```
