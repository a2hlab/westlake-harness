# cv2 non-lit keys re-run with --hilog (2026-10-01, oc-t4)

Dispatch (board R2 #97 10:05:37): the cv2 full sweep ran without --hilog; the 33 non-lit keys needed hilog for first-fatal clustering. Re-run with `--reinstall --hilog --shots 5,20` under U7, three boards ≤30min windows.

## Selection

From master `benchmark/2026-10-01-cv2-sweep/outer-signoff.json`, keys whose verdict does NOT start with `lit`: **5ea 12** (cv2-anupam-acrylic [alive-launcher-foreground] + 11 dead), **5cd 10** (3 alive-launcher-foreground + 7 dead), **61b 11** (cv2-com-frequent-habits [app_failed] + 2 alive-blank-window + 8 dead). Key lists: `$WORKSPACES/westlake-inputs/corpus-v2/keys-cv2-hilog-{5ea,5cd,61b}.txt`.

## Runs

- 5ea `westlake-harness-t4/benchmark/2026-10-01-cv2-hilog/5ea/20261001T101035-6780fc5e/`
- 5cd `westlake-harness-t4/benchmark/2026-10-01-cv2-hilog/5cd/20261001T101035-8d71b9e8/`
- 61b `westlake-harness-t4/benchmark/2026-10-01-cv2-hilog/61b/20261001T101035-d4e56708/`

Identity identical on all three: RUNTIME fingerprint=68b7fb016253 files=119 / FROZEN checked=4 violations=0 / BOOTIMAGE fingerprint=8fe2e5fd7d65 files=36 / TOOL bms_batch=456dfc6f head=7252382f2 manifest=d5451a89. Boards unlocked after the runs (held empty).

## facts.txt verbatim (TOTAL lines)

- 5ea: `TOTAL keys=12 screenshots_captured=24/24 alive_t5=1 alive_t20=1`
- 5cd: `TOTAL keys=10 screenshots_captured=20/20 alive_t5=2 alive_t20=2`
- 61b: `TOTAL keys=11 screenshots_captured=20/20 alive_t5=2 alive_t20=2` (cv2-com-frequent-habits app_failed, no hilog)

All keys foreground_unconfirmed; lit/not-lit left to outer-loop screenshot review.

## first-fatal clusters (clusters.json, scripts/lab/first_fatal.py per key dir — same method as 0944217a4)

33 entries: 29 termination-found, 3 no-observed-termination, 1 process-disappearance-cause-unknown. Terminal kinds: 26 main_threw, 3 none, 2 signal, 1 system-exit, 1 process-disappeared. 9 clusters by first-cause tag+message prefix:

- [21] AppSpawnXJava main_threw RuntimeException (majority, startup runtime failure)
- [4] none (no first cause extracted)
- [2] main_threw NullPointerException
- [1] DfxSignalHandler SIGSEGV (signo 11, cv2-com-ath0-rpn)
- [1] appspawn-x System.exit status 0 (cv2-com-kaajjo-libresudoku)
- [1] DfxSignalHandler SIGABRT (signo 6, cv2-org-linaro-glmark2)
- [1] main_threw UnsatisfiedLinkError (cv2-com-chessclock-android)
- [1] main_threw NoClassDefFoundError
- [1] main_threw android.view.InflateException

## Landing paths

- benchmark/2026-10-01-cv2-hilog/README.md
- benchmark/2026-10-01-cv2-hilog/clusters.json
- benchmark/2026-10-01-cv2-hilog/5ea/20261001T101035-6780fc5e/ (run dir)
- benchmark/2026-10-01-cv2-hilog/5cd/20261001T101035-8d71b9e8/ (run dir)
- benchmark/2026-10-01-cv2-hilog/61b/20261001T101035-d4e56708/ (run dir)
- $WORKSPACES/westlake-inputs/corpus-v2/keys-cv2-hilog-{5ea,5cd,61b}.txt

## What is committed (outer loop, master)

Full `hilog.txt` files (33, 232 MB) and the per-command `commands/` dirs stay in the westlake-harness-t4 worktree; `hilog-manifest.json` records each path, sha256 and size. Committed per key: `record.json`, `install.txt` and `first-cause-excerpt.txt` (the AppSpawnXJava stderr block from `J_invokeStaticMain_main_threw`, up to 80 lines, or signal lines when nothing was thrown); per run: `facts.txt`, `plan.json`, `baseline.json`, fingerprints. Key lists copied to `keys/`.
