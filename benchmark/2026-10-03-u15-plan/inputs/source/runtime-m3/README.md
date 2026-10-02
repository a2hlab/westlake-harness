# U15 runtime M3 = U13 runtime 18763dd4 with one object replaced (EGLImpl.o): the GLSurfaceView converter is bound to the runtime's own ANativeWindow_fromSurface = `94c31177` (x2); only jni_eglCreateWindowSurface changes, exports/NEEDED/imports unchanged

#90, native, offline. No board touched. Built on hw248 (frozen clang feef13a3 / lld); a2hlab was left to the executor.
The wall: `2026-10-03-white-residual-u13` §M3 and `2026-10-02-white-m3-glsurfaceview`.

## 1. Two reproduction gates before any change

**Gate 1: relinking U13 itself gives `18763dd4…` byte-identically.**
- U13's runtime was built on a2hlab with the recipe in
  `$WORKSPACES/westlake-inputs/generations/u13-runtime-m1-v1/build/u13/`. The frozen clang there is a Linux x86-64 ELF.
- The recipe skips every object that is newer than its source, so the build is a pure link.
- **Getting the exact argv.** I ran the recipe on the Mac with its link line replaced by "print argv"
  (`evidence/link-argv-u13-recipe.txt`, 111 items). The object order therefore comes from the recipe itself.
- **One correction.** The original environment set `N3B_WITH_PUBLICATION=1`, which adds `webview_publication.o`
  after `n2-native/gl/bounds.o`. Without it the first relink was `3a316fea`, 9 webview symbols short. With it the argv
  is 112 items (`evidence/link-argv-hw248.txt`).
- **The relink on hw248.** Each `-l` was resolved with lld's rule (first `-L` hit); the 33 inputs
  (`evidence/mirrored-link-inputs.txt`, 50 MB) were mirrored under one root, plus the 87 U13 objects. The same frozen
  toolchain (clang-15 `b107ce03`, lld `8583bdc8`, identical to the Mac copy) gives
  **`18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae`** (`evidence/relink-u13-18763dd4.log`).

**Gate 2: EGLImpl.o `fc7b30b6` is faithfully reproduced (A′).**
- EGLImpl is not compiled by the recipe. It is the prebuilt
  `westlake-harness-bms-deploy/bms/src/.work/n4-native/gl/EGLImpl.o`, made by `benchmark/2026-09-30-n4-native/build-egl.sh`
  from `src/oh_egl_impl.cpp`.
- Its DWARF says frozen clang feef13a3, comp_dir = the 58-char bms-deploy root.
- In hw248's same-length mirror root, `build-egl.sh` run verbatim gives `2ea04e12…` ×2.
- `path_equal.py` (from `2026-10-03-u14-native-abi-gecko`): after the root placeholder, **0 differing bytes**, size
  equal (`evidence/egl-faithful-2ea04e12-vs-fc7b30b6.txt`).

## 2. The change (`src/oh_egl_impl.cpp`, diff `src/oh_egl_impl-vs-n4.diff`; the n4 original is untouched)

In `oh_window_from_surface` (inlined into `jni_eglCreateWindowSurface`):

**Before.** `static FromSurface from_surface = dlsym(RTLD_DEFAULT, "ANativeWindow_fromSurface");`
- The lookup misses when the runtime is not in the global scope.
- The null is cached for the process.
- The GL thread then never reaches the converter and throws `Make sure the SurfaceView … has a valid Surface`.

**After.** `static FromSurface from_surface = ANativeWindow_fromSurface;`, a direct reference to the converter this
same image defines and exports (0x197388).
- In the ELF this adds **one `R_AARCH64_GLOB_DAT` against `ANativeWindow_fromSurface`**.
- The runtime's existing `JUMP_SLOT` for the same symbol already resolves in the same lookup scope today, so the new
  reference cannot be null. It binds to exactly the converter the rest of the runtime calls.

**Plus one HiLog line per conversion** (`HiLogPrint`, already imported; domain 0xD000F00, tag `WL-OPENGL`):

`EGLImpl window surface: converter=%p surface=%p anw=%p oh=%p`

- The hilog header carries the calling GL thread's TID, so no `gettid` import is added.
- **If an IAE appears without this line, the Java Surface jobject itself was null.** That is the other M3 branch, and
  then the Java→JNI handoff is the wall.

**The unwrap resolver** (the bridge `oh_anw_get_oh`, with its NOLOAD fallback) and **all other code** are unchanged.

**The build.**
- `build_m3_hw248.sh`: the build-egl.sh compile line verbatim with only the source path changed, then Gate 1's link
  argv with only the EGLImpl.o item replaced.
- Two runs: EGLImpl.o `b67d9003…` and **runtime `94c31177709dbea0b1615a63c0d41a358f7db6843cbbd11f77979576a1a86a47`**,
  both runs identical, rc 0, no compiler output (`evidence/build-m3-{a,b}.log`).

