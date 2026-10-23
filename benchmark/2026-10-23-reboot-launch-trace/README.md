# T85 — 61b software reboot, one desktop tap, 30 s ability+window hitrace (FAIL)

**Verdict: FAIL — no feed.** t10/t30/t60/t120 screenshots are all white (`screens/`). This was one **standard software reboot** (`hdc target boot`), **not** a physical power-cut signoff.

## What was wrong before
On boot e9d0a715 the guardian sat in a fail-closed reentry hold (T82/emergency). A host force-stop did not clear it. T85 took a fresh boot so that one first launch could be observed with a bounded trace.

## Timeline (2026-10-23, +0800)
| Step | Time / guardian uptime | Detail |
|---|---|---|
| Lock | 16:58:02 | holder herdr-t85; stop deadline 17:06:02, restore deadline 17:08:02 |
| Reboot issued | 16:58:03 | old boot e9d0a715 |
| Ready | 16:58:56 | new boot 61aa5791 |
| Wake and unlock | 16:59:15 | — |
| WiFi auto-connected | 16:59:18 | — |
| Desktop tap | 17:00:01 (≈ uptime 109) | one tap on `AppIconCommonView_org.westlake.imehost.EntryAbility` (189,234) |
| Guardian | uptime 110 | `SUPERVISOR_STARTING` |
| Guardian | uptime 131 | `BOOTSTRAP` child=7049, parent appspawn-x 5129 |
| Guardian | uptime 133 | `UI_UNVERIFIED alive_no_cleanup` |
| Guardian | uptime 136 | `process_exit first_read_exited` / `child_retired strict_exited` |
| Guardian | uptime 137 | `AWAITING_REENTRY child_exited_wait_manual_icon` |
| Restore and release | 17:03:38 – 17:03:50 | Home; power `-r` and `-o 10000` read back 30000/10000 AWAKE; board UNLOCK 17:03:50; `held` rc=1 |

Throughout the window the host was `imehost` pid 4958 and the focus window was 32.

Child 7049 lived about 5 s, with no feed.

There was no `REFUSE FOREGROUND_HOST_NOT_READY` on this boot, unlike the emergency run.

## Trace
| Item | Value |
|---|---|
| Command | `hitrace -b 4096 -t 30 -o /data/local/tmp/t85-61aa5791.trace ability window` |
| rc | 0 |
| Size | 192811 B |
| SHA-256 | `08bc81f6…` (full value in results.json) |
| Uptime window | 91.55 – 120.70 |

**Limitation:** the trace **ended before the child bootstrap at uptime 131**. It covers the tap and the host 4958 ability/window marks at 108.83–109.10 only. It contains no record of child 7049. Summary: `trace_summary.txt`.

Cleanup checks after the run:
- `tracing_on` = 0.
- No hitrace process remained.
- The device trace file was deleted and verified absent.

The original trace is kept privately at `$HOME/.local/share/westlake/reboot-launch-trace-20261023/raw/06/` and is not committed.

## Collected / not collected
**Collected:**
- A rec receipt (argv/start/end/rc/stdout/stderr) for every device command.
- Samples of ps/WMS/uptime/guardian state+events at pre-tap, 1–10 s, and 30/60/120 s.
- The hitrace file.

**Not collected:**
- hilog, faultlog, or any application error log.
- `spawn.txt` content after the spawn. The 1–10 s samples predate the spawn at uptime 131, and the file was absent then.
- `readiness-reentry-7049-12973.jsonl` and `classifier.log`, which were listed in the boot dir but not read.

## Rules set
- A 30 s trace started at the tap does not cover a guardian-supervised child that bootstraps about 20 s later. Size the trace window from the guardian event timeline, not from the tap.
- `rec.py` refuses to reuse a record name. One failed `recv` invocation (empty `$HDC` variable, FileNotFoundError, no device effect) left `recv.argv/start`. The retry was named `recv2`, rc=0.
