# Runtime stub census — 325 deliberate-stub JNI methods, and which ones actually block a key

Offline, no board, board #90. A one-time census of the "deliberately return empty / stub" JNI methods in the deployed
route-A runtime `liboh_android_runtime.so` (`ac59dec0`; real source `4d5cac38ff`,
`bms/src/adapter/framework/android-runtime/src/`), cross-referenced with which stage-A keys actually hit them and
whether hitting one is that key's first fatal.

## Headline
**325 deliberate stubs. Exactly ONE causes a stage-A first fatal: `Surface.nativeLockCanvas` (+ its pair) → fd-plus.**
Every other first fatal in the candidate base is a jar / native-lib / namespace / policy / **libhwui** / app issue, not
a runtime stub. So the vast majority of "return null/0/false" stubs are **benign on this corpus** — their stated
assumption ("no path strict-requires this") holds. Static method/file:line/assumption for all 325 is in
`evidence/stubs-full.txt`; the first-fatal correlation backbone is `evidence/dynamic-first-fatal-map.txt`.

## Method
- **Static** (4 parallel sub-audits over 53 `.cpp`): a stub = a function registered in a `JNINativeMethod kXxxMethods[]`
  table whose body does no real work and returns a constant empty/placeholder (`nullptr`/`0`/`JNI_FALSE`/empty/unchanged
  out-param) or a hard "unsupported". Real implementations with error-path returns were excluded.
- **LIVE?** A source stub can be dead if a later `RegisterNatives` (ART: last wins) rebinds the method to the real
  libhwui/bridge. Checked each via the on-device `OH_RegHook` log (method → winning lib). Spot result: the compat_shim
  ImageDecoder stubs register *after* libhwui (lines 18218+ > 17744+) so they **win**; `Bitmap.nativeComputeColorSpace`
  is libhwui-only (not a runtime stub).
- **Dynamic reach / first-fatal**: silent stubs leave no per-call log (the generic UNSUPPORTED/stub markers are OH
  system noise, thousands/key), so reach is attributed from the first-fatal stack (27-cluster backbone) and, where a
  stub logs, a marker sweep over 56 stage-A hilogs.

## The table — sorted by blocked-key count
| stub(s) | file | returns | LIVE | keys reached | blocks (first fatal) |
|---|---|---|---|---|---|
| **`Surface.nativeLockCanvas` (+`nativeUnlockCanvasAndPost`)** | compat_shim:219/224 | 0 / void | yes (runtime sole) | fd-plus (sw-canvas) | **1 — fd-plus** `ISE "Surface was not locked"` |
| `SurfaceControl.nativeSetFocusedWindow` | SurfaceControl:603 | void (log) | yes | **52 keys** (window setup) | 0 (benign — focus not adapter-managed) |
| all other 322 stubs (Binder/Trace/SysProp/Parcel/Sensor/Media/Audio/KCM/SurfaceControl/HardwareRenderer/BLAST/…) | — | empty/no-op | yes | varies (mostly 0 observed) | **0** |

### Separate list — refuted assumption / latent hazard (0 observed first fatals, but the stated assumption does NOT hold universally)
| stub | file | the assumption | status |
|---|---|---|---|
| `ImageDecoder.nGetColorSpace` → null | compat_shim:79 | "no Android UI path strict-requires non-null ColorSpace; sRGB assumed when null" | **REFUTED** — `Bitmap.createBitmap(source,…)` strict-requires it (fd-musicplayer). But musicplayer's *actual* first fatal is `Bitmap.nativeComputeColorSpace` in **libhwui** on a *resource* bitmap (BitmapFactory path), not this ImageDecoder stub (see benchmark/2026-10-02-u13-runtime-v2). So: latent risk for an ImageDecoder-decode-then-scale app, **0 observed** here. |
| `DisplayEventReceiver.nativeGetDisplayEventReceiverFinalizer` → 0 | DisplayEventReceiver:523 | (comment) "previously returned 0 which feeds NAR(0) crash via ART intrinsic … TODO P1 real release fn" | **SELF-FLAGGED HAZARD** — a 0 finalizer handed to `NativeAllocationRegistry.applyFreeFunction` can crash; 0 observed first fatals, but the source itself marks it unsafe. |
| `Typeface.*` fallback (16) → fake handle 1L / 0 / null | Typeface:66–84 | "BROKEN FALLBACK PATH … non-functional but non-crashing at Java-ctor time" | fallback-only (libhwui Typeface delegation failed); if reached → text does not render (quality), does not crash. 0 observed. |
| `Surface.nativeGetWidth`→720 / `nativeGetHeight`→1280 | compat_shim:226/227 | hard-coded | wrong dimensions to an app that queries Surface size directly; 0 observed. |

