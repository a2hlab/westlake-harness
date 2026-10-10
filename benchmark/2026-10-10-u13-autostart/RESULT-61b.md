# 61b on-board result — U13 autostart (WITH_BOAT=0) install + real reboot (2026-10-10)

Outer-approved window (ACK(91) ~09:00, ≤30 min, one reboot only). Announce→LOCK→install (WITH_BOAT=0)→one real
reboot→verify. Board left **autostart DISABLED + UNLOCKED** (safe handoff; next boot = bare /system for cx-t0's
native-ticket redeploy). Install log: `evidence/61b-autostart/install.log`.

## Verdict

- **Autostart mechanism: PASS, cleaner than 5cd** — `INSTALL_OK` (56/56), autonomous reboot ran the recover worker
  (`recover-autonomous-091726.log`: replayed 56/56, ondemand listener intact, `ready=true`), **319 fingerprint =
  319/319 exact, 0 mismatch, 0 absent** (vs 5cd's 315; 61b has physical route-a host libs + no boat overlay this round).
- **Apps still do NOT render (white)** — HelloWorld + ZigZag white (`evidence/61b-autostart/as-*.jpeg`). **But the
  blocker is different from 5cd and narrower.**

## The hilog finding (why white) — 61b's libinstalls WORKS; appspawn-x daemon doesn't spawn

On an `aa start` of ZigZag, hilog shows:
```
[AMSI4787]StartProcess: routing to appspawn-x for Android app: com.a2hlab.bridge.zigzag
[appspawn_client.c:148]Create socket success /dev/unix/socket/AppSpawnX socketFd: 14   (×2, retried ~2.2s later)
```
So on 61b AMS **does** recognize the app as Android/anco and **connects to the AppSpawnX socket** — the 5cd blocker
(stock `libinstalls` → app never marked anco → AMS never routes to appspawn-x) is **gone on 61b** (physical route-a
`libinstalls 51e1b525` works). The remaining gap: **the appspawn-x daemon never materializes** from that ondemand
connection (`pidof appspawn-x` stays empty; the client just retries the socket). Apps therefore stay white.

### Interpretation

- 5cd gap = libinstalls/anco routing (AMS never even tried appspawn-x). **Fixed on 61b.**
- 61b gap = appspawn-x **daemon not started**. init holds the ondemand listener (`/dev/unix/socket/AppSpawnX`,
  `00010000`) but does not spawn the daemon on connection in this state. 61b rendered under cx-t0's deploy only because
  **appspawn-x was already running** (I saw `pidof appspawn-x=11752` at install time, from that Mac-driven deploy).
- The autostart worker (per the proven donor shape / autostart-plan) deliberately **preserves the ondemand listener
  and never starts the daemon** (begetctl `start_service` returns 0 without starting an ondemand service; a direct exec
  from the su-domain worker would hit the `PR_SET_KEEPCAPS` wall). So from a bare-reboot autostart the daemon is down.

**Net:** the only remaining last-mile for a self-booting lit demo on 61b is **getting appspawn-x actually running** as
init's child after the replay — a narrow, well-isolated question now that libinstalls/anco routing is confirmed working.

## Facts (read straight off 61b)

| Check | Result |
|---|---|
| Install | `INSTALL_OK`, 56/56 archived+verified, WITH_BOAT=0 (no boat), pr03 superseded (backed up), cfg label `system_etc_file` |
| Bundle count (STOP-gate ≥128) | **231** (well above; not the "only 3" failure) |
| Autonomous reboot recover | `state=READY`, 56/56 replayed, `ready=true` (log 091726, ran on its own) |
| 319 fingerprint | **319/319 exact**, 0 mismatch, 0 absent |
| ondemand appspawn-x listener | present (`/dev/unix/socket/AppSpawnX`, `00010000`) |
| libinstalls (host lib) | route-a `51e1b525` (physical) — AMS routes Android apps to appspawn-x (hilog) |
| appspawn-x daemon after tap | **not spawned** (socket connect succeeds, daemon never comes up) → apps white |
| HelloWorld / ZigZag screenshots | **white** (`as-helloworld.jpeg`, `as-zigzag.jpeg`) |
| Toutiao / 10-key regression | not run (moot while appspawn-x daemon is down — all would be white; skipped to respect the window) |

## Caveats / discipline

- Per the outer's failure退路 (acceptance not met) I did **not** fix on-site; board handed back UNLOCKED + autostart
  DISABLED (next boot bare) for cx-t0's native-ticket redeploy (`5a172dd057`).
- One self-inflicted artifact: during diagnosis I manually re-triggered the recover service once, which re-ran the
  replay (the idempotence block logs but does not `exit 0`) → a cosmetic **double-bind** on the 56 targets. SHAs/319
  are unaffected (top bind wins); a clean reboot restores single binds. The autonomous proof is the 09:17:26 log, which
  predates any manual action.
- No `setenforce`; `/` remounted rw only for placement, re-sealed ro; only serial `61b0657200000000000000000324012c`
  touched; `wl_toutiao.cfg.disabled` left untouched. One reboot only (per outer). Not pushed.
