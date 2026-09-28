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

## 关机启动后的使用流程（2026-09-28 冷启实测通过）
61b06572 装了 **13 个可点桌面图标**（la0-la11 十二个 app + 今日头条红图标 imehost），全部 `bm install`，**重启存活**。

**每次开机/重启后，跑一条命令即可（纯板载自启尚未打通，见 `autostart/README.md`）：**
```
bash benchmark/2026-09-28-persistent-demo/persist_demo.sh 61b06572 up
```
它按正确顺序起 host 宿主窗 + 保屏 keeper + open-broker。之后**点任意一个桌面图标 → 对应 app 渲染到首屏**（头条点它自己的红图标）。

**冷启实测（03:11，uptime 94s 的全新重启）**：`persist_demo.sh 61b06572 up`（UP: host=4331 broker=5373）→ 点 la6 图标 → Aegis 首屏渲染。截图 `screens/`（final2/reboot_la0b/myla6）。

**图标↔app**：la0 Wikipedia · la1 OONI · la2 KeePassDX · la3 Amaze · la4 Auxio · la5 AntennaPod · la6 Aegis · la7 NetGuard · la8 AppManager · la9 Droid-ify · la10 Noice · la11 Fitness · imehost 今日头条。

**注意**：Toutiao selfheal watchdog 若在跑会抢前台把头条顶上来盖住别的 app；`up` 不启动它，保持关闭即可（头条仍可点自己图标打开）。

**踩坑（2026-09-28）**：
- 参数顺序是 `persist_demo.sh <SERIAL> <CMD>`。写反（`up 61b06572`）会报 `REFUSE: only 61b06572 (got up)`，看着像 broker 坏了，其实没有。
- 在 61b 上 stage 这 12 个 app 时一度把头条运行时 `a2hlab-source-c91d26bf…` 删了，头条随即起不来（watchdog 永远 `BOOTSTRAP`）。给 demo 板加 app 前先确认不动这个目录。该目录后来已恢复（11:40 复核：143 个 lib，与 5cd 一致），但 61b 的 watchdog 仍停在 `SPAWN_BLOCKED`，原因未查。
- 该目录在 61b 上长到 31 GB（5cd 6.9 GB）：`profile-backups/` 22 GB（提速期 JIT profile 备份）+ `private-tmp/adapter_child_*.stderr` 5.7 GB（单个可达 743 MB，几乎全是 `[TOUCH21-POLL]` 调试输出）。/data 还剩 177 GB，暂不构成问题，但 grep 这些 stderr 必须先记基线行只看新增。
- 头条红图标点开是 host 启动器而不是 feed：图标只拉起 host 窗口，feed 要靠 selfheal watchdog spawn 进去。watchdog 没跑或卡住时就只看到 host。
