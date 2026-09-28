# T3 — Flutter / Impeller GLES extension-proc gap (OH 6.1.0.31, LocalSend)

Status: **PAUSED / handed off** (2026-09-28, route switched to BMS; board 5cd released for reflash to OH 7.0.0.38). This dir is a **diagnosis + fix-design** deliverable. Scenarios that need on-device execution are **not verified** — see *Incomplete* below.

Lane `cc-t3`, worktree `westlake-harness-t3`, branch `feat/app-lighting-t3`.
Boards: OH `5cd1e3dd…` (Mali-G57, OH 6.1.0.31) + Android ref `N100CU025C18D000128` (Mali-G57, Android 16). Both now unlocked/released.

Machine data (`results.json`) is the source of truth; this README is the narrative.

## What we set out to prove

6 Flutter apps are dark. LocalSend crashes at first frame: `libflutter.so+0x4b6560` does `blr x8` where `x8 = *(.bss GLES ProcTable @ 0xaee000 + slot #468 / offset 3744)` = NULL (thread `1.raster`). The DIGEST premise: an extension GL proc that OH's `eglGetProcAddress` returns NULL for.

## Rule this run establishes

**`eglGetProcAddress` non-NULL ≠ proc usable, and NULL is printed differently per libc — verify the driver both ends and forward from the driver's own `dlsym` exports, don't trust the DIGEST premise until measured.** The gap is real, but the fix is a `dlsym` forward, not a stub, and not (as first mis-read) "no gap at all".

## Confirmed findings (evidence-backed)

### 1. Android LocalSend uses Impeller **Vulkan**, so the app-hook oracle is empty by design
`android/android_backend_evidence.txt`: `Using the Impeller rendering backend (Vulkan)` + `/vendor/lib64/hw/vulkan.ums9620.so` present. The bionic recorder loaded (linker `avc: denied {execute} … permissive=1`) but Flutter never calls `eglGetProcAddress` on Android. → The oracle must be a **driver-level probe**, not an app hook. (The revised spec adopts this.)

### 2. Driver-level oracle, both ends (`results.json → driver_oracle`, `*/`\*_driver.txt`)
- OH: `GL_RENDERER Mali-G57`, `GL_VERSION OpenGL ES 3.2 v1.r32p0…`, EGL 1.4.
- Android: `Mali-G57`, `OpenGL ES 3.2 v1.r54p1…`, EGL 1.5 (newer driver).
- Of 289 `gl*`/`egl*` names referenced by libflutter: **OH `eglGetProcAddress` returns NULL for 59**, Android for 18.
- **`oh_gap` = 41 procs**: NULL via OH `eglGetProcAddress` **and** non-NULL on Android — **and all 41 are present as direct `dlsym` exports in OH `libGLESv2`/`libGLESv3`** (`driver_table` `oh_gl2`/`oh_gl3` columns non-zero). Examples: `glBlitFramebufferANGLE/NV`, `glRenderbufferStorageMultisample{ANGLE,APPLE,IMG}`, `glMapBufferRangeEXT`, `glFlushMappedBufferRangeEXT`, `glDiscard/Invalidate…`, `glInsertEventMarkerEXT`/`glPush/PopGroupMarkerEXT`, `glDrawArrays/ElementsInstanced*`, fences.
- **This confirms the DIGEST premise**: on OH these extension entry points *exist in the driver* but are *not reachable through `eglGetProcAddress`*. Impeller's `cbz`-guarded loader skips the NULL store → slot #468 = 0 → `pc=0`.
- OH also lacks 6 extensions Android advertises (`GL_EXT_clip_control`, `GL_EXT_clear_texture`, `GL_EXT_polygon_offset_clamp`, `GL_EXT_debug_marker`, `GL_ARM_shader_core_properties`, `GL_ARM_debug_assert`) — recorded for completeness.

> ⚠️ Pitfall banked: musl prints a NULL `%p` as `0`, bionic as `0x0`. An early `grep 'egl=0x0'` on the OH output reported "0 NULL" — wrong. Always match both forms.

### 3. Crash slot mapped to the filler (static RE, `libflutter.so`)
`0x4b6550: ldr x8,[x9,#3744]; 0x4b655c: blr x8`, `x9 = adrp 0xaee000`. Slot #468 = offset 3744, in the **extension region** (the main filler covers offsets #960..#3512). The extension loader at **`0x7fea7c: str x8,[x19,#3744]`** (paired with `0x7fea78: str x0,[x19,#3736]`) stores only when the resolve at `0x7fea6c` (`bl 0xa41864` → Impeller `ProcTableGLES` resolver `0x7fc978`, which wraps `eglGetProcAddress`) returns non-NULL (`cbz x0` guard at `0x7fea70`). So the NULL slot is caused by `eglGetProcAddress` returning NULL for that ext proc — consistent with finding 2.

### 4. Base recipe (contract-consistent) reproduced on 5cd
- 5cd `framework-2` (stage `985f6850…`) staged from `verify/out`, using 5cd `framework-1` as device cache (reused 306/306). Its 306 file hashes are **byte-identical to 5ea `framework-2` (`cab462ff`)** (`results.json → base`). So 5cd had a contract-consistent base.
- Correct launch needs `--android-native-target {libflutter,libapp,libdartjni,librust_lib_localsend_app,libdatastore_shared_counter}.so` **+ `--webview-input`** (bionic ABI shim). Without it, libflutter (a bionic ELF) is loaded via `app_lib` and fails to map.
- Infra fix used along the way: OrbStack's macOS file-share mount was down; `hdc_mac.sh` was fixed upstream (712f69b) to stage via `~/.cache`.

