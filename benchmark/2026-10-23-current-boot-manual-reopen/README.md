# T87 — same boot, one normal desktop reopen: feed shown at t90

On boot 61aa5791 the board was in `AWAITING_REENTRY` after T85's child 7049 exited. One ordinary desktop tap at 17:21:34 (uptime ≈1401) brought up a new child 6291, which reached a visible Toutiao feed by t90.

- **Spawn timing:** the guardian logged `reentry_spawn_ok` / BOOTSTRAP for child 6291 at uptime 1428, about 27 s after the tap. The 1–10 s samples show no new spawn; the last event visible in them is still T85's old seq=1 record.
- **Screens over time:**
  - t10 and t30: white.
  - t60: the app UI was rendered, with the error message 网络异常，请稍后重试 in the feed area.
  - t90: a feed showing a recommend list and a video card.
  - At t90 the guardian logged `first_feed_observation`.
- **Network caveat:** at t90 wlan0 had no IPv4 address, so the feed may have come from cache; whether the device was online is unknown.
- **Trace:** a 90 s ability/window trace finished normally (rc 0). It covers uptime 1401.3–1490.7, which includes child 6291 (3324 B-marks). The device copy of the trace was deleted.
- **Close-out:**
  - Power was restored; the 30000/10000 timeouts were read back.
  - The board was unlocked at 17:23:51, with the lock taken at 17:20:55.
  - The feed was kept on screen.
- **Scope:** this is a same-boot manual reopen. It is **not** a power-cut first-launch signoff.

The original trace and per-command receipts are kept privately at `$HOME/.local/share/westlake/current-boot-manual-reopen-20261023/raw/`.
