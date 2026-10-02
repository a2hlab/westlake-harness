# U15 #3: private-domain NDK symbols — immich ATrace (Flutter) + mindustry OpenSLES (native)

#90, offline, no board. Static analysis of cluster C4 (`master 49e6f805da benchmark/2026-10-03-u13-first-fatal-clusters`):
two apps die on NDK public symbols missing from their **private** domain's visible set. Full missing-symbol sets
(not just the first), the AOSP 14 provider, the minimal fix per app, and the first-fatal prediction.
(`evidence/symbol-replay.txt` has the raw `nm`/`objdump` replay.)

## ① Full missing-symbol sets (musl per-namespace replay)
| app | domain | app lib | missing NDK symbols (complete) |
|---|---|---|---|
| fd-immich | Flutter-private (`westlake_flutter`) | `libcronet.143.0.7445.0.so` | `ATrace_beginSection`, `ATrace_endSection` (exactly 2; no other `ATrace_*`/`ASurface_*`/… ) |
| mindustry | native (`westlake_native`) | `libarc.so` | `slCreateEngine`, `SL_IID_ENGINE`, `SL_IID_PLAY`, `SL_IID_VOLUME`, `SL_IID_ANDROIDSIMPLEBUFFERQUEUE` (5) |

## immich / ATrace — the Flutter libandroid is a shim, not a full NDK libandroid
`westlake_flutter/libandroid.so` (`fff9be31`) exports **9** symbols — `ANativeWindow_lock/unlockAndPost@@FLUTTER_ANDROID_1`,
`eglCreateWindowSurface/eglDestroySurface/eglSwapBuffers/eglSwapBuffersWithDamageKHR@@LIBEGL`, + 3 libc re-exports — i.e.
a purpose-built ANW+EGL interposer, **not** the full NDK libandroid, so it has no `ATrace_*`. The Flutter domain's inherit
lists (`westlake_stock_host_main.c:266-270`) carry no libandroid either. The inherited `liboh_android_runtime.so`
(`18763dd4`) has only the **internal lowercase** impl `atrace_begin_body` / `atrace_end_body` / `atrace_get_enabled_tags`
(T) — **not** the NDK-public capital-A wrappers. AOSP 14 contract (confirmed `benchmark/2026-09-21-ndk-coverage` +
runtime-candidate maps): `ATrace_beginSection`/`endSection` are `libandroid.so` NDK exports, each a thin wrapper over
`atrace_begin_body`/`atrace_end_body`. **Genuine gap:** the NDK-public ATrace_* are absent domain-wide; only the body
impl exists (in the inherited runtime).

**Minimal fix → add 2 (or 3) forwarders to the private libandroid `fff9`** (the "补转发 in 私有 libandroid" option):
```c
extern "C" void atrace_begin_body(const char*);
extern "C" void atrace_end_body(void);
extern "C" uint64_t atrace_get_enabled_tags(void);
extern "C" void ATrace_beginSection(const char* name) { atrace_begin_body(name); }
extern "C" void ATrace_endSection(void)               { atrace_end_body(); }
extern "C" int  ATrace_isEnabled(void)                { return atrace_get_enabled_tags() != 0; } // cheap completeness
```
The bodies resolve against the already-inherited runtime. This is the right layer: `fff9` **is** the Flutter domain's
libandroid; it should export the NDK symbols app libs expect, exactly as it already forwards `ANativeWindow_*`. A
domain-inherit-soname fix is not viable (no full NDK libandroid exists in the OH system to inherit); `native_abi` is the
Gecko/native-domain ABI lib — wrong domain for a Flutter app.

## mindustry / OpenSLES — the 5 symbols split across two providers; the host already wires it
`libarc.so` needs the OpenSL ES **core** (`slCreateEngine` + `SL_IID_ENGINE/PLAY/VOLUME`) **and** the **Android
extension** `SL_IID_ANDROIDSIMPLEBUFFERQUEUE`. No single lib has all 5:
- OH platform `/system/lib64/libOpenSLES.so` (66 exports) = the core 4/5 — **no** `SL_IID_ANDROIDSIMPLEBUFFERQUEUE`.
- `libwestlake_native_abi.so` (+ the `/system/android/lib64/libOpenSLES.so` stub) = the Android-ext IID (1/5).

The host **already codes** the fix (`westlake_stock_host_main.c:291-313`): for `io.anuke.mindustry`/`org.ppsspp.ppsspp`
it `dlopen_ns(app_ns, "/system/lib64/libOpenSLES.so", RTLD_NOW|RTLD_GLOBAL)` (core, globally resolvable for `libarc`) and
`native_abi` supplies the Android IID. mindustry's U12 failure = that branch was not active/deployed then.

**Minimal fix → domain provisioning, no new lib** (the "域加载/继承" option): ensure the native_private audio branch
**and** `native_abi` are in the deployed U15 host. Prefer the **explicit absolute-path `dlopen_ns` RTLD_GLOBAL** already
coded over a bare soname-inherit, because the soname `libOpenSLES.so` is **ambiguous** — it resolves to either the OH
platform core lib or our Android-ext stub depending on default's search order (this ambiguity is exactly why U12's
soname path left `slCreateEngine` unresolved). One hardening nit: the branch's verify list checks `SL_IID_BUFFERQUEUE`
but `libarc` uses `SL_IID_ANDROIDSIMPLEBUFFERQUEUE` — add that to the verify set so a missing Android IID fails closed.

## Prediction (first-fatal)
- **immich:** ATrace is **not** its first-fatal. Its first-fatal is the Java **`VerifyError A2.b`** (Unresolved Reference
  `d7.c`, a MethodChannel `onMethodCall` verify failure — a separate Java/dex cluster) at bind; the `ATrace` reloc fires
  later when `libcronet` loads. So the ATrace forwarders clear the **cronet-load** wall, but immich stays blocked by the
  prior VerifyError → **will not light from this fix alone**. Fix is still correct (removes a real second wall) but must be
  paired with the VerifyError fix to light immich.
- **mindustry:** `slCreateEngine` is the **terminal** native-domain wall (Arc engine audio init); mindustry is `bound`.
  With all 5 OpenSLES symbols provided (host core dlopen_ns + native_abi Android IID), `libarc` resolves and audio init
  completes → mindustry proceeds past this wall. Lit likelihood **medium–high** (GL game; next risk would be GL/EGL/asset,
  not covered here).

## This round's rule
Replay the **complete** NDK import set of the app's own lib against the **private domain's** visible set, and locate each
missing symbol's AOSP owner — then fix at the layer that owns that domain's copy: export the NDK wrappers from the
domain's own libandroid (Flutter: `fff9` forwarders over the runtime's `atrace_*_body`), or provision the platform
implementation into the domain by **absolute path** when the soname is ambiguous (native: OpenSLES core via `dlopen_ns`
RTLD_GLOBAL + `native_abi` for the Android extension). "Missing in a private domain" ≠ "missing on the system" — the
impl usually exists one edge away; supply the edge, don't duplicate the lib.

## Files
- `evidence/symbol-replay.txt` — the per-app missing-symbol replay + provider map (nm/objdump).
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board; no push; static symbol replay only (no build, no deploy). Fixes are the Flutter-libandroid / host
owners' to build + ship. Sources read read-only: the two apks (`westlake-inputs/apks`), `fff9` libandroid + runtime +
OpenSLES + native_abi (`westlake-inputs/generations`), the host source + AOSP14 ref (`westlake-harness`,
`westlake-inputs/aosp-14.0.0_r1-src`), the cluster table (`westlake-harness/benchmark/2026-10-03-u13-first-fatal-clusters`).
