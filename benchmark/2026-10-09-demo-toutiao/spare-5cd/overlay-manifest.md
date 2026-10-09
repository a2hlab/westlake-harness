# Step 1 — Route-B static overlay manifest (exactly what the ttbundle writes on a board)

Derived from `benchmark/2026-09-27-device-provisioning/provision_toutiao.sh` + the ttbundle contents (7/7 verified).
Everything Route B touches is under **one HAP sandbox + `/data/local/tmp`** — zero `/system`, zero frozen artifact.

## On-board writes
| # | On-board path | Source (ttbundle) | Note |
|---|---|---|---|
| 1 | HAP `org.westlake.imehost` (installed via `bm install`) | `source-host.hap` (df385638) | host window + launcher; sandbox `/data/app/el2/100/base/org.westlake.imehost/files/` |
| 2 | `…/files/a2hlab-source-c91d26bf…/` (RT) ← `tar xpf` | `tt-rt.tar` (755 MB, SHA 014c566e) | self-contained RT: **its own libart 78e34445, boot image, fw BCP jars, webview-t-lib, appspawn-x** |
| 3 | `…/RT/oat/arm64/toutiao.{art,odex,vdex}` (only with `--with-aot`) | `aot/*` | Tier-2 speed layer; feed renders without it (JIT). Omitted by default |
| 4 | `/data/local/tmp/a2hlab-app-c91d26bf…/` ← `tar xpf` | `tt-stage.tar` | `source_app_namespace`, `host_spawn`, `request.bin` |
| 5 | `/data/local/tmp/operator45/selfheal48/` ← `tar xpf` | `tt-wd.tar` | `watchdog.sh`, `start-parent.sh`, `spawn.sh`, `screen-gate`, `onscreen_keeper.sh` |
| 6 | `…/RT/private-tmp/asx` (mount point, created) | — | `source_app_namespace` bind-mounts `$RT/private-tmp→/data/local/tmp` then `$RT→/data/local/tmp/asx` **inside B's own mount namespace** |
| 7 | `/data/local/tmp/tt-prov/` (staging scratch) | — | tar landing dir; removable |

## Processes B starts
`watchdog.sh` (guardian, selfheal) → `start-parent.sh` → `source_app_namespace` (uid 20010053) → `/data/local/tmp/asx/run.sh` → the Toutiao Android child (`com.ss.android.article.news`); plus `onscreen_keeper.sh` (keyguard-dismiss daemon). **B does NOT use the host `appspawn-x`** — its child is parented by `source_app_namespace`.

## Conflict resolution vs the static README's predicted conflicts
- **#3 `/data/local/tmp/asx` (predicted SHARED)** → **RESOLVED**: B bind-mounts its own RT onto `/data/local/tmp/asx` *inside its private mount namespace* (provision step 6); the host-fs `/data/local/tmp/asx` is not overwritten. Confirmed on 5cd: host-fs `/data/local/tmp/asx/libart.so` is **absent** right now.
- **#6 `tt-rt.tar` (predicted UNKNOWN)** → now **present (7/7)** and is B's self-contained runtime, extracted *into the imehost sandbox*, not into a shared `/system` path.
- **#7 `/data/local/tmp/operator45` selfheal (predicted SHARED)** → B owns this path; on a board not running a unified selfheal it is B's alone. Rollback clears it.

## Board-safety finding (blocks running the stock scripts as-is)
`provision_toutiao.sh:40` and `toutiao_accept.sh` both do **`kill -9 $(pidof … appspawn-x)`**. RUNBOOK #12 (hard rule,
2026-09-30): *no lane may `kill -9` the appspawn-x main process* — OH init's `CheckOndemandService` NULL-derefs (SEGV@0x34)
and the **whole board goes down** (physical reboot needed). That kill is unnecessary for Route B (its child is parented by
`source_app_namespace`, not appspawn-x). **Fix shipped here**: `provision_toutiao.SAFE.sh` cleans only B's own
`com.ss.android.article.news / source_app_namespace / host_spawn` and leaves appspawn-x untouched; `rollback_toutiao.sh`
likewise never touches appspawn-x. These SAFE copies are what the on-board run uses.
