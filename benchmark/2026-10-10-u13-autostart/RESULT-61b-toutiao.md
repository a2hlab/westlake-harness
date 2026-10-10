# 61b Toutiao Route B overlay (叠回) + AppSpawnX socket 0660 — honest outcome (2026-10-10)

Outer-approved window: LOCK 61b → re-overlay Route B from the on-board inputs (source-host.hap / tt-rt.tar 014c566e /
asx-spawner rename) → foreground-tap acceptance (feed / article / 3 cold starts) with HW·ZZ 不退 → boot slot NOT enabled
→ v2 recover AppSpawnX socket 0660. Recipe copied from master `0cd47f8b6b` (`provision_toutiao.SAFE.sh`, `demo-path.md`)
and `cfab66ae8c` (boot-slot, `run-spawner-rename.patch`). LOCK 13:38 → UNLOCK. Evidence: `evidence/61b-toutiao/`.

## Verdict: Route B runtime re-overlaid + HW 不退 PROVEN; on-screen front BLOCKED by imehost having no launcher icon on 61b

| Item | Result | Evidence |
|---|---|---|
| Route B inputs present on 61b (no 792 MB push needed) | **PASS** — imehost installed; RT already extracted; stage + watchdog present | read-only check: RT `appspawn-x a7a358c6`, `run.sh 7a0877d7`, `prepare_jit50 ad115b0b`; STAGE `source_app_namespace 60b89e11`, `host_spawn 019acf9e`, `request.bin 2190ff06` — all = inventory pins |
| asx-spawner 改名共存 applied | **PASS** | `run.sh:42` → `cp -f appspawn-x asx-spawner; exec asx-spawner --socket-name A2HSource…` (new sha `4c77e323`, backup `run.sh.pre-rename.bak`); ran as distinct process `asx-spawner` (A2HSource socket) coexisting with U13 `/system/bin/appspawn-x` |
| onscreen_keeper.sh staged (was missing) | **PASS** | pushed from `tt-wd.tar`, sha `a55ebc4c` = boot-slot donor |
| Route B runtime spawns | **PARTIAL** — spawner + `com.ss.android.article.news` child spawn, but child **crash-loops** (no host window to render into) | asx-spawner + child pids cycled 7281/7300 → 12877/12896 → child 15416; `adapter_child_*.stderr` shows `Backtrace:`/`Fault message:`; 113 watchdog instances |
| **前台桌面点击启动 (foreground tap)** | **BLOCKED** | `bm dump org.westlake.imehost`: EntryAbility has `action.system.home`+`entity.system.home` but **`isLauncherAbility:false` / `isLauncherApp:false`, `label:""`** → **no 今日头条 desktop icon** (9 desktop pages scanned, 0 头条 nodes). Reinstalling the bundle HAP (`df385638` ✓) did not change it. `aa start` = 10107101 (background); broker refuses 61b. No icon → no host window (imehost0) → child can't render |
| 刷首页 / 点开文章 / 3 cold starts | **NOT REACHED** | depends on imehost0 being fronted; blocked above |
| **HW 不退 (route-A coexistence)** | **PASS (HW)** | after SAFE-stopping the Route B thrash, `aa start helloworld` → full UI rendered (`evidence/61b-toutiao/hw61b-lit.png`: Hello World! + CHANGE COLOR + lifecycle + buttons, Focus window 29); U13 appspawn-x daemon respawns on demand (pid 17208) |
| ZZ relaunch | **not confirmed** — `aa start -b com.a2hlab.bridge.zigzag -a EntryAbility` failed (wrong ability name); not chased in-window |
| appspawn-x never killed (RUNBOOK #12) | **PASS** | every clean used `pidof` of B's own names only (`article.news`/`source_app_namespace`/`host_spawn`/`asx-spawner`); appspawn-x daemon alive throughout |
| boot slot enabled | **NO** (as instructed) — no init cfg placed/enabled; left for the v1-seal reboot |
| v2 recover AppSpawnX socket 0660 | **staged** (verify next reboot) | `westlake-u13-recover.sh:186` now actively `chown 0:6005 + chmod 0660 + chcon appspawn_socket` the listener (was WARN-only); 42/42 KA pass |

## The blocker, precisely

Completing the on-screen Toutiao demo needs the host window **imehost0** fronted. The proven lever (master `demo-path.md`,
5ea) is a **foreground tap on the 今日头条 desktop icon** — but on 61b the installed imehost HAP registers its EntryAbility
as a *home-screen* ability (`action/entity.system.home`) that is **not launcher-visible** (`isLauncherAbility:false`), so
there is **no icon to tap**. `aa start` is a background caller (10107101), and the privileged broker (`persist_demo.sh`)
hard-refuses 61b. Without imehost0 the Route B child crash-loops (it has no surface).

**This is a HAP/registration gap on 61b, not a Route B runtime failure.** The runtime itself re-overlays cleanly (inputs
verified, rename applied, spawner+child spawn; ICU walls were already proven on 5ea at `0cd47f8b6b`). To finish on-screen,
a follow-up needs one of: (a) the launcher-registered imehost HAP variant (whatever 5ea had a 今日头条 icon from), or
(b) the `START_ABILITIES_FROM_BACKGROUND` grant so `aa start`/the watchdog can front imehost0 (`host-launch-grant.md`
lever). Both are out of this read-and-overlay window; reported for the outer to choose.

## Board left clean

Route B SAFE-stopped (stop files set; child/spawner/host_spawn killed by `pidof` — **never appspawn-x**); inputs staged +
rename applied (re-arm = clear stop files once the icon/grant lever lands). U13 base intact: HW lights, appspawn-x daemon
respawns. No `/system` frozen-identity change; no `setenforce`; no reboot; only serial `61b0657200…` touched; not pushed.

---

## UPDATE (2026-10-10 ~14:20) — root cause is NOT the installer; it's 61b's SceneBoard launcher grid

Outer-dispatched A/B (install the same `df385638` under the route-a installer `51e1` and check for the icon). 5cd was
held by cx-t0, so I ran it on **5ea** (free, and the *better* control — 5ea is the board that showed the 今日头条 icon last
night under the original installer `2c9a5294`). Evidence: `evidence/5ea-installer-ab/`.

### Finding: the installer is exonerated; `isLauncherAbility` is a red herring

| Board | installer | df385638 install | `isLauncherAbility` | 今日头条 desktop icon |
|---|---|---|---|---|
| 5ea (clean, fresh install this window) | `51e1` | fresh | **false** | **PRESENT** ✓ (`uitest` node `今日头条`; alongside Hello World/Wikipedia/AntennaPod…) |
| 61b | `51e1` | update (`-p`) | false | **ABSENT** (14 pages scanned, 0 nodes) |

So **`51e1` installs a working, tappable 今日头条 icon** (proven on clean 5ea). `isLauncherAbility=false` appears on BOTH
boards yet 5ea still shows the icon → **SceneBoard enumerates home entries by the stored skill
(`action.system.home`+`entity.system.home`), not by that derived flag.** The blocker is **61b-specific launcher state**,
exactly the outer's alternate branch — not the frozen installer, not the HAP.

### Why 61b specifically

- 61b has **13 `org.westlake.la0..la11`** launcher-experiment apps installed (+ their HAPs and `applauncher*.hap` in
  `/data/local/tmp`); each carries the same `entity/action.system.home` skill and populated 61b's grid.
- imehost is installed on 61b but **never entered the grid**: a `bm install -p` *update* (what was done earlier) does not
  trigger SceneBoard's add-to-grid, whereas a *fresh* install does (proven on 5ea). A **SceneBoard restart did NOT re-add
  it** (pid 2445→19059, still 0 icon over 14 pages) → the omission is persisted in SceneBoard's launcher store, not just
  an in-memory cache. SceneBoard's grid store is not a plain file under `com.ohos.sceneboard` (likely a distributeddata
  kvstore) — not cleanly clearable in-window.

