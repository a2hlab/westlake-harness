# T114 — 5cd host lifecycle after RETRY_LIMIT (read-only, 1.2 s of 60 s)

**Identity.** `held` returned rc 1. Boot ecb84d86 and host `org.westlake.imehost` pid 5074 (birth 9930) were identical before and after the read (`identity_stable: true`). There was no UI action and no device write.

**`window-state.json`.** `/data/app/el2/100/base/org.westlake.imehost/files/window-state.json` does **not exist** (stat: No such file or directory), so its state is **unknown**.

**Host hilog.** The command was `hilog -P 5074 -z 2000 -L D,I,W,E,F -v epoch`, with an 8 s host timeout and no `-x`. It returned rc 0 and 987 lines, covering 22:41:56.501 – 22:51:28.827 (see `hilog_coverage.json`). The T112 tap at 22:48:54 falls inside that coverage. The full original is private; only the 28 `WL_IME_HOST` lines are published, in `wl_ime_host_lines.txt`.

**Lines around the T112 tap.** The host's own `WL_IME_HOST` callback records show the following:

| Time | Event |
|---|---|
| 22:48:38 | `foreground` |
| 22:48:41 | `background` |
| **22:48:56.912** | `foreground`, then stage-event 1 and 2 (device log clock; host/device offset not measured) |
| 22:51:27 | `background` |

These are listed as recorded and not interpreted further; the offline comparison is Codex's.

**Private originals.** `$HOME/.local/share/westlake/host-lifecycle-after-retry-limit-20261023/` (`raw/hilog.stdout`, SHA-256 bb0355ed…).