## Two intentional-architecture groups (NOT accidental gaps)
- **HardwareRenderer neuter (41 stubs, compat_shim:867–878)**: deliberately makes `nCreateProxy`/draw no-ops so the
  libhwui RenderThread is **never born** — route-A owns rendering. Registered **only** behind the Unity/CW env gate
  (`OHUB_VARIANT` / `OHUB_UNITY_LIBDIR`); outside it, libhwui's real natives bind. This is a design choice, not a wall.
- **Binder / Parcel-binder / SystemProperties-write / Trace / Sensor / AudioFlinger-less caps**: whole-subsystem no-ops
  because OH has no Android binder / AudioFlinger / sensor HAL. Apps degrade gracefully (null-checks, default fallbacks,
  empty lists). 0 first-fatals across the 56-hilog corpus.

## Counts by file group (325 total)
compat_shim 72 (ImageDecoder 5, Surface 18, BLAST 8, HardwareRenderer-neuter 41) · Typeface 16 · SurfaceControl 85 ·
DisplayEventReceiver 1 · GraphicsEnvironment 11 · InputChannel 3 · InputEventReceiver 3 (+4 in adapter_bridge) ·
KeyCharacterMap 9 · MotionEvent 2 · AudioSystem 5 · AudioTrack 4 · MediaPlayer 40 · EGL14 2 · SensorManager 16 ·
Binder 16 · Debug 1 · MessageQueue 1 · SystemProperties 8 · Trace 9 · Activity 1 · Parcel 14 · EventLog 2 · CursorWindow 2.

## What this buys
- **Risk is concentrated, not diffuse.** Only `nativeLockCanvas` turns a stub into a crash on the current app set; and
  even that one is already known to need the libhwui-backed software-Canvas path (deferred with fd-plus, DIGEST 610).
  No other stub needs touching for the current keys — don't "fill in" 324 benign stubs.
- **A lookup table for future walls.** When a NEW app's first fatal lands in a native method, `evidence/stubs-full.txt`
  says in one grep whether it's a known stub, what it returns, and the author's assumption — so the next investigation
  starts from "is this stub's assumption being violated?" (as fd-plus and the nGetColorSpace refutation both were).
- **Refuted-assumption discipline.** A stub comment that says "no path needs this" is a hypothesis; this census records
  the two that have been (nGetColorSpace) or self-flagged as (DER finalizer) refutable, so they get fixed on evidence,
  not pre-emptively.

## This round's rule
Enumerate stubs by the JNI method table + body, not by raw `return null` lines (520 of those are mostly real error
paths). Decide LIVE by the on-device `OH_RegHook` winner, not by source presence (a source stub can be overridden by
libhwui). Attribute "blocks a key" only from the first-fatal stack — a stub reached by 52 keys (`nativeSetFocusedWindow`)
can still block zero.

## Files
- `evidence/stubs-full.txt` — all 325 stubs: `CLASS::method(sig) | Cfunc | file:line | returns | assumption`.
- `evidence/dynamic-first-fatal-map.txt` — the 27-cluster first-fatal → cause-layer map + RegHook winners + the
  net attribution (only nativeLockCanvas blocks a key).