### Fix plan (none touches the frozen `51e1` installer) — recommend option 1

1. **RT-preserving fresh reinstall of imehost (recommended, no 792 MB push)**: the RT lives at
   `…/org.westlake.imehost/files/a2hlab-source-…/` on the same `/data` fs as `/data/local/tmp`, so `mv` it out is an
   instant rename. Sequence: `mv RT → /data/local/tmp/rt-keep` → `bm uninstall org.westlake.imehost` →
   `bm install -p df385638` (**fresh** → SceneBoard adds the 今日头条 icon, as on 5ea) → `mv rt-keep → new files/` →
   `chown -R 20010053 + restorecon -R` (re-verify member SHAs) → foreground-tap → feed. Reversible; RT never leaves the
   board. (Caveat to handle: if the reinstall assigns a new uid, `chown -R` the RT to it.)
2. Full fresh reinstall + re-provision RT from `tt-rt.tar` (792 MB push) — simpler but heavy + hub-reboot risk.
3. Locate + clear SceneBoard's launcher grid store (distributeddata) for a clean rebuild — cleanest conceptually but the
   store wasn't a simple file; needs more spelunking.

Deliberately deferred option 1 to a clean full-budget window rather than a rushed end-of-window attempt (uninstall→install
→mv→chown→restorecon→tap is multi-step; a half-done run would leave imehost's RT mislabeled). 61b left intact: imehost +
RT untouched, SceneBoard restarted healthy, only serial `61b…` touched, not pushed. 5ea restored (imehost uninstalled).

---

## UPDATE 2 (2026-10-10 ~14:40) — fix ① executed: icon+front UNBLOCKED, but reinstall caused a uid regression that blocks the child

Outer approved fix ① (RT-preserving imehost reinstall) + laN cleanup. Executed on 61b. Two findings, one of them a
correction of my own earlier conclusion.

### Done
- **laN cleanup**: uninstalled exactly the 12 `org.westlake.la0..la11` experiment apps by name (total 231→219); imehost +
  the demo apps (`com.example.helloworld`, `com.a2hlab.bridge.zigzag`, `org.wikipedia`) untouched.
- **RT-preserving reinstall**: `mv` RT to same-fs staging (device id 66352, instant rename) → `bm uninstall imehost` →
  fresh `bm install -p df385638` → `mv` RT back → `chown -R` + `restorecon`. RT SHAs preserved (appspawn-x `a7a358c6`).

### Finding A (CORRECTION) — the "no icon" was a lock-screen scan artifact, not a grid/installer problem
Every "icon absent" scan I ran was **reading the lock screen** (`SCBScreenLock` re-fronts when no keeper runs; `uitest
dumpLayout`/`snapshot_display` then capture the lock, whose only text node is the battery "85"). Once I started
`onscreen_keeper.sh` (dismisses the lock every 4s) and verified `Focus window: 11` (SCBDesktop) per page, the **今日头条
icon is on desktop page 9** (`[673,1075][800,1107]`, `evidence/61b-toutiao/61b-icon-page9.json`). A `uitest uiInput click`
on the icon image (736,986) **fronted imehost0** (`Focus window: 33`, ZOrd 101, `61b-imehost0-fronted.png`). **The
foreground-tap front works.** This is the same lock-screen artifact as the 5cd HW "black" at the start of the day — the
decisive lever was the keeper, not the reinstall. (So fix ①'s reinstall was, in hindsight, not what unblocked the icon.)

### Finding B (REGRESSION I introduced) — OH reallocates the app uid on reinstall → Route B child won't spawn
`bm uninstall`+`install` gave imehost a **new uid `20011206`** (was `20010053`; OH allocates sequentially, not by bundle
hash). I chowned the RT and sed'd `run.sh`+`start-parent.sh` 20010053→20011206 (backups `*.pre-uid20011206.bak`), so the
chain is internally consistent — but the Toutiao child still **PARENT_BLOCKED** (`watchdog.sh:100`: the A2HSource socket
never comes up within 10 s after `source_app_namespace "$RT" 20011206 …`). The Route B sandbox (hash `c91d26…`, internal
app-data) was built for uid 20010053; a uid swap is deeper than ownership. **Net: the reinstall broke the child spawn.**

### Recovery plan (next window) — the icon/front path is proven; only the uid-consistent runtime remains
1. **Clean reprovision of Route B at a single consistent uid**: `rollback_toutiao.sh` (SAFE, never appspawn-x) →
   `provision_toutiao.SAFE.sh 61b…` (fresh, which installs host + extracts RT + stages + watchdog all under whatever uid
   OH assigns, self-consistent). Needs `tt-rt.tar` (792 MB push, or pre-stage on board). Then: run keeper → tap icon
   (page 9) → feed → scroll/article/3 cold starts.
2. Lighter but uncertain: debug why the A2HSource socket fails under 20011206 (may be a path/label the RT embeds for the
   old uid) — not worth it vs a clean reprovision.

**Lesson**: never uninstall+reinstall a uid-pinned host (OH doesn't preserve the uid); and always run the keeper / verify
`Focus window` ≠ SCBScreenLock before concluding a desktop icon is missing.

### 61b left
imehost installed (uid 20011206), RT preserved + uid-consistent scripts, **laN removed**, Route B + keeper stopped (SAFE),
appspawn-x daemon alive (23358), SceneBoard alive (21001), U13 autostart intact (`00_westlake_u13_recover.cfg`), desktop
healthy. Only serial `61b…` touched; not pushed.

---

## UPDATE 3 (2026-10-10 ~15:1x) — 上屏 PASS: Toutiao feed on screen via foreground tap, self-heal, HW coexist

Full reprovision (outer-approved) + the final uid fix landed it. **61b Toutiao Route B now lights on the physical screen.**

### Flow that worked
1. `rollback_toutiao.SAFE` (61b-admitted copy) → clean; `provision_toutiao.SAFE` → **792 MB tt-rt push survived the hub** (SHA ok), RT extracted, stage+watchdog deployed. Step-8 auto-front FAILed as expected (watchdog `aa start` = 10107101).
2. **uid reconciliation** (OH gave imehost `20011206`, not the bundle's pinned `20010053`, and won't reclaim it):
   - sed'd **all** `.sh` (run.sh, start-parent.sh, watchdog.sh, preseed_metasec48.sh, prepare_jit50.sh) `20010053`→`20011206` + `chown -R` RT.
   - **the decisive one: `request.bin` embeds the uid as a binary LE int (×2), not ASCII** — ASCII grep missed it; the child kept spawning as `uid=20010053` (parent.log) and couldn't render into the `20011206` host (alive but black). Patched `request.bin` LE `20010053`→`20011206` (both occurrences; `source_app_namespace`/`host_spawn` carry 0 embedded uid). Backup `request.bin.pre-uidpatch.bak`.
3. keeper on (dismiss lock) → tap 今日头条 icon image → imehost0 fronted (pid 29186) → watchdog `source_app_namespace` → asx-spawner → **child spawns uid=20011206** → state **READY** → feed.

### Acceptance (screenshots are ground truth; `evidence/61b-toutiao/`)
| item | result | evidence |
|---|---|---|
| 前台点击启动 | **PASS** | `61b-toutiao-cold1-feed.png` (2.99 MB — video feed, search/关注/点赞2667/评论725/分享) |
| 刷首页 + 点开文章 | **PASS** | `61b-toutiao-cold2.png` (推荐 feed: nav tabs, article body 「缴费基数上调…」, video card 张一鸣 06:21/331, bottom tabs); `-feed-scroll.png`, `-article.png` |
| 三次冷启 + self-heal | **PASS** | cold1/cold2/cold3; child 32391→4758→5836→6788, **host imehost0 29186 constant** across every child-kill (RUNBOOK #12 respected, appspawn-x never touched) |
| HW/ZZ 不退 | **PASS (HW)** | `61b-hw-coexist.png`; after `aa start helloworld`, Route B child + host 29186 + appspawn-x all still alive |
| laN pollution | **removed** | 12 `org.westlake.la0..la11` uninstalled |
| boot slot | **not enabled** (per instruction) | — |

### Left on 61b
Route B running (feed live, child respawns via watchdog), U13 autostart intact, appspawn-x + SceneBoard healthy, laN gone,
imehost uid 20011206 fully self-consistent (scripts + RT + request.bin). Keeper is flaky (dies intermittently; a re-tap/
swipe wakes the feed). Only serial `61b…` touched; not pushed. The request.bin binary uid is the one thing a future clean
reprovision must re-patch (or the bundle be rebuilt uid-agnostic).