## 3. Gates vs 18763dd4 (`evidence/gates.txt`, `evidence/equiv-18763dd4-vs-m3.txt`)

| gate | result |
|---|---|
| exports + imports (dynsym, defined and UND) | 1443 = 1443, **0 differences** |
| NEEDED / SONAME | identical |
| open sites | dlopen call sites 197 = 197 (`open_site_scan.py` finds the same DEFAULT-NS GL forwarder sites); **dlsym 211 → 210**: the removed one is the RTLD_DEFAULT lookup; none added |
| per function (`equiv.py`) | **`jni_eglCreateWindowSurface` 221 → 208 insns: the only code change.** 28 others (sqlite3/json/fts/gl forwarders) report operand differences with equal instruction counts: address attribution moved by the `.bss` shrinking 0x10 (the removed `from_surface` static + guard). They come from byte-identical input objects (every link input except EGLImpl.o is the 18763dd4 input), so the difference can only be link layout. The same set shows in 18763dd4 vs ac59. |
| strings added | **the HiLog tag `WL-OPENGL` and its format**; also the debug-info path strings of the new CU (mirror root + `benchmark/2026-10-03-u15-runtime-m3/src`) and short code-byte sequences |
| strings removed | **`[WL-OPENGL] ANativeWindow_fromSurface not found`**, because that branch is now unreachable (`from_surface` is a non-null constant) and the compiler drops it. Also the `from_surface` static/guard symtab names, the old CU's debug path strings, and code-byte sequences. Reported, not hidden: it is the only deviation from "strings only gain the HiLog". |

## 4. Prediction (first fatal; IAE = the caught M3 exception)

| key | prediction |
|---|---|
| cv2-com-bytehamster-flowitgame | **GLSurfaceView IAE gone (medium)**; lit medium (no other native libs) |
| fd-app (Unciv) | **IAE gone (medium)**; lit low–medium (also a bg `MediaStore.scanFile` NSME) |
| fd-shatteredpixeldungeon | **IAE gone (medium)**; lit medium |
| why medium | Conditional: the GL thread never entered the converter in every M3 run, which fits the null lookup. But a null Surface jobject reaches the same IAE text. The new HiLog line settles which. |
| every other key | 0. No lit U13 key (0/60) creates an EGLImpl window surface; hwui's EGL path is separate. Watch the lit keys whose APK references GLSurfaceView (anki, antennapod, photophase, shadereditor, libretube, tusky, newpipe); shadereditor hit this IAE on a non-main GL view on U10.1T8, and its GL view may now render. dddmodel2 never reaches GLSurfaceView on U12 (dialog first), so 0. |

**Board check (runtime behaviour, minimal experiment).** flowitgame alone, ≤ 10 min, on a free board.
- **Pass:** a `WL-OPENGL EGLImpl window surface: converter=<non-null> … anw=<non-null> oh=<non-null>` line on the GL
  thread, then no `GLSurfaceView: …IllegalArgumentException: Make sure`.
- **Fail without the line:** null jobject, so look at the Java handoff.

## Release (for cx-bms)

- `$WORKSPACES/westlake-inputs/generations/u15-runtime-m3-v1/payload/android/lib64/liboh_android_runtime.so`
  = **`94c31177…`**. Its slot is the runtime 18763dd4 slot.
- Also there:
  - `builds/` (a, b);
  - `objects/` (EGLImpl m3 `b67d9003`, faithful repro `2ea04e12`, original `fc7b30b6`);
  - `logs/` (teed: relink-u13, m3-a/b, egl-repro-a/b);
  - `link/` (recipe-printed and hw248 argv, mirrored-input list);
  - the source and build script;
  - `SHA256SUMS` (18 files).
- hw248: `$HW248_HOME/cc-t3-u15rt-m3/` (link root) and the mirror `cc-t3-nabi-2026103/` are kept.

## Rules this round sets

- **A runtime relink needs the recipe's environment switches as well as its argv.** `N3B_WITH_PUBLICATION=1` adds an
  object. Print the argv from the recipe itself and compare the symbol set before blaming the toolchain.
- **To bind to a symbol the same image defines, reference it directly.** A preemptible reference still resolves in the
  library's own scope, as the existing JUMP_SLOT proves. Do not look up your own export through RTLD_DEFAULT.

## Files

- `src/oh_egl_impl.cpp`, `src/oh_egl_impl-vs-n4.diff`, `build_m3_hw248.sh`.
- `evidence/`:
  - `link-argv-u13-recipe.txt`, `link-argv-hw248.txt`, `mirrored-link-inputs.txt`;
  - `relink-u13-18763dd4.log`, `build-m3-{a,b}.log`;
  - `egl-faithful-2ea04e12-vs-fc7b30b6.txt`, `gates.txt`, `equiv-18763dd4-vs-m3.txt`.
- `results.json`.
