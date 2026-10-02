# U13 dead-keys recheck: measured U13 first-fatals vs U14/U15 ownership

#90, offline, no board (window3 wrapping up — not touched). The cc-t3 cluster table (`master 49e6f805da
benchmark/2026-10-03-u13-first-fatal-clusters`) had many dead keys on U12 data only; U13 window1/window2/window2-61b
have now run. This re-reads each key's **U13** hilog first-fatal + earliest wall and judges, per the existing U14/U15
deliverables, who U14 moves / who waits for U15 (Bitmap / M3 / mindustry host / compat v3) / who is unowned.
(`evidence/u13-first-fatals.txt` = the raw per-key extraction; `evidence/immich-verifyerror.txt` = the immich
VerifyError mechanism + min-fix.)

## Per-key table (U13 measured)
| key | board/win | bind | U13 first-fatal | earliest wall | disposition |
|---|---|---|---|---|---|
| **fd-saber** | 61b/W2 | OK | **ALIVE-WHITE** (t5/t20 screenshots full-screen white, process alive — corrected 07:06; BIND OK + Impeller fallback only mean "did not crash", not "on screen") | window published, activity terminates, ~0 frames | **unowned white** — see `u13-white-saber-x`. **NOT** the U14 Flutter EGL wall; `Failed to load GLES`/`viewRoot null` are lit-shared red herrings |
| **x** (`com.twitter.android`) | 61b/W2 | OK (relaunch) | **ALIVE-WHITE** (t5/t20 screenshots full-screen white, process alive — corrected 07:06; BIND OK only means "did not crash") | window published, activity TerminateAbility ×2 + relaunch, ~0 frames | **unowned white** — see `u13-white-saber-x`. The C9 ITelephonyRegistry NPE *is* gone (U13 JAR), but the app still does not render. Note: key "x" = Twitter/X, not a Compose app |
| **toutiao** | 61b/W2 | OK | SIGSEGV (`platform-single`) at the **ICU** load; then NPE `PermissionManager.shouldShowRequestPermissionRationale` | `libmetasec_ml __system_property_read` reloc (earliest, non-fatal); **`load libicui18n.so failed`** 1 line before the segfault | **U14 app-ns 341c + ICU shim** (libicui18n visibility + `_74` shim) moves the ICU segfault; next = Lynx/V8 (`toutiao-next-wall`); residual `PermissionManager` NPE (framework stub) |
| **privacybrowser** | 5ea/W1 | OK | IAE "can't create bitmap without a color space" | (CoroutineStart CNFE, benign) | **U15 #1 Bitmap framework** (`u15-framework-bitmap`) |
| **mcdonalds** | 61b/W2 | FAILED | bind FAILED → NPE SplashActivity (`DataSourceModuleProvider.v()` null, **downstream**) | **`librealmc.so _ctype_`** reloc (Realm) | **U15 compat v3 / native_abi v2** (`_ctype_` in native domain). The Java NPE is downstream of the Realm init failure |
| **fd-im-vector-app** | 5ea/W2 | FAILED | bind FAILED → `librealm-jni.so.10.19.0 _ctype_` ULE | **`librealm-jni _ctype_`** reloc (Realm) | **U15 compat v3 / native_abi v2** (`_ctype_`) |
| **vlc** | 5ea/W1 | OK | vlcjni ULE `libvlc.so __pthread_cleanup_push` → app exit | `libc++_shared.so strtoll_l` reloc | **U15 compat v3 / native_abi v2** — vlc is native_cluster-enrolled; `__pthread_cleanup_push`/`strtoll_l` are the same bionic-export family as `_ctype_`. **Correction:** cluster said "U14 native_abi 7605812c moves"; 7605812c lacks `_ctype_` (DIGEST 738) and these too → needs the v2 export set + NEEDED closure |
| **immich** | 5cd/W1 | FAILED | **VerifyError `A2.b`** (bind FAILED); 2nd wall libcronet `ATrace_beginSection` | VerifyError (`b7.a.D` / Unresolved `d7.c`) | **unowned — new min-fix:** `d7.c implements android.net.nsd.NsdManager$DiscoveryListener`, **NSD absent from route-A BCP** → d7.c unresolvable → verify-reject. Fix = NSD BCP stubs (FZ-007/008 pattern). 2nd wall ATrace = U15 #3 (shelved); immich lights only when BOTH done |
| **glmark2** | 61b/W2 | OK | **SIGABRT — JNI `GetLongField`** in `libglmark2-android.so getSceneInfo` | JNI abort (no reloc wall) | **unowned — cluster prediction FALSIFIED:** C3 predicted "U13 runtime 18763dd4 (GetLongField) moves"; under the U13 runtime glmark2 **still** aborts in `GetLongField` (its app-native `getSceneInfo` path, distinct from the Flutter GetLongField U13 fixed) |
| **chessclock** | 5cd/W1 | OK | `WindowManager$InvalidDisplayException` "the specified display can not be found" (addView) | (CoroutineStart CNFE, benign) | **unowned** — display/window: addView can't find the display; also earlier NSME `ActivityManagerAdapter.nativeConsumeConnectionFailure(I)Z` (a JAR stub gap). Not M3 (that's GLSurfaceView EGL) |
| **fd-api** (`com.termux.api`) | 5ea/W1 | OK | IllegalStateException "You need to use a Theme.AppCompat theme" (start TermuxAPIMainActivity) | (bg `LocalSocketImpl.bindLocal` ULE, non-fatal) | **unowned / probe** — AppCompat-theme issue (`u13-java-walls-2` theme probe); an app-theme/manifest matter, not a runtime wall |

> **Correction (outer 07:06, on-board re-judged):** fd-saber and x in 61b window2 are **alive-white** (t5/t20
> screenshots full-screen white, process alive), **not lit**. BIND OK / Impeller fallback / no-crash in the log only
> mean "did not crash", not "on screen" (AGENTS: screenshots are ground truth). Their white mechanism is in
> `benchmark/2026-10-03-u13-white-saber-x` — both publish a window session but the activity self-terminates and renders
> ~0 frames; the `Failed to load GLES`/`viewRoot null` markers are **lit-shared red herrings** (refuted by the
> separation table). Rows + summary below are corrected accordingly.

## Disposition summary
- **BIND progressed under U13 but still alive-white** (not lit): **fd-saber** and **x/Twitter** — window published,
  activity TerminateAbility + ~0 frames (`u13-white-saber-x`). The U13 JAR *did* clear x's C9 telephony NPE (BIND OK),
  but x still does not render.
- **U14 moves**: **toutiao** (app-ns 341c + ICU shim → past the ICU segfault; next Lynx/V8). (x's residual `libGLESv2`
  for libtwittermedia → U14 app-ns, but that is not why x is white — see `u13-white-saber-x`.)
- **U15 waits**: **privacybrowser** → Bitmap #1; **mcdonalds / fd-im-vector-app / vlc** → compat v3 / native_abi v2
  (the `_ctype_` + bionic-export family in the native domain); **immich** → NSD BCP stubs (new, below) + ATrace (U15 #3).
- **Unowned / needs a new owner**: **glmark2** (GetLongField JniAbort — U13 prediction falsified), **chessclock**
  (InvalidDisplay + ActivityManagerAdapter NSME), **fd-api** (AppCompat theme probe), **immich** (NSD), **fd-saber /
  x** (alive-white, activity-terminate/no-render — `u13-white-saber-x`).
- **M3** (GLSurfaceView EGL IAE, `u15-runtime-m3`) owns **none** of the 11's *current* first-fatal — glmark2 is a
  GLSurfaceView app but its U13 wall is the `GetLongField` JniAbort, which precedes any EGL IAE (M3 would be its *next*
  wall).

## Corrections to the cluster predictions (the value of this recheck)
1. **glmark2 — FALSIFIED.** C3 "U13 runtime GetLongField moves" is wrong for glmark2: it still SIGABRTs in
   `GetLongField` under the U13 runtime (app-native `getSceneInfo`, a different call site than the Flutter GetLongField
   U13 fixed). fd-saber (the other C3) cleared the SIGABRT but is **alive-white**, not lit (next).
2. **fd-saber — corrected to alive-white** (outer 07:06, on-board). It cleared the C3 SIGABRT but did **not** light: t5/t20
   screenshots are full-screen white, process alive. The "lit via Impeller fallback" claim was wrong — BIND OK + Impeller
   fallback only mean "did not crash"; the activity self-terminates and renders ~0 frames. The `libvulkan`/`libGLESv3`
   load-fail and `Failed to load GLES` markers are **shared with lit keys** (separation refuted). Mechanism in
   `benchmark/2026-10-03-u13-white-saber-x`; it is **not** the U14 Flutter EGL (`eglCreateWindowSurface`) wall.
3. **vlc — owner corrected.** Not "U14 native_abi 7605812c"; the real first symbols (`__pthread_cleanup_push`,
   `strtoll_l`) are the bionic-export family that 7605812c lacks → **U15 compat v3 / native_abi v2** with the NEEDED
   closure (DIGEST 741).
4. **mcdonalds — root is the Realm `_ctype_` wall, not the Java NPE.** The `DataSourceModuleProvider.v()` NPE is
   downstream of the `librealmc _ctype_` ULE (androidx Startup fails → provider null).
5. **toutiao — progressed to BIND OK** under U13; the first-fatal is now the ICU segfault (U14 app-ns + ICU), with a
   residual `PermissionManager` NPE behind it.
6. **immich — concrete owner found** (NSD, below), replacing the cluster's bare "UNOWNED".

## immich VerifyError — mechanism + min-fix (`evidence/immich-verifyerror.txt`)
`A2.b.onMethodCall` (a Flutter `MethodChannel.MethodCallHandler`) does `iget-boolean b7.a.D` on a register typed
`d7.c`. Decompile: `d7.c extends b7.a` (so `b7.a.D` is legitimately accessible) **and implements
`android.net.nsd.NsdManager$DiscoveryListener`**. Route-A `framework.jar` has **0** `android/net/nsd/*` classes (vs 571
other `android/net/*`) — NSD is absent from the BCP. So `d7.c`'s declared interface is unresolvable → `d7.c` is an
"Unresolved Reference" → the verifier can't prove `d7.c` is-a `b7.a` → hard-rejects `A2.b` → `VerifyError` → bind
FAILED. **Min-fix:** add the NSD classes as BCP stubs in `adapter-mainline-stubs.jar` (FZ-007 tagsoup / FZ-008
SSLSockets pattern): `NsdManager$DiscoveryListener` (interface), `NsdManager` (no-op), `NsdServiceInfo`,
`$RegistrationListener`/`$ResolveListener`. That resolves `d7.c` → `A2.b` verifies → bind proceeds to immich's 2nd wall
(the libcronet `ATrace` = U15 #3, shelved); immich lights only with both.

## Files
- `evidence/u13-first-fatals.txt` — per-key U13 first-fatal + earliest wall, with hilog citations.
- `evidence/immich-verifyerror.txt` — the immich VerifyError decompile + NSD-absence proof + min-fix.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board (window3 wrapping — untouched); no push. Verdicts/promotions are the outer's. Sources read
read-only: the U13 run hilogs (`westlake-harness-u7-executor/benchmark/2026-10-03-u13-stage-a-plan/window1|window2|
window2-61b`), the cluster table (`westlake-harness/benchmark/2026-10-03-u13-first-fatal-clusters`), the immich apk +
framework.jar (`westlake-inputs`), and the existing U14/U15 deliverables.
