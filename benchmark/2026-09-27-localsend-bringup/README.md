# LocalSend (Flutter) bring-up on OH 6.1.0.31 — #48 horizontal (2026-09-27)

Goal: light up LocalSend (`org.localsend.localsend_app`, F-Droid v643 / 1.18.2, Flutter) to first usable frame on
board 61b06572, westlake musl runtime. Task premise was a single-symbol blocker
(`SurfaceControl.nativeSetDesiredHdrHeadroom(JJF)V` unregistered → no first frame; register a no-op).

## Result: launch PASS, HDR premise STALE (already fixed), NEW deeper blocker found (no first frame)

| Step | Outcome |
|------|---------|
| Stage + launch | **PASS** — `probe_source_app.py` staged a fresh runtime (`a2hlab-source-a457795c…`) + spawned; libflutter/libapp/libdartjni load; app reaches MainActivity, window session 1402/1403, main surface + SurfaceView ANativeWindow (prewrapped) |
| HDR blocker (`nativeSetDesiredHdrHeadroom`) | **ALREADY RESOLVED** — current verify `liboh_android_runtime.so` sha `7ff14690` has the no-op registered (`android_view_SurfaceControl.cpp:487` def + `:884` JNINativeMethod; child log `ok register_android_view_SurfaceControl`). westlake source @ `22b9453` (also wv46 b14e4d0 / westlake-current 532633d). No action needed. |
| First frame | **NO** — pc=0 SIGSEGV before compositing; screenshot shows the Westlake IME host launcher, not LocalSend UI |

## The actual current blocker (evidence/)

- **pc=0 SIGSEGV (SEGV_MAPERR fault addr 0)** = call through a NULL function pointer.
- Crash site (caller LR): **`libflutter.so + 0x4b6560`**. Instruction at `0x4b655c`: `blr x8`; `x8` loaded at
  `0x4b6550: ldr x8, [x9, #3744]`, `x9 = adrp 0xaee000` → **x8 = *(libflutter `.bss` @ vaddr `0xaeeea0`, slot #468) = NULL**.
- `0xaeeea0` is in **`.bss`** (NOBITS, zero-init) — **NOT** a dynamic-import GOT slot (no reloc there). So it is a
  **runtime-populated function-pointer** that Flutter resolves at init and cached NULL, then calls unconditionally.
- Fires immediately after `[WESTLAKE-ANWFS] #2 -> ANativeWindow (prewrapped=1)` — i.e. during Flutter's first-frame
  GPU/render surface setup. x0 = an object (`this`); x22 = the ANativeWindow (0x…4ba0).
- **Class = graphics-stack proc gap** (a GL/EGL/graphics proc Flutter resolved to null on OH), NOT a JNI no-op.
  `[WL-OPENGL] registered EGLImpl/GLES10..32=ok` is the Java-layer android.opengl binding, not the native proc
  libflutter calls directly.

## Handoff (needs graphics work — claude-3 / focused RE)

Identify the exact null proc: instrument/bisect the `.bss 0xaeeea0` populator (many `adrp …,0xaee000` store sites in
libflutter .text ~0x4ad0xx), or trace Flutter's GL/EGL proc resolver at init to see which entry returns null on OH,
then provide it (OH GLES/EGL driver export, or a shim). This is M/L effort, not the XS the premise assumed.

## Board state left

Board repurposed for LocalSend (Toutiao delivery set aside per outer loop): Toutiao selfheal watchdog STOPPED,
host swapped to verify `signed-host` (`bm install`), LocalSend runtime `a2hlab-source-a457795c…` staged + stage
`a2hlab-app-a457795c…`. Toutiao delivery restorable from committed artifacts (reinstall its host + libart 78e34445
+ shim 85c789f4 + restart watchdog).

## Layout
| Path | What |
|------|------|
| evidence/localsend-child-crash.stderr | child stderr through the pc=0 crash (surface setup trace + reg dump) |
| evidence/localsend-crash-maps.txt | /proc/pid/maps captured just before crash (for LR→lib mapping) |
| evidence/libflutter-crashsite-disasm.txt | disasm of the crash site (blr x8, x8=*(.bss 0xaeeea0)) |
| evidence/localsend-no-first-frame.png | post-launch screenshot = host launcher (no LocalSend UI) |

## 2026-09-27 update — Impeller-off fix (claude-3 RE) re-confirmed on 5ea34a45; injection has no config hook
Re-staged LocalSend on 5ea34a45 (framework-2 = a2hlab-framework-cab462ff, runtime a2hlab-source-cc99f157): SAME
crash (pc=0 after ANWFS #2, the Impeller GLES ext-proc null, slot#468). claude-3's fix is DEFINED — disable
Impeller → Skia GL (manifest meta-data `io.flutter.embedding.android.EnableImpeller=false`, or engine switch
`--no-enable-impeller` / `--enable-software-rendering`). BLOCKER = **no config hook to inject it on this runtime**:
- No apktool/aapt2 available to repack the APK's binary AndroidManifest.
- probe_source_app has NO intent-extra / shell-arg passthrough (only `--runtime-env` for child ENV, which Flutter
  doesn't read for Impeller).
- westlake PM reads app meta-data from the APK manifest (ApplicationMetaDataReader ← apk_manifest_parser JSON,
  re-parsed each launch); no on-disk manifest JSON cache to edit, no `appMetaData` override file hook.
- The launch Intent CAN carry extras (IntentWantConverter/`android_extras_json`) but they come from request.bin
  (binary want), not an env — no easy injection.
DETERMINISTIC FIX (framework, route to claude-3 / a framework-fix pass): patch `ApplicationMetaDataReader.read()`
to inject `result.putBoolean("io.flutter.embedding.android.EnableImpeller", false)` for Flutter apps (or scoped to
org.localsend.localsend_app), rebuild framework-java, re-stage. App-scoped, harmless to others. Then LocalSend
falls back to Skia GL (defensive GrGLInterface tolerates the missing ext proc) → first frame. Alt: get apktool,
repack the manifest + update app-input sha.
