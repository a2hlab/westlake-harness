# 5cd suspect cluster: el2 SQLiteCantOpen (create-path) — root-cause static/log analysis (cc-t3 #91)

**VERDICT (refined with cc-wiki's 61b repro, 2026-10-10 17:09): the cluster is an enforced-sandbox PATH-NONEXISTENCE bug, not a label/create-permission one. The westlake adapter hands the app its Android dataDir + keystore at the RAW HOST path `/data/app/el2/100/base/<pkg>`, but the OH sandbox exposes that CE data only at the SANDBOX path `/data/storage/el2/base`. Before today the `appdata-sandbox.json` was mis-labeled, so appspawn-x never loaded it → no rebase → the child saw host `/data` → the raw path worked. Today's v2 autostart fixed the json label (→`system_etc_file`), which turned sandbox enforcement ON, rebasing the child into `/mnt/sandbox/100/<pkg>/` where the raw `/data/app/el2/...` path does not exist → SQLite `CANTOPEN "doesn't exist"`. The "working" demo had the sandbox silently disabled.**

cc-wiki 61b evidence (17:09): 61b now REPRODUCES (studytracker/listmaker CANTOPEN) even though the DB files exist (10-01/10-03), dir owner=BMS uid, label appdat, and there is NO normal_hap avc in the window — i.e. not a policy denial. libresudoku's `-shm` was last written 2026-10-10 00:22 (before this morning's v2 reboot), i.e. it COULD write before enforcement. So the fork is TODAY's reboot/v2-autostart state (appspawn-x now preloads the correctly-labeled `appdata-sandbox.json` → sandbox truly in effect), not DB-exists-vs-absent and not the chcon label.

(Superseded earlier draft hypothesis: "appdat create-denial / fresh-create". It was directionally right that the regression is sandbox/label-triggered, but the mechanism is raw-host-dataDir vs sandbox-path under newly-enabled enforcement, confirmed by the json mount-paths + the raw paths the adapter logs. No board was touched by this lane; 5cd evidence is the existing run; 61b is cc-wiki + historical t3 logs.)

## Numbers (observed-89 run, resume-organicmaps/compare-observed-89)
- **37 / 89** observed keys' hilog contain `SQLiteCantOpenDatabaseException` / `CREATE_IF_NECESSARY`.
- **25 / 26** suspect keys have it (the lone exception: **opencamera** — different failure).
- All 25 share one signature (studytracker shown; cv2 pid 21662, 15:39:48–52):
  - `SQLiteCantOpenDatabaseException: Cannot open database '/data/app/el2/100/base/<pkg>/databases/<db>' with flags 0x30000000: Unable to deduct failure reason`
  - `Caused by: ... unknown error (code 14 SQLITE_CANTOPEN): Could not open database`
  - stack: `Room → FrameworkSQLiteOpenHelper.getWritableDatabase → SQLiteDatabase.openDatabase(CREATE_IF_NECESSARY) → SQLiteConnection.open` (native open/create).
  - then `AppSpawnXJava [W-ROOM-SURVIVE] UNCAUGHT in thread 'Thread-1' (main=true) ... main-thread fatal -> preserving kill semantics` → **exit 1** (W-ROOM-SURVIVE intentionally kills on a main-thread DB-open fatal).
  - app uid is **per-app** (studytracker = 20011117, bundle com.edward.studytracker).

## First divergence (outer ①): 61b opens, 5cd cannot create
- 61b historical t3 hilogs — `cv2-com-edward-studytracker` (demo-baseline/t3/plans-v2/capture-03), `cv2-com-harr1424-listmaker` (same), `cv2-com-kaajjo-libresudoku` (×2) — all **CANTOPEN = 0** (DBs present/built 2026-10-09, app-created; open path only).
- 5cd this run freshly installed + sandbox-prepped these apps → the DB does not pre-exist → the app hits the **CREATE** branch, which fails. So the fork is create-vs-open, not a generic "el2 invisible".

