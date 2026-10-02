# What the old Toutiao route provided that the BMS + route-A path does not (offline, feature-level)

#90, user-directed (2026-10-02 17:1x), read-only evidence, no board. The 2026-09-28 old route put the Toutiao feed
on screen in **~20 s (5cd) / 25 s (5ea)** with `provision_toutiao.sh`, Tier-1 (no app AOT). Today's route-A run
(window5, 61b, 2026-10-02 17:05, runtime `d6848fa2c989`) is still inside `ArticleApplication.attachBaseContext`
12 s after bind. Wall 1 is "not finished by t20". This compares the two route-wide, item by item, and ranks the
gaps by how likely filling them gets Toutiao on screen: `diff.csv`, 17 rows.

## What was wrong first

- **The 10-01 copy-list compared 5 file SHAs and the wall order, and so missed the largest difference.** That
  difference is not a file. **The old route ran Toutiao under ART JIT; route-A runs every app on the interpreter.**
  - Route-A hard-sets `APPSPAWNX_NO_JIT=1` in `appspawn_x.cfg:61` and `main.cpp:123`.
  - `test_production_config.py:47` and `verify_generation.py:175` *require* that setting. Its origin is a comment:
    "2026-05-01 G2.14n DIAGNOSTIC: disable JIT".
  - The 09-25 old-route child compiled with JIT: `[WESTLAKE-OH-JIT] memfd RX denied (13); using ART anonymous
    cache`, 3.3 MB JIT code (`evidence/old-stderr-lines.txt`, child.stderr:23 / :21754).
  - Today's hilog:28007 reads `ART JIT DISABLED via APPSPAWNX_NO_JIT=1`.
  - There is no app AOT on either side, so the old feed time was JIT alone. The current libart (`59e1bb45`) also
    lacks the OH JIT patches that the old libart (`78e34445`) has (`WESTLAKE_OH_JIT_*`).
- **"Toutiao's native libs fail because musl lacks bionic symbols" is half the story.** Route-A already has a
  bionic ABI provider, `libwestlake_native_abi.so`, and `libbionic_compat` exports `__system_property_read`. But:
  - `libapp_native_loader` places an app in the domain that loads that provider (`dlopen_ns … NOW|GLOBAL`) only if
    the app is on a **hard-coded list of 13 packages** (`app_native_loader.c:62`, `native_cluster_path`).
  - Toutiao is not on it. Its libs load into a plain `westlake.anl.app.*` namespace with no global ABI provider.
    `libbionic_compat` is shared there by name only, so libmetasec still misses `__system_property_read`.
  - The old route made `libwebview_bionic_shim.so` process-wide (LD_PRELOAD) and preloaded it into libart's
    `westlake_android_app` namespace.
- **The old route did not avoid Mira's early PPMP failure; it avoided caching it.**
  - The old `AdapterIAM-stub` (direct launch) leaves `getContentProvider` unhandled and returns null. Mira's early
    lookup fails, but nothing is cached, and the real PPMP answers after `installContentProviders`.
  - Route-A answers with an OH DataShare bridge that ActivityThread caches (`already published as …pm.PPMP`,
    hilog:32894).
  - The old run also logs "mira plugin not loaded" (old-stderr:2751), so the plugins are not on the first-frame
    path.
- **Route-specific machinery is not the gap.** These do not explain the old route reaching the feed:
  - host HAP sub-window, bind mounts, fixed uid, `request.bin`;
  - 7 patched app libs (hollow metasec/npth, …) and the slack/gwp/canary libs;
  - preseed metasec, the private WebView, the consent-tapping watchdog.

  They target the #48 crash rate *after* the feed or the operator verdict. They are Toutiao-only and are not ported.

## Ranked gaps (`diff.csv`)

