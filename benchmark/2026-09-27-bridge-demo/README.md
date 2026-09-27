# Bridge-layer capability demo — 13 apps on-screen on 61b06572 (#48) — 2026-09-27

A camera-friendly, repeatable script that shows the westlake bridge lighting up a breadth of real
Android apps on one OH 6.1.0.31 DAYU600 board: it brings each verified-LIT app onto the physical
screen in turn, holds it for the camera, snapshots it, then force-stops and moves on — finishing by
restoring the flagship Toutiao feed. **Test run: 13/13 apps reached the screen, Toutiao restored.**

## Deliverable
`demo_bridge_apps.sh <SERIAL=61b06572> [HOLD=10] [RENDER_WAIT=13]`
- **Only 61b06572 is allowed** — 5cd1e3dd / 5ea34a45 (their own Toutiao demos) are hard-refused.
- Idempotent + repeatable. Leaves the board on the Toutiao feed.

## What it demonstrates (the bridge, per app — all via `probe_source_app.py`)
1. A **self-contained source runtime** staged on-device and launched through `source_app_namespace`
   (Android app running on musl/OpenHarmony, no OH install).
2. The app's **sub-window attached to the OH host window** (`WL_PARENT_ID` / `WL_SUB_WINDOW`), so it
   composits onto the real display.
3. **Real touch**: `touchfwd` reads the digitizer evdev node and re-injects gestures into the bridge's
   in-process channel — OH MMI never routes to these bridge sub-windows, so without this the panel is
   dead. (Visible in the demo: e.g. Termux renders its full soft keyboard.)

## Flow
1. Stop the Toutiao watchdog + keeper and kill the source apps, **keeping the host** (so no host
   reinstall / WL_PARENT_ID drift). Clear stale per-app runtimes (guarding the Toutiao RT **and** STAGE).
2. Start the on-screen keeper (`onscreen_keeper.sh`, reused from the device-provisioning bundle) —
   keeps the screen awake and swipe-dismisses the OH keyguard for the whole demo.
3. For each of 13 apps: `probe_source_app.py` stage+launch (~25–30 s) → wait `RENDER_WAIT` → wake +
   swipe-dismiss the keyguard → confirm on-screen by **window ZOrder** (host `imehost0` fronted ≥0 AND
   `SCBScreenLock` dismissed <0) + child alive → **HOLD** for the camera → `snapshot_display` →
   force-stop → reclaim that app's on-device runtime/stage.
4. Finale: relaunch the Toutiao watchdog + keeper; wait for READY + feed on screen.
5. Print `on-screen: N/13` + `Toutiao restored: yes/no` and per-app screenshot paths.

## Apps (demo order; keys = `app-inputs/<key>`)
wikipedia · antennapod · aegis · fd-com-kunzisoft-keepass-libre · fd-netguard · fd-auxio ·
fd-com-amaze-filemanager · fd-AppManager · fd-droidify · ooniprobe · fd-noice · fd-fitness · termux

## Test-run result (runtag 0927-225907, HOLD=10s)
**on-screen: 13 / 13 · Toutiao restored: yes.** Every app rendered its real UI (host_z=101, lock_z=-1,
child alive) — spot-checked: Wikipedia onboarding globe, OONI Probe mascot + "Got It", Termux dialog +
full soft keyboard. Screenshots in `screens/` (`01-wikipedia.png` … `13-termux.png`,
`99-toutiao-restored.png`). ~29 s/app staging → whole cycle ~14 min.

## Board key facts baked in (learned live)
- **Drop `--host-build`**: 61b runs the Toutiao-branded host (df385638), which differs from verify's
  signed-host, so probe's host-payload check refuses it. Without `--host-build` probe reuses the
  installed host — and keeps df385638 the whole time, so restoring Toutiao needs no host reinstall.
- **Use 61b's own `framework-1` device-report** (passed=True) as `--framework-report`.
- **Fresh `--out` per app** (probe rejects a reused output dir).
- **Guard BOTH `a2hlab-source-c91d26bf…` (RT) and `a2hlab-app-c91d26bf…` (STAGE)** when cleaning:
  the STAGE dir holds `source_app_namespace`/`host_spawn`/`request.bin` and the watchdog's
  `start-parent.sh` writes `parent.log` there — deleting it strands Toutiao in `PARENT_BLOCKED`.
  (Found the hard way in the first test run; fixed in the cleanup step + restored from `tt-stage.tar`.)
- The board shell has no `awk`/`tr`; ZOrder parsing is done Mac-side from `hidumper` output.

## Constraints honored
Only 61b06572 was touched. 5cd1e3dd / 5ea34a45 kept their own Toutiao demos on-screen throughout.
