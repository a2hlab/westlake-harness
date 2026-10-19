# 5cd normal-icon readiness: reviewable collection tool

The 61b acquisition plan cannot be reused for 5cd: this board has a different UID, run script and libandroid. An entry shell is not a business parent. This package pins the actual 5cd boot, cfg/run and UID from the indexed read-only receipt. It has **not executed on a device**. It is evidence collection, not production admission or video acceptance.

The outer owns the lock and one 600-second window. It performs one ordinary icon launch, reads the actual feed screenshot, and only with that same child alive performs one ordinary video-tab/open-visible-video action selected from the screenshot. No feed or exited child ends the window; no second icon, attach, deployment, reboot or automatic UI loop. Wakeup/Home/desktop navigation are outer actions. Do not call the screen-timeout-changing power-shell part of `bms_batch.desktop_launch`. Only this window's dedicated dumpLayout JSON/snapshot files are temporary device-file exceptions. Record skipped commands as NOT_EXECUTED, not fake device return codes.

`collect.py` defaults to local preview with zero device calls. Execution reads only the pinned serial. Every command checks the exact board-lock holder and boot; after identities are established, reads also check PID/PPID/birth, live state, UID, executable SHA and TracerPid before and after. The first stat is pinned immediately, before status/executable collection, and rechecked after bootstrap. Each command saves argv, stdout, stderr and rc/timeout in the fresh persistent output directory. A single command is limited to ten seconds or the remaining window, using a fixed monotonic budget after validating the outer wall-clock start. It uses a short serial-qualified HDC subprocess reader to preserve those bounds; it does not invoke the UI side effects of the general batch launcher.

## Outer procedure

1. Review t11 and this profile; hold the board lock. Set one `WINDOW_START` epoch at lock acquisition and preserve it across every call. Run before-icon once. It must return `NO_BUSINESS_CHILD`; an existing child is refused. Do not infer a current window ID from old run configuration.
2. Perform the single normal icon launch and actual feed screenshot. If feed is visible and the child remains alive, collect `after-feed` once, and use its identity for any subsequent collection. No UI verdict comes from the collector.
3. Perform at most one screenshot-selected ordinary video action; collect `after-video` using **mandatory `--identity-receipt "$AFTER_FEED/result.json"`**. This refuses a replacement child or parent. Missing modules remain unknown; feed brightness does not admit the player. End and release the lock within the original 600 seconds, retaining failures.

Illustrative commands below require outer-provided real values. They do not acquire a lock, perform UI, reboot or restore anything:

```sh
TASK="$WORKSPACES/westlake-harness/benchmark/2026-10-20-5cd-icon-readiness"
python3 "$TASK/collect.py"  # preview only
python3 "$TASK/collect.py" --execute --phase before-icon \
  --hdc "$HDC" --holder "$LOCK_HOLDER" --window-start "$WINDOW_START" \
  --repo "$WORKSPACES/westlake-harness" --out "$BEFORE"
# Outer: ordinary icon, actual screenshot and feed review.
python3 "$TASK/collect.py" --execute --phase after-ui --before "$BEFORE" \
  --hdc "$HDC" --holder "$LOCK_HOLDER" --window-start "$WINDOW_START" \
  --repo "$WORKSPACES/westlake-harness" --out "$AFTER_FEED"
# Outer: one ordinary visible video action, only if same child and actual feed.
python3 "$TASK/collect.py" --execute --phase after-ui --before "$BEFORE" \
  --identity-receipt "$AFTER_FEED/result.json" \
  --hdc "$HDC" --holder "$LOCK_HOLDER" --window-start "$WINDOW_START" \
  --repo "$WORKSPACES/westlake-harness" --out "$AFTER_VIDEO"
```

Five mapped roles are recorded with current file SHA/device/inode, not assumed from the profile. cfg/run alone are pinned as admission inputs; this is not a production provenance gate. GOT execution is disabled in this revision and always unknown. `--execute --player-elf` is rejected before transport; the ELF argument is offline preview only. The previous optional execution design lacked a mapping/file-identity sandwich and is not admitted. A later version would need that separate review. No process memory is read. `windows.txt` needs independent screenshot/WID correlation. Module SHA, GOT mapping and a process being alive do not establish actual calls, namespace winner, successful lock, playback or audio.

## Verification and sources

Six Python tests are exercised through three real Rust wrappers in `tools/spec-checks/tests/toutiao_5cd_icon_readiness.rs`. They cover profile/preview refusal, full-name/malformed-row selection, exact path refusal, disabled GOT execution, UID/duplicate/birth/read-range refusal and unknown-only receipt semantics. They do not certify device behavior. The contract has five scenarios; its three human scenarios remain pending review. `raw-index.json` indexes the original 5cd read-only receipt; `profile.json` contains its derived device profile. No prior raw evidence is modified.

Raw observations must stay in a persistent private directory; public summaries must omit personal media/URL data. This collector does not retrieve application logs automatically. The outer may preserve already authorized read-only logs separately within the same bounded window.