| # | item | old route | route-A now | fix layer | wall-1 effect | Toutiao-only? |
|---|---|---|---|---|---|---|
| 1 | **JIT** | JIT on (`APPSPAWNX_JIT_BASELINE`, OH anon-cache fallback; file-backed cache #50 opt-in) | `APPSPAWNX_NO_JIT=1`, enforced by the production gate; libart without OH JIT patches | native (libart `jit_memory_region`) + config (cfg/main.cpp/gate tests) + sandbox `code_cache` dir | **high**: 12 s of app init on the interpreter | no |
| 2 | **bionic ABI provider** | shim 85c789f4 process-wide (73 syms) + `westlake_android_app` ns for 22 libs | native_abi d2053066 (26 syms), GLOBAL only for 13 hard-coded packages | native (`libapp_native_loader` selection by imports, native_abi exports) | medium: `__errno`×24, `__cmsg_nxthdr`×5, `__system_property_read`×4 relocation failures during attach; Cronet dead | no |
| 3 | own-provider answer before bind | null, not cached | cached DataShare bridge | JAR, **already in U12** (OwnProviderLocal) | medium | no |
| 4 | bind providers | 43 (main process) | 54 (incl. 11 `:push`/`:smp`/stub) | JAR (canRunHere filter) | low-medium | no |
| 5 | native network compat | LD_PRELOAD `libandroid_native_network_compat` for Cronet | absent | native | low for frame, high for feed | mechanism no, target list yes |
| 6 | Settings holders | Proxy in 3 holders | hollow | JAR, **already in U12** | low | no |
| 7 | network/permission state | `connectivity`→adapter + OH helper libs | ONLINE-CM fetcher; raw `getService` null | JAR + native helpers | low | no |
| 8 | BCP classes | 9 jars incl. real conscrypt | 9 jars, no conscrypt | JAR (stubs) | low | no |
| 9 | namespace model | one default ns; 16 plain `dlopen` | sealed child + per-app ANL domain | native | (covered by #2; wall-1 libstdc++ now resolves) | no |
| 10 | `vm.max_map_count=1048576` | watchdog sets it | unset | config | none | no |
| 11-17 | conscrypt, launch model, app AOT, patched app libs, LD_PRELOAD libttcrypto, private WebView, on-screen ops | see `diff.csv` | | | none | 13-17 yes |

**Prediction for wall 1:**
- **Row 1 is the only item that plausibly turns "still in attachBaseContext at t+12 s" into a first frame by t20.**
  The same app init under JIT reached the feed in 20-25 s on the old route, consent tap included.
- Rows 2-4 shave time and keep TTNet / Mira working. Row 2 and row 5 are what the feed needs for content.
- Rows 3 and 6 are already in the U12 runtime jar (`3bca82c5`).
- Row 1 changes every app's startup, so it needs the full sweep and the G2.14n SIGILL family re-checked before it
  joins the unified state.

## Per question

1. **Libraries: where, which loader** (`inventory.csv`, 479 files, built by `inventory.py` from the MANIFEST-checked
   bundle):
   - 131 app libs are byte-identical to the APK copies BMS extracts today; 7 were patched by the old route; 5 are
     old-route extras.
   - 58 runtime natives: 24 have a same-named file today, all with different SHAs. 34 are absent by name; some are
     re-expressed under other names, and the hilog shows which actually fail (row 2).
   - Old loaders: appspawn-x plain `dlopen` (default namespace); libart's source loader for `System.loadLibrary`;
     libart's `westlake_android_app` namespace for the 22 `WESTLAKE_ANDROID_NATIVE_TARGETS`; LD_PRELOAD for 3 libs;
     the BCP boot image.
   - New loader and mapping: window5 `maps-t5-10020` / hilog.
2. **Namespaces** (`evidence/open-sites-{old,new}.txt`, `scripts/lab/open_site_scan.py`):
   - Old appspawn-x a7a358c6 has 16 open sites, all plain `dlopen` into the caller's default namespace, with no
     namespace edges.
   - Host 65cc3535 has 8 sites:
     - `StockCreateConfiguredNamespaces`: sealed child plus `westlake.anl.app.*`, inheriting
       `libc:libdl:libm:libEGL:libGLESv3:libsurface.z:liboh_android_runtime:libbionic_compat:liblog:libc++:libstdc++:libOpenSLES`
       from default;
     - `dlopen_ns` of native_abi / liboh_android_runtime / libOpenSLES GLOBAL into the selected domain;
     - libbionic_compat NOLOAD probes.
3. **Java layer** (`java-classes.csv`, `java_classes.py`):
   - Toutiao references 2016 platform types. 23 exist only in the old BCP: 6 are added by the U12 stubs, and 17
     remain (bluetooth 9, `android.net.nsd` 5, NetworkStatsManager, WifiP2pManager, 2 MediaStore inner classes).
   - 61 are in neither, mostly `org.apache.http` legacy.
   - Window5 shows no NoClassDefFound or ClassNotFound for Toutiao.
4. **Providers and services**: row 3 explains why the old route passed Mira (null, uncached); see also rows 4, 6
   and 7. The old route answered `connectivity`, `permissionmgr` and `audio` with adapters backed by OH helper libs.
   Route-A binds 12 local services but returns null for raw `getService("connectivity")` (window5 :31181).
5. **Process and environment**:
   - Old: direct launch under a host HAP window, a fixed uid, JIT on, `max_map_count` raised, and a keyguard keeper.
   - Route-A: BMS + `ScheduleLaunchAbility`, JIT off, sandbox prepared by the runner.
   - Both reach `ensureBindApplication` within 1 s of the child starting, so launch mechanics are not the gap.

## Rule set down

- **Compare runtime configuration, not just files.** A route diff must include the ART option set (JIT/AOT/
  verify), process-wide env (LD_PRELOAD, loader env) and the per-domain selection logic. Today's largest gap
  (JIT off) and the second (ABI provider gated by package name) are both invisible to a file-SHA comparison.
- **A "DIAGNOSTIC" switch that a production gate *requires* is a finding to report, not a baseline.** List such
  switches with their origin before attributing slowness to an app.

## Files

- `diff.csv`: 17 ranked rows (columns: old provides / now / gap / fix layer / generic fix and source / wall-1
  effect / Toutiao-only hack / evidence). `make_diff.py` writes it plus `results.json` and re-checks the counts it
  quotes.
- `inventory.csv` (`inventory.py`): every old-bundle file with board path, SHA, category, old loader, today's
  same-named file, SHA, mapping.
- `java-classes.csv` (`java_classes.py`): Toutiao's platform type references against both BCPs.
- `evidence/`:
  - `old-run.sh`: the old env;
  - `old-stderr-lines.txt`: the 09-25 old-route child, line-numbered;
  - `window5-toutiao-lines.txt`: today, line-numbered;
  - `abi-symbols.txt`: shim vs native_abi vs compat, plus per-lib needs;
  - `open-sites-{old,new}.txt`.
- Old-route evidence caveat: no old-route maps or hilog of the 9-28 on-screen run survive locally. The old
  side's runtime facts come from the same runtime family's 09-25 Toutiao child stderr on 5ea, and from the
  bundle itself.
