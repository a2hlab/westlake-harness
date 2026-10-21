# G06 operator card — CC is the sole device lane

All commands below are for the outer-reviewed execution channel. The author ran only prepare/tests/dispatch, never HDC. Keep G05's original rollback script as history; do not use it for this retained-install window.

## Offline preparation

```sh
MAIN="$WORKSPACES/westlake-harness"
G06="$MAIN/benchmark/2026-10-21-commercial-game/first-launch"
BASE="$HOME/.local/share/westlake/commercial-game-20261021"
python3 "$G06/prepare.py" --repo "$MAIN" --g05-root "$BASE/spare-preflight" \
  --out "$BASE/first-launch/plan-01" --window "$BASE/first-launch/window-01" --lane cc-video
python3 "$MAIN/scripts/lab/board_run.py" "$BASE/first-launch/plan-01/board-run.disabled.json" --dispatch
```

The output config has `approved_by=null`, and the plan has `execution_enabled=false`. The outer reviewer must check G07 wait/shot support and the exact new source pin, then sign a new execution copy by setting the actual approval and enabling the plan. This document is not a signature. Do not reuse an existing window directory; do not reuse the old October 13 runtime fingerprint. `after_lock` will bind the actual holder/start and recheck boot and all members. If boot/power/foreground changed, recapture and rederive; do not edit expected values to pass.

## Single window

Run the accepted plan with the original `board_run.py --detach`. Its normal sequence is lock → after_lock → existing smoke → one Genshin shard → before_unlock → unlock. Keep only CC issuing device commands. The plan's `shards` output path and recovery record search are the same path.

Outer records the actual lock timestamp and maintains 1200s experiment stop / 1800s close. Do not assume the JSON controls an in-flight 180-second install or a hanging subprocess. Do not terminate only board_run while its child BMS process can still write; coordinate a safe stop and serial recovery through the existing execution channel.

1. Inspect the actual after_lock context and smoke result. Fresh target must be absent; original power is SLEEP / 30000 / 10000 and focused lockscreen. No runtime replacement.
2. One original APK install, exact BMS bundle/UID/nativeLibraryDir readback. Normal `desktop_launch` selects the real icon from current layout; no `aa start` shortcut or stale coordinates.
3. G07 schedules the same launch at 5/20/60 seconds. Review actual images. Stop at resource/login/consent prompts without accepting them or downloading full resources. No extra sound confirmation is required by this first-launch card.
4. At the earliest serialized capture opportunity, retain `ps -A -o PID,PPID,UID,NAME`, actual child/parent `/proc/PID/stat`, boot, maps, and `readlink /proc/CHILD/fd/2`. Use the exact observed UID and fresh PID/birth, not a comm-only selector or old u8 PID. If fd2 is a regular file, pin inode/size and collect a fixed `[0,end)` range with after identity/hash; if already gone, preserve a proven newly-created dead-file but mark birth/coverage unknown. Do not collect concurrently with BMS's HDC requests. This explicit early-log seam is not automated by the stock BMS and must be scheduled by CC/outer, not asserted as completed by this plan.
5. For bounded PID hilog use the existing offline renderer:
   `python3 "$MAIN/benchmark/2026-10-20-t23-hilog-tail-successor/hilog_tail.py" plan --pid "$ACTUAL_CHILD" --tail 2000`.
   Execute its exact shell serially through the existing guarded Board; save transport rc/stdout/stderr. Run `inspect` on those files. Body `[CODE:-31]` is failure even with transport0. First/last timestamps and bytes establish coverage, not elapsed time. A vanished postguard does not justify deleting the captured log or claiming no call.
6. On return or failure, the signed `before_unlock` hook stops the proven target and retains installation/data. It checks nonempty successful BMS readback, exact member hashes, power/hilog/foreground. It never cleans a possibly preexisting app. A nonzero hook keeps the lock. Preserve all failed attempts; do not manually unlock until recovery is accounted for.

## Outstanding in-window reads, not new provider gates

- Ten sandbox directory absences and logging configuration are sampled automatically in `after_lock`; q07 covered only four paths and is not substituted for this check.
- Installed bundle readback: nativeLibraryDir plus actual selected-ABI members/hashes (32 static APK libraries is not a promised extracted count).
- Child birth/fd2/earliest log coverage and actual images require the real window. Provider binding, first fatal and game readiness remain unknown until then.
- At close run existing `scripts/lab/run_facts.py` on the actual BMS run root. Copy its output verbatim. Keep package retention inventory distinct from a successful game launch. Preserve original runtime and existing app data.
