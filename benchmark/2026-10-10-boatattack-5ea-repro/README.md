# BoatAttack 00.Workspace reproduce on 5ea + baseline diff vs our U13 (cc-t3 #91)

Copy-exact attempt per the already-solved 00.Workspace solution (`~/orca/00.Workspace-games-ad1ab0a7`, branch
`games/boatattack-repro` 43ec24af9). Goal: get the GOOD reference BoatAttack (the 00.Workspace PASS) and diff it against
our boards to explain the bad render (low-res/purple/KPH-001).

## What was done (whitelist-only, pins/criteria untouched)
Added our spare serial `5ea34a4500000000000000001123012c` to the serial whitelist of **both** drivers the reproduce uses:
- `src/tools/devices/boat-attack-apk-lightup.sh` — constant + BOARD_LABEL case + `device_preflight` case (3 spots).
- `src/tools/devices/zigzag-apk-lightup.sh` — constant + `device_preflight` case (the boat restore calls `zigzag
  run-light-risk` for the shared candidate; its separate whitelist was the real gate, plus a hidden-char typo in my first
  edit — both fixed, backups `*.pre5ea34.bak`). No pin/criterion/SHA changed.

## BLOCKER — the reproduce cannot run on a U13 board
After the whitelist fix the board check passes, but `restore` fails at **`verify_pr03_backing`** (zigzag deploy):
```
==> deploy native closure plus runtime-jar candidate to direct 5ea34
candidate deployment failed; restoring visible PR03 mounts
ERROR: candidate deployment failed   (auto-rolled-back; 5ea /system intact at U13: adapter 84695d62)
```
`verify_pr03_backing` requires the board's **/system targets to already equal the PR03 backing** (`/data/pr03-74e6-portable`),
because the reproduce **bind-mounts the 9-file BoatAttack candidate OVER an assumed-PR03 /system** (it does not install PR03).
Our 5ea is at the **U13 campaign baseline**, not PR03 → verify fails. The reproduce was validated on PR03-baseline boards
(61ae / 8605 / 5ea17192); our campaign boards (5ea34a45, 61b) are U13. So the GOOD reference cannot be produced on 5ea, and
61b currently has **no** BoatAttack (adapter 84695d62 = U13, `bm dump` BoatAttack = 0). The live "5ea-PASS vs 61b" diff is
therefore unreachable right now — but the static baseline diff below is the actionable result and the likely defect root.

## Diff table — 9 shared files: three distinct versions
The BoatAttack **candidate** (what bind-mounts on top) is identical in both scenarios; the **backing** underneath differs.
Everything NOT in these 9 (EGL/Swappy/graphics/boot image/other runtime libs) uses the backing — PR03 for the good ref,
U13 for ours.

| shared file (target) | our U13 deployed (前16) | PR03 backing RAW (前16) | BoatAttack candidate (前16) | verdict |
|---|---|---|---|---|
| liboh_adapter_bridge.so | 84695d62 | 7db99e1b | 8ab85446 | use original candidate (overlaid); backing differs |
| liboh_android_runtime.so | 18763dd4 | 9689ce76 | adc125f4 | use original candidate; backing differs |
| oh-adapter-runtime.jar | bbc3f530 | 06141543 | **56e4d473** (vs C9 6333bcab) | use original 56e4d473 (the validated jar), NOT the C9 6333bcab |
| appspawn-x | 2a87118e | c7fd4bd6 | 76e6df93 | use original candidate |
| libnativeloader.so | b8be63d2 | f8a5c192 | fde6f31c | use original candidate |
| libandroid.so | 9ccf64f8 | (candidate-only) | (SHARED_LIBANDROID) | use original candidate |
| libwestlake_android_runtime_provider.so | (read) | 9c650fe3 | f821d20e | use original candidate |
| libwestlake_android_child.z.so | (read) | f9a36217 | 47f238ae | use original candidate |
| libwestlake_bionic_pthread_bridge.so | (read) | cce31e65 | db31d6d8 | use original candidate |

**Key**: the candidate (col 4) is validated against the PR03 backing (col 3). Our boards' backing (col 2) is U13 — a
DIFFERENT set. The reproduce refuses to overlay the candidate unless the backing is PR03, precisely because mixing the
validated candidate with a non-PR03 backing is untested — which is almost certainly why 61b's BoatAttack renders badly:
the non-overlaid libs (EGL/Swappy color config, SurfaceView/HWUI buffer sizing, input) are U13's, not the PR03 ones the
candidate expects.

## Likely defect root + what to diff next (render/color/input — per the 06:15 acceptance)
- **Render resolution / SurfaceView buffer**, **color (Swappy/EGL config)**, **input path** all live in libs OUTSIDE the
  9-file candidate → they come from the **backing**. On a U13 backing they are U13's; on PR03 they are PR03's. The diff that
  matters is the **backing delta** for the graphics/EGL/Swappy/input libs + boot image, not the 9 candidate files.
- **BMS install projection**: `bm dump -n com.Unity3d.BoatAttackDay` can only be diffed once BoatAttack is actually
  installed on a board — currently 0 on both 5ea and 61b, so this is pending a real install.

## Recommendation
To produce the GOOD reference and a meaningful diff: run the 00.Workspace reproduce on a **PR03-baseline** board (its
intended target), OR establish the PR03 backing on a spare board first, then compare the backing graphics/EGL/Swappy/input
libs against U13's. The whitelist edits are in place for when a PR03 board is available. 5ea left intact at U13 (deploy
auto-rolled-back); appspawn-x is the ondemand U13 service — cx-t0's U13 restore/verify covers it.
