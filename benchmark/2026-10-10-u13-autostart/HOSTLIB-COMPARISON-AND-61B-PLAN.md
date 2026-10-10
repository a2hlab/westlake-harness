# Host-lib comparison (5cd vs 61b) + 61b autostart plan

Read-only comparison (2026-10-10, zero board writes) answering the outer's ACK(91) 07:10: why 5cd apps stay white but
61b should render. Plus the offline-ready 61b autostart variant and the acceptance plan (board step pending an
approved time window).

## 1. Host-lib comparison — the discriminator is `libinstalls.z.so`

Every route-a host lib is a **physical file** (`/proc/mounts` bind=0) on **both** boards — none is a runtime mount.
They are identical on both boards **except `libinstalls.z.so`**:

| Path | bind (5cd / 61b) | 5cd SHA | 61b SHA | |
|---|---|---|---|---|
| `/system/lib64/libinstalls.z.so` | 0 / 0 | `2c9a5294` **stock** | `51e1b525` **route-a** | **← discriminator** |
| `/system/lib64/platformsdk/libinstalls.z.so` | 0 / 0 | `2c9a5294` **stock** | `51e1b525` **route-a** | **← discriminator** |
| `/system/lib64/libbms.z.so` | 0 / 0 | `6aadb8b4` | `6aadb8b4` | identical |
| `/system/lib64/libapk_installer.so` | 0 / 0 | `7048c7c5` | `7048c7c5` | identical |
| `/system/lib64/libappms.z.so` | 0 / 0 | `182937bb` | `182937bb` | identical |
| `/system/lib64/libappspawn_client.z.so` | 0 / 0 | `f4df7769` | `f4df7769` | identical |
| `/system/lib64/libwestlake_hap_domain_wrapper.so` | 0 / 0 | `06c35353` | `06c35353` | identical |
| `/system/bin/appspawn-x` (56-layer) | 1 / 2 (bound) | `2a87118e` | `2a87118e` | route-a (mount) |
| `/system/android/lib64/liboh_adapter_bridge.so` | 1 / 0 | `8ab85446` (5cd boat) | `84695d62` (61b base, physical) | — |
| `/system/android/framework/oh-adapter-runtime.jar` | 2 / 1 | `6333bcab` (5cd boat) | `bbc3f530` (61b base, mount) | — |

**Conclusion.** `libinstalls.z.so` is the bms installer that marks apps "anco" (route-a). 61b has it **physically in
/system** (`51e1b525`), so it survives reboot → bms marks the pre-installed apps anco → AMS routes them to the
AppSpawnX socket → appspawn-x spawns and renders. 5cd has it **physically stock** (`2c9a5294`), so apps are never
marked anco → white. This is **not** an autostart-mechanism difference (the 56-layer replay is identical on both and
excludes `libinstalls`); it is a persistent-/system-contents difference, exactly as the outer stated. **5cd's app-render
failure does not extrapolate to 61b.**

## 2. 61b autostart variant — offline-ready (U13 56 layers + Toutiao placeholder, NO BoatAttack)

- `payload/scripts/westlake-u13-recover.sh` — shared, unchanged (replay 56 + preserve ondemand appspawn-x listener).
- `payload/u13-recover-table.json` + `.plan` — shared (the 56-layer SHAs are board-independent; verified 56/56 on 5cd).
- `payload-61b/init/00_westlake_u13_recover.cfg` — **recover service only** (1 job + 1 service); documents a reserved
  **Toutiao-overlay placeholder** slot (留位, not wired this round).
- Installer run with **`WITH_BOAT=0`** → skips all BoatAttack staging/placement; `SUPERSEDE=1` → supersedes the stale
  `00_pr03_runtime_recovery.cfg` (+ `pr03-runtime-recover.sh`) with backup. `wl_toutiao.cfg.disabled` is left alone
  (init ignores the `.disabled` extension; the supersede loop only scans `*.cfg`).
- KA: 31/31 (adds 61b-cfg checks: recover-only, no boat-overlay service, no setenforce, Toutiao placeholder, min caps).

61b pre-state (read-only): boot=true, ROM 6.1.0.31; init cfgs `00_pr03_runtime_recovery.cfg` + `wl_toutiao.cfg.disabled`;
appspawn-x currently running (active deploy — will be ondemand-down after reboot); demo bundles installed =
**HelloWorld, ZigZag, Toutiao (`com.ss.android.article.news`)**.

## 3. 61b board step (pending an approved time window — report before touching 61b)

Announce → wait ~2 min → LOCK 61b → stage (payload scripts + table + plan + the 61b cfg; **no boat-artifacts**) →
`DEPLOY=… ALLOW_REMOUNT=1 SUPERSEDE=1 WITH_BOAT=0 sh install-…` → verify INSTALL_OK (56/56, pr03 superseded, cfg label)
→ **real reboot** → (no Mac interaction) read-only verify:

1. receipt `state=READY`, `sys.westlake.demo.u13.ready=true`, 56/56 replayed;
2. ondemand appspawn-x listener intact (`/dev/unix/socket/AppSpawnX`, `00010000`, `660:0:6005`);
3. 319 fingerprint (expect 319/319 exact on 61b — the evidence was captured on 61b, no boat overlay this round);
4. foundation/bms maps include the route-a host libs (esp. `libinstalls` `51e1b525`);
5. **tap HelloWorld / ZigZag / Toutiao → screenshots lit** (ground truth).

Then disable+reboot → bare /system, re-enable+reboot → U13-prepared (kill-switch validation, as on 5cd). UNLOCK, facts,
PROGRESS(91).

Estimated window: **≤30 min** (install + 3 reboots + reads + 3 screenshots). ⚠ remount/reboot may drop 61b from USB —
may need a user re-plug (61b once vanished from enumeration on a foundation restart; RUNBOOK §11).