## What is NOT the cause (ruled out from logs)
- APPSPAWN sandbox binds that fail `errno:2`/`errno:13` (hiai, system_optimize, **el2/distributedfiles**, ark-profile, shader_cache, **el2/share**, themes, systemResources) are the **standard optional-bind warnings every OH app emits**, incl. apps that light. There is **no failed el2 `base` (CE data) bind**. `[ROUTE-A] child diagnostic fd unavailable: errno=13` is a benign diagnostic-fd warning.
- No explicit `EACCES`/`ENOENT`/`mkdir errno` is surfaced by SQLite ("Unable to deduct failure reason" = SQLite's own errno probe on the path also came back inconclusive → consistent with a dir the app may traverse but not create in, or a label/CE mismatch).
- Policy: outer confirmed normal_hap→{appdat, data_app_el2_file, data_app_file} **search** allow. NOTE: **create/add_name/write was NOT verified** — this is the open question below. (No queryable sepolicy binary exists offline in the repo — only text policy.patch/policy.json — so create-perm sesearch must run on-board.)

## sandbox-command.sh prep (the suspected lever)
Pre-run prep `mkdir`s `/data/app/el2/100/base/$PKG/{databases,...}`, then `chown -R $APP_UID:$APP_UID`, `chmod 0700` base / `0770` database, and `chcon -R u:object_r:appdat:s0` the el2 base+database trees — with a documented OH-6.1 toolbox caveat that `chcon -R` labels only the first child, so it re-runs per-item via `find -exec chcon`. Net on 5cd: `databases/` is owned by the app uid, 0700, **labeled `appdat`** (prep-seeded), and **empty**. On 61b the same dir was **created by the app itself** on 10-09 (installd/app default context), and already holds the DB.

## The mount map (offline proof)
`appdata-sandbox.json` (frozen `oh-appspawn-security-v7`) maps, under `app-base` mount-paths:
- L102-103: `src /data/app/el2/<uid>/base/<variablePackageName>` → `sandbox-path /data/storage/el2/base` (bind,rec)
- L117-118: `src /data/app/el2/<uid>/database/<pkg>` → `/data/storage/el2/database`; L107-108 log → `/data/storage/el2/log`
- **No mount-path has `sandbox-path` = `/data/app/el2/...`.** So in the enforced child namespace the CE data exists ONLY at `/data/storage/el2/base`; the raw host path `/data/app/el2/100/base/<pkg>` is NOT present.

But the adapter hands the app RAW host paths (studytracker hilog `[B43-BIND]` / `[WL-KEYSTORE]`): DB at `/data/app/el2/100/base/<pkg>/databases/...`, keystore at `/data/app/el2/100/base/<pkg>/no_backup/...`. (sourceDir is el1 `/data/app/el1/bundle/public/<pkg>/android/base.apk`, which IS mapped → the apk loads; only the el2 data writes break.)

## Root cause (ranked)
1. **Adapter uses the RAW host el2 dataDir instead of the sandbox path (confirmed mechanism).** Android `ApplicationInfo.dataDir`/keystore resolve to `/data/app/el2/100/base/<pkg>`, which is the sandbox SRC, not the in-child `sandbox-path` `/data/storage/el2/base`. Under newly-enabled enforcement the raw path is absent in the child → every el2 write (Room/SQLite CREATE, keystore) fails. Systematic across all el2-writing apps → the cluster; opencamera has no Room DB so it differs. Trigger = today's v2 json-label fix enabling enforcement.
2. **Trigger/enabler: `appdata-sandbox.json` label.** Pre-v2 the json was mis-labeled → appspawn-x `PreLoadAppSandboxCfg` couldn't read it → sandbox not enforced → child saw host `/data` → raw dataDir worked (libresudoku -shm 00:22). v2 relabel (→`system_etc_file`) made appspawn-x load+enforce it. (Same lever as the 61b seccomp wall: correct json label = appspawn-x actually uses the cfg.)
3. (Not the cause, from cc-wiki: not SELinux/appdat — no avc, DB files exist, owner/label unchanged; setenforce is predicted NOT to help since it's mount-namespace path-nonexistence.)

## Minimal board experiments to settle it (cc-wiki is already on /proc/<pid>/root + setenforce)
1. **Child-namespace view (decisive):** for a live crashing app pid, `ls -ld /proc/<pid>/root/data/app/el2/100/base/<pkg>` (predict: ENOENT — absent in child) vs `ls -ld /proc/<pid>/root/data/storage/el2/base` (predict: present + writable by app uid). If so → raw-dataDir-vs-sandbox-path confirmed.
2. **setenforce 0 single-variable (cc-wiki running):** predict it does NOT fix CANTOPEN (path-nonexistence is mount-ns, independent of SELinux mode) → rules out a policy cause.
3. **dataDir origin:** dump the adapter's resolved `ApplicationInfo.dataDir` (B43-BIND already shows raw el2) and confirm Android `getDatabasePath` builds on it; confirm `/data/storage/el2/base` is the writable twin in-child.

## Suggested fix direction (pending confirmation)
Primary: the westlake adapter must resolve the Android app dataDir (and keystore path) to the **sandbox path `/data/storage/el2/base`** (the in-child CE mount), not the raw host `/data/app/el2/100/base/<pkg>`. Then Room/SQLite create under `/data/storage/el2/base/databases`, which the sandbox maps to the host — the standard OH flow. Stopgap alternative (worse): add a mount-path exposing `/data/app/el2/<uid>/base/<pkg>` at the same `sandbox-path` so the raw path resolves in-child. Note this is a **pre-existing adapter bug that v2's correct sandbox enforcement exposed** — the frozen demo baseline was captured with the sandbox silently off, so a full-128 re-baseline under real enforcement is warranted once fixed.

Evidence: `westlake-harness-tools-inventory/benchmark/2026-10-10-5cd-demo-regression/resume-organicmaps/{compare-observed-89,observed-89/.../cv2-com-edward-studytracker/hilog.txt}`; 61b t3 `westlake-harness-tools-inventory/benchmark/2026-10-09-demo-baseline/t3/plans-v2/capture-03/...`; prep `benchmark/.../sandbox-command.sh`.
