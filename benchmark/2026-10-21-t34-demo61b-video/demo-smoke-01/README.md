# T34 normal-icon demo smoke selector

The old smoke card guessed EntryAbility for both apps, while the actual 61b desktop records select the Android activity names. The original ui-01 CLI also launches only imehost. This successor changes **only two source locations**: a required `--app` whitelist and the dictionary passed to the existing `desktop_launch` call. Original functions (including GuardedBoard, Budget, UI power envelope and screenshot observation) are byte-identical. Old ui-01 is unchanged.

- `boatattack`: `com.Unity3d.BoatAttackDay` / `com.unity3d.player.UnityPlayerActivity`.
- `libresudoku`: `com.kaajjo.libresudoku` / `com.kaajjo.libresudoku.MainActivity`.

The old coordinates are not reused. The existing BMS helper selects the full icon identifier from the current layout, wakes the device and bounds page search. The original guarded board restores override86400000 after each UITest. Actual current serial/boot/holder/start are still mandatory. The window start is never reset; this package does not create a lock or admission. Keep the same 1200-second experiment/1800-second recovery limits.

Example for the already authorized current window (values must be its actual fresh inputs):

```sh
python3 "$REPO/benchmark/2026-10-21-t34-demo61b-video/demo-smoke-01/ui.py" \
  --app boatattack --repo "$REPO" --window "$W05_UI" --session "$FRESH_SESSION" \
  --tag boat-smoke --observe-seconds 20 launch
# Same command with --app libresudoku and a new --tag sudoku-smoke.
```

All original action modes remain; `--app` is mandatory, including capture/back/power. It selects only launch, not a new lifecycle. Do not use Android activity names in aa start. The normal icon must be found in fresh layout. This is first-screen smoke, not completed racing/gameplay/functionality or audio acceptance. Every screenshot remains pending human review; rc0 is not a lit verdict. Failure preserves receipts and does not retry automatically. No device action was performed for this delivery.

Actual host checks: original 8 cases plus 3 new cases pass. New tests execute the real main parser/pin checks/branch with offline board/observation seams, assert both exact dictionaries reach desktop_launch, check invalid/missing app fails before board construction, and compare all non-main functions byte-for-byte to the donor. The original suite independently exercises real GuardedBoard/BMS marker and local shell envelope with mocked transport. These tests do not simulate live UI success.

61b references: Boat actual selected_icon is in `benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final61b-game-086d/run/record.json`; the accepted continuation image is `.../final61b-game-resume-086d/run/final.jpeg` (SHA074534ec6cab8a415597f35ee794391a84a8749211828dc9530c2a58b0350508). LibreSudoku actual record/image are referenced by `benchmark/2026-10-14-final61b-full128-peer/startup-demo-recommendations.json` rows[0], t10 image SHAb0a05e3909f8bacc160fd80f82c0ec814430992f05d77918ad791a7101bf1f95. Both are historical 61b evidence, not new W05 acceptance.
