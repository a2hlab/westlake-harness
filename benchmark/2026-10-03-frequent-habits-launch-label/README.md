# Frequent Habits: label vs absent desktop tile

The label-name hypothesis is wrong for this recorded failure. The master runner matches the exact `AppIconCommonView_<package>.<ability>` identifier, not the displayed label. All 20 `icons--1-*.json` / `icons-1-*.json` dumps contain desktop tiles, with 155 distinct icon IDs; none contains `com.frequent.habits` or `Frequent Habits`. The visible `Habits` tile is `org.isoron.uhabits`, a different app. `desktop-icons.json` lists every actual icon ID and label; `results.json` lists labels and counts for each dump and its original SHA.

| Layer | Label / identity | Resource ID |
| --- | --- | --- |
| APK application | Frequent Habits | 0x7f0b0001, nonzero |
| APK launcher activity | com.example.MainActivity, Frequent Habits | 0x7f0b0001, nonzero |
| Recorded BMS launcher ability | com.frequent.habits / com.example.MainActivity, Frequent Habits | labelId 16777219 (0x01000003), nonzero |
| Runner expected tile | AppIconCommonView_com.frequent.habits.com.example.MainActivity | no text-name lookup |
| Other app's visible Habits | org.isoron.uhabits / org.isoron.uhabits.MainActivity | not a substitute |

The APK SHA matches the captured record (`3b6cb468…`). The application and activity use the same label resource, resolved from the APK. BMS marks the ability enabled, visible and launcher-capable. Installer logs write/load `android/icon.png` (1485 bytes), and SceneBoard's launcher ability list contains the correct name. Therefore this is not “installer never wrote an icon” or a zero `labelRes` issue. SceneBoard then reports `getPixelMap is empty: true`, `combinePic is empty`, and `load iconId is invalid`; no usable target tile appears in the recorded desktop pages. The precise placement/cache internals are not established by this offline evidence.

This agrees with the existing DIGEST's 2026-10-01 14:25/14:41 findings: the selected `res/d2.webp` in the original APK is malformed; the installation service wrote it under a PNG name. The present analysis does not reopen the frozen installer or re-infer the old defect from label IDs. The recorded install log and original APK icon header/hash are included as independent evidence.

## Minimal diagnostic plan

`launch-fallback-plan.json` is disabled and proposal-only. After bounded exact icon search fails, an explicit allowlist for this one key may use `aa start -b com.frequent.habits -a com.example.MainActivity`, with the package/unique launcher ability independently checked against pinned APK and BMS metadata. Preserve the original icon failure; record `launch_method=ability-fallback`, actual return code/output and timestamp, and leave `clicked=false`. Keep all lock, identity, cold-stop, capture and recovery rules. Never click the other application's Habits tile or add a text-only label mapping.

This removes one runner blocker and reveals the currently unknown app blocker. It does not repair the desktop icon and changes the launch variable, so future results must be labelled separately. No executable U13 plan, gate, installer or runtime was changed; no device command was issued. The actual icon repair remains the separately reviewed frozen-installer fallback task.

## Reproduce offline

Run `analyze.py` using the lab venv with `--record-dir` pointing to the archived 5ea Frequent Habits record directory, `--runner` pointing to master `bms_batch.py`, and `--out` to a fresh directory. It verifies the pinned APK, parses its binary manifest/resources, inventories all saved layouts and replays the actual `select_icon` function on each. The known answer is 20 dumps / 155 distinct IDs / 0 target-prefix matches / 0 strict-selector matches. Source and input hashes are in `results.json`; raw inputs remain in the preceding long-wait archive.