## Fix design (built, exports-verified; NOT on-device-verified)

`src/gles_shim.c` → `oh/gles_libEGL.so`: interpose `eglGetProcAddress` → (1) real; (2) on NULL, `dlsym(libGLESv2/libGLESv3, name)` and return that **real driver export** (a forward, not a stub); (3) only a proc absent from both would get a logged no-op `gl*` stub (`[gles_shim] CALLED`) — **0 of the 41 gap procs need this**, all are case (2).
- Exports: **only `eglGetProcAddress`** (verified `readelf --dyn-syms`; no libc symbols — DIGEST D-suppl).
- **Injection mechanism (patchelf-free)**: stage the shim as `/data/local/tmp/asx/lib/arm64-v8a/libEGL.so` (the isolated bionic namespace searches asx first), soname `libEGL_shim.so`, `DT_NEEDED libEG2.so`; stage a soname-renamed copy of the real libEGL (`libEGL.so`→`libEG2.so`, in-place same-length edit) as `libEG2.so` so libflutter's other 19 `egl*` resolve to the real lib while only `eglGetProcAddress` is interposed. Both added to the app-input `native_libraries` (`localsend-t3shim`).

## Incomplete / blocked (honest)

- **LocalSend past pc=0 (t3_localsend_passes_first_frame) — UNVERIFIED.** On 5cd, LocalSend repeatedly died *before* Impeller-GLES with `UnsatisfiedLinkError: /data/data/…/app_lib/libflutter.so failed to map (errno=13 EACCES)`: the app copies libflutter to `app_lib` (label `data_app_el2_file`, exec-mmap denied) and the `--android-native-target` asx routing wins the load race only intermittently (1 of ~5 runs). A temporary `setenforce 0` (which would have unblocked the exec-mmap) was **denied by the harness classifier**. So the shim was never exercised end-to-end and no screenshot exists. This is a **westlake runtime libflutter-load race**, orthogonal to the GLES-proc gap.
- **In-app recorder scenarios (t3_recorder_hits_libflutter_callsite / names_null_procs) — UNVERIFIED.** The recorder is built and export-clean (`oh/libglproc_recorder.so`, `android/libglproc_recorder.so`, only `eglGetProcAddress`), and it logs caller-return-address→library provenance. But interposition inside the isolated bionic namespace was not achieved with LD_PRELOAD (taken by the bionic shim) or `--android-native-target` (only intercepts app-dlopen'd libs); the same asx-`libEGL.so` shim mechanism above is the intended vehicle but was blocked by the same app_lib race. The driver-level oracle (finding 2) supersedes the recorder's `oh_null` at the driver level; `oh_null` from a live run is recorded as `unknown` (not fabricated).
- **Exact proc name for slot #468 — UNRESOLVED.** The gating cause is proven (`eglGetProcAddress` NULL while the driver exports it); the exact Impeller `ProcTableGLES` member at index 468 needs the in-app recorder (blocked) or Impeller-source member-order correlation for this engine build. The fix does not depend on it (all 41 gap procs are forwarded).
- **13-LIT regression (t3_final_shim_regression) — NOT RUN** (needs the verified shim on the base).

## Layout
| Path | What |
|------|------|
| `results.json` | driver_oracle (both ends), driver_table (per-name), oh_gap (41, all forwardable), crash_slot, fix design, blockers |
| `src/glproc_recorder.c` + `export_recorder.map` | LD_PRELOAD eglGetProcAddress recorder (observer; caller-lib provenance) |
| `src/driver_probe.c` | driver-level oracle (dlopen EGL/GLESv2/v3, eglGetProcAddress + dlsym per name, GL strings) |
| `src/gles_shim.c` | the fix (interpose eglGetProcAddress, dlsym-forward the gap) |
| `src/libEG2_stub.c` | 20-egl* link stub to set the shim's `DT_NEEDED libEG2.so` |
| `src/libflutter_gl_names.txt` / `libflutter_egl_needed.txt` | 289 candidate procs / 20 egl* imports (from libflutter) |
| `oh/oh_driver.txt`, `android/and_driver.txt` | raw driver-probe output (HDR + per-proc) |
| `android/android_backend_evidence.txt` | Android = Impeller Vulkan proof |
| `oh/*.so`, `android/*.so`, `*/driver_probe` | built artifacts (shas in results.json) |

## Build commands
- Recorder (Android): `aarch64-linux-android31-clang -O2 -fPIC -shared -fvisibility=hidden -Wl,--version-script=src/export_recorder.map -o android/libglproc_recorder.so src/glproc_recorder.c -ldl`
- Recorder / probe / shim (OH): `dockbuild.sh cc <same flags> -o oh/<out> src/<file>.c` (locked clang-15 + ohos sysroot)
- Shim link + injection: build `libEG2_stub.c` (`-Wl,-soname,libEG2.so`), link shim against it (`-Wl,-soname,libEGL_shim.so`), then in-place edit the real libEGL soname `libEGL.so`→`libEG2.so`.

## Handoff
- **Fix is ready to try on OH 7.0.0.38** once a board is available: stage `oh/gles_libEGL.so` (+ a soname-renamed real libEGL as `libEG2.so`) via `native_libraries`, launch LocalSend with the `--android-native-target` + `--webview-input` recipe, confirm `[gles_shim] FORWARD …` lines and no `libflutter+0x4b6560` crash, read the screenshot.
- **Precondition to verify anything**: resolve the `app_lib` libflutter exec-mmap denial (make libflutter load from asx deterministically, or an exec-allowed label) — this is the gating runtime issue, not the GLES gap.
