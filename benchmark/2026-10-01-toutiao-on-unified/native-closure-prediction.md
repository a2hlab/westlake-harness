# Toutiao native-closure static prediction (U10) — which `lib/arm64-v8a/*.so` resolve, which predict a wall

Static `llvm-readelf -d` of all **138** `.so` in `toutiao.apk` `lib/arm64-v8a/`. For each NEEDED we judge
resolution under **U10**: (a) APK-bundled; (b) `shared_sonames` = the current 6 **+ `libstdc++.so`** (wall-1,
master `504b66cea`); (c) OHOS/bionic base that must resolve for any native lib (`libc/libm/libdl/libc++`);
(d) none → **predicted wall**. Per-`.so` rows in `native-closure-prediction.csv`, sorted earliest-loaded.

## Headline: the Application-bootstrap closure resolves under U10
`libflipped.so` (rank 0 — loaded in `Application.attachBaseContext`, the U8 death-chain wall 1) NEEDED =
`liblog.so`(b) · `libm.so`,`libdl.so`,`libc.so`(c base) · **`libstdc++.so`(b, the U10 add)** → **no wall.**
Its only bionic UND symbol is `__android_log_print` (exported by `liblog.so`, in `shared_sonames`). **So the
wall-1 `libstdc++` fix is sufficient for Toutiao's native bootstrap**; the remaining walls are in
later/on-demand feature libs, not the first-frame path.

## Predicted walls: 23 / 138 `.so`, 12 distinct blocking NEEDED
Grouped by whether route-A can satisfy it (checked against tt-rt's system libs):

### A. Generic, route-A HAS it → add to `shared_sonames` (same one-line mechanism as wall 1)
| blocking NEEDED | # `.so` | note |
|---|---|---|
| **`libjnigraphics.so`** | **13** | standard NDK bitmap; route-A ships it. **Highest-value next add** (13 consumers, additive, generic). Likely the next wall once image-decode libs load. |

### B. Platform-internal, route-A HAS it but exposing to the app namespace is risky → do NOT blanket-add
| blocking NEEDED | # `.so` | note |
|---|---|---|
| `libart.so` `libbase.so` `libcutils.so` `libdexfile.so` | 1 (`libcvt.so`) | ART/platform internals; exposing them to app namespaces risks correctness/ABI. Only `libcvt.so` (a feature lib) needs them — defer; do not add to `shared_sonames`. |

### C. Genuinely missing on route-A (not in tt-rt system libs) → needs a provider, not a config line
| blocking NEEDED | # `.so` | consumers (feature) |
|---|---|---|
| `libGLESv2.so` | 6 | bytenn, lens, monitorcollector, sysoptimizer, texturerender, ttmplayer |
| `libGLESv3.so` | 3 | animax, krypton, lynx_helium |
| `libOpenSLES.so` | 2 | kryptonaurum, ttmplayer (cx-bms has an OpenSLES facade from the Mindustry fix — reuse) |
| `libaudioeffect.so` | 1 | kryptonaudioeffect |
| `libnapi_v8.so` `libv8_libfull.cr.so` | 1 | lynx_v8_bridge (Lynx/V8) |
| `libprofiler.so` | 2 | npth_fd_tracker, npth_ref_monitor (crash-monitor) |

## Load-order note (earliest first)
- **rank 0 `libflipped.so` — resolves (U10).** 
- The 23 wall `.so` are all rank 2 (not NEEDED by `libflipped`): feature/monitor libs — image decode
  (`libgifimage`, `libbdheif`, `libimagepipeline`, `libstatic-webp`, `libnative-filters`), video/player
  (`libttmplayer`), camera/effects (`liblens`, `libkrypton*`, `libanimax`), Lynx (`liblynx*`), neural
  (`libbytenn`), crash-monitor (`libnpth_*`), optimizer (`libsysoptimizer`, `libmonitorcollector`). Static
  analysis cannot pin their exact `System.loadLibrary` order; **none is on the `libflipped` bootstrap path**,
  so none blocks first-frame under U10. Which of them load during `onCreate`/first-frame (vs truly
  on-demand) needs a dynamic trace once Toutiao runs on U10.

## Recommendation (prediction only; no device this step)
1. **U10 (wall 1) is enough to get Toutiao's native bootstrap past `libflipped`.** Run Toutiao as an
   ordinary key on U10 and read the FIRST actual native wall it hits.
2. **Most-likely next generic wall = `libjnigraphics.so`** (13 consumers, route-A provides it): the fix is
   the same additive one-liner — add `libjnigraphics.so` to `native_bridge_policy.v1.json` `shared_sonames`
   — benefits any app using NDK bitmaps, no regression. Propose it only if the on-board run confirms an
   image-decode lib loads and fails on it.
3. Group C (GLES/OpenSLES/V8/profiler) = feature libs; address per wall only if they load before first
   usable UI, each with the regression gate. Do NOT expose group B (ART internals).
