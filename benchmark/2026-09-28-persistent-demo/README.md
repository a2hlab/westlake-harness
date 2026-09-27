# Persistent bridge-app demo — 61b06572 (reboot-surviving) — 2026-09-28

Install 13 bridge apps on 61b06572 so they survive a **reboot** and can be opened to their first screen —
tomorrow's demo material. The 13 source runtimes are staged on `/data` (persistent), and any app is opened
by a fast `host_spawn` from its persisted runtime — no re-staging, no Mac/VM needed at demo time.

**Reboot-verified**: after a real reboot (`uptime` 1 min), `up` + `open wikipedia` / broker `req ooniprobe`
both rendered the app's first screen. Command entry is the reliable baseline; the desktop-icon entry is being
added by claude-3 as a HAP that talks to the broker (see the contract below).

## Feasibility answers (explored before building)
1. **Persistence** — `/data` is f2fs (persistent), `/dev` is tmpfs (sockets auto-cleared on boot, so no stale
   sockets after reboot). The 13 runtimes (`/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-*`),
   their stages (`/data/local/tmp/a2hlab-app-*`), the manifest, the host bundle and the framework all persist.
   Only **processes** die on reboot (host, appspawn-x, source_app_namespace, keeper, broker) — re-launched by `up`.
2. **Auto-start** — **not established.** The Toutiao watchdog was a manual `nohup` (not a boot service); OH
   `/system` is read-only (ext4 ro), so adding an init `.cfg` service isn't safe/feasible for tomorrow. The
   one post-boot step is `persist_demo.sh 61b06572 up` (starts host + keeper + broker). `bootevent.boot.completed`
   exists but wiring a service to it needs a `/system` write or a host-HAP rebuild — out of scope for stability.
3. **Entry to first screen** — (a) one OH icon per app is **infeasible** (only ONE OH bundle exists,
   `org.westlake.imehost`; 13 real icons would need 13 OH bundles). So: **(c) command `open <app>`** (reliable,
   shipped here) and **(b) desktop icons via a launcher HAP → broker** (claude-3 builds the HAP; the broker
   below is the privilege bridge).

## Deliverables
- **`persist_demo.sh <SN> {install|up|open <app>|open-all [HOLD]|req <key>|broker-stop|list|status|toutiao}`**
  - `install` (needs VM, ~7 min): clean orphan runtimes, stage all 13 apps, record `manifest.txt`.
  - `up` (post-boot, no VM): start host window + on-screen keeper + open-broker.
  - `open <app>` (no VM, ~1 s + render): fast `host_spawn` one app from its persisted runtime to first screen.
  - `open-all [HOLD]`: open each of 13 in turn (screenshot each) — the reboot verification.
  - `req <key>`: drop a broker request (simulates a HAP icon tap).
- **`open_broker.sh`** — the privileged on-device broker (see contract). Runs as root, started by `up`.
- **`manifest.txt`** — `app-key  runtime-suffix  socket  package` for the 13 apps (persists on device).

## Broker contract (for the launcher HAP / claude-3)
An OH HAP icon runs as a normal app uid and **cannot** do the bridge launch itself (`host_spawn` +
`source_app_namespace` need root / mount-namespace privilege). The broker runs as **root** and does it on the
icon's behalf. To open app `KEY` (KEY = app-key in `manifest` col1 **or** its package in col4), the HAP drops a
request via ANY of:
1. **Drop dir (preferred)**: create `/data/local/tmp/persist-demo/reqs/<KEY>` (empty file; filename = KEY). Dir 777.
2. **Drop file**: write `"<KEY>\n"` to `/data/local/tmp/persist-demo/open.req` (666).
3. **App sandbox (most robust)**: write `"<KEY>\n"` to `context.filesDir + "/wl_open.req"`; the broker scans all
   app sandboxes' `files/wl_open.req` via root. Use this if the OH sandbox blocks writing to `/data/local/tmp`.

The broker consumes the request and opens KEY to the physical first screen (killing any other demo app first,
so exactly one app shows), ~1 s + first-frame render. Verified: `req ooniprobe` → broker `HOST_SPAWN result=0` →
OONI Probe first screen on the display.

## How the fast open works (why no re-staging is needed)
`request.bin` encodes only uid + host name (NOT the window id); `WL_PARENT_ID` is passed via the RT's `run.sh`
env. So a persisted runtime is re-launchable: resolve the current `imehost0` window id → `sed` it into
`run.sh` → `source_app_namespace <RT> <uid> sh /data/local/tmp/asx/run.sh` → wait for the app's
`A2HSource<suffix>` socket → `host_spawn <socket> request.bin`. The socket name is deterministic
(`A2HSource` + first 20 hex of the runtime suffix). `/dev` is tmpfs so no stale socket survives a reboot.

## Demo runbook (after a reboot)
```
persist_demo.sh 61b06572 up            # once, post-boot: host + keeper + broker
persist_demo.sh 61b06572 open wikipedia # or any of the 13 keys — app to first screen
# (with the launcher HAP installed: just tap the app's desktop icon → broker opens it)
persist_demo.sh 61b06572 toutiao       # optional: bring back the Toutiao self-heal flagship
```

## Constraints
Only 61b06572 was touched. 5cd1e3dd / 5ea34a45 (their own demos / claude-3's HAP work) not touched.
