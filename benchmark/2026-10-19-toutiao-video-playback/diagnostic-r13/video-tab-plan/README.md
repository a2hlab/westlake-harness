# One-child video-tab-first R13 plan

**Planning template only; no device execution performed.** A bright feed did not imply a loaded player: all 9 retained early-readiness maps lacked player while the other four roles existed. Historical R10 maps already contained player after entering the video tab and before the subsequent play1 tap. Do not repeat feed-before-player waiting as the preferred order.

1. Before the window, run local preflight; prepare exact tools, source pins and rollback. In the exclusive window stage `video_outer.py stage BOOT` from the main repository root, using its fresh owned `window4` directory. Launch the normal icon once, confirm feed by screenshot, and record exact boot/parent/birth/child/birth. No automatic launch or UI retry.
2. Perform a normal video-tab action. The outer checks that same child's five module maps. If player is missing, use the actual screenshot to perform **one** normal play action, then check again inside the original window. If still missing or identity changes, restore; do not run the attach template or select another child. The UI check is deliberately outside this script and is not replaced by a guessed coordinate.
3. Once all five modules are present, invoke the one-shot template below. It rechecks exact full `ps NAME`, UID, PID/birth/parent, module SHA/inode/PT_LOAD and unique player, then calls existing attach and unmodified observer once. After verified hardware-breakpoint setup and resume, the outer may perform normal UI actions to produce subsequent calls; initial calls before attachment remain unobserved. Partial/no events are unknown, not playback acceptance.

```sh
python3 benchmark/2026-10-19-toutiao-video-playback/diagnostic-r13/video-tab-plan/acquire_once.py \
  --identity "$BOOT" "$PARENT" "$PARENT_BIRTH" "$CHILD" "$CHILD_BIRTH"
# Only after the outer completed steps 1–2 and reviewed the window:
python3 benchmark/2026-10-19-toutiao-video-playback/diagnostic-r13/video-tab-plan/acquire_once.py \
  --identity "$BOOT" "$PARENT" "$PARENT_BIRTH" "$CHILD" "$CHILD_BIRTH" --execute
```

Without `--execute`, only local source/module/tool hashes are checked; no HDC/LLDB import or execution. Run from the main repository or pass `--repo`. The existing private admission template remains an input, not a committed credential/configuration file. Preflight may use the known intended identity before the actual window; execution always requires current exact identity. Source pins reject drift; do not update pins merely to make a mismatch pass.

`video_outer.py` differs byte-for-byte from reviewed `r13_early_outer.py` only in three strings: `r13-early-server-` → `r13-video-server-`, `-window3` → `-window4`, and `r13-early-admission.json` → `r13-video-admission.json`. Observer output is fresh `r13-video-observer`. No original observer or GOT/module/120-second rule is altered. Existing paths must not be overwritten; refuse reused readiness/output directories.

**Stops and recovery:** same child only, no retry loop. Readiness has a 30-second logical deadline checked after every read and before attach. `Board.shell` internally runs `ready()` with separate timeouts, so this is **not a strict wall-clock bound**; an overdue read cannot proceed to attach. The outer retains the original 20-minute restore start / 30-minute hard window. Attach timeout is 35 seconds; observer retains its own 120-second observation and cleanup grace. Any failure/nonzero/timeout requires immediate outer rollback/fresh boot and verification. Killing the orchestration process does not prove the remote server or separate LLDB process was cleaned up. Even successful diagnostic completion still follows the planned baseline restoration.

The real `ps` fixture preserves the selected original line (`7462 5602 20011206 com.ss.android.article.news`); `/proc/stat` uses truncated comm `id.article.news` but is parsed by PID/birth, not name. Tests reject wrong UID/name/PID/parent/birth and duplicate full-name candidates. Original sources and hashes are in `source-index.json`; local fixture projections contain no user content. These tests do not prove actual attach compatibility or runtime identity.
