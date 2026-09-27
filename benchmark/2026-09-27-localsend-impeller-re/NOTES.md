# LocalSend libflutter pc=0 RE — Impeller GLES extension-proc gap (#48 horizontal)
date: 2026-09-27  (RE of the crash in westlake-harness/benchmark/2026-09-27-localsend-bringup)

## Crash (recap + confirmed)
- pc=0 SIGSEGV on thread **"1.raster"** (Flutter GPU/raster thread), at first frame right after the
  ANativeWindow is prewrapped. Caller: libflutter.so `0x4b655c: blr x8`; `x8 = ldr [x9,#0xea0]`,
  `x9 = adrp 0xaee000` → x8 = *(.bss table `0xaee000` + slot #468 / offset 0xea0) = **NULL**.
- Runtime regs confirm: x9 = 0x7f096ae000 = libflutter_base + 0xaee000 (table base), x8=0, x0=`this`,
  x22 = ANativeWindow. `.bss` (NOBITS) @ vaddr 0xaea8c0..0xafe6b0 → 0xaee000 IS in .bss (zero-init).

## What the table is + why slot #468 is NULL (static RE of libflutter.so)
- `0xaee000` is a **runtime-populated GL function-pointer table** (a global GLES ProcTable).
- The MAIN filler is an `adrp x8,0xaee000; str x9,[x8,#N]` sequence (0x4af974… / 0x4b0228…) that fills
  offsets **#960 … up to #3512** — the core GLES procs. It RAN (the app reached the raster thread), so
  these core slots are populated.
- Slot #468 = offset **#3744 (0xea0)**, which is **PAST the main filler's #3512 end** — it lives in the
  **extension-proc region**, populated by a SEPARATE loader that resolves each proc via
  `eglGetProcAddress` and guards each with `cbz x0, <skip>` (e.g. the 0x7fe9xx loader storing
  #3616/#3624/…/#3736/#3744 with per-entry null-skips). If a proc resolves NULL, the store is skipped
  and the slot stays 0 (from .bss).
- **Backend = Impeller (GLES), default in this build**: libflutter strings include
  `[Action Required]: Impeller opt-out deprecated.`, `CreateImpellerContext`, `enable-impeller`, and the
  Impeller GLES source paths, plus `eglGetProcAddress` and a large `GL_EXT_*`/`GL_OES_*` extension list.
- ROOT CAUSE: an EXTENSION GL proc that Impeller's GLES ProcTable resolves via `eglGetProcAddress`
  returns **NULL on OH's GLES driver** (classic gap: the driver advertises the extension in
  GL_EXTENSIONS but does not export the proc, or vice-versa), the null-guard skips its store, and
  Impeller's raster path calls slot #468 **unconditionally** → NULL call → pc=0. It is NOT "a whole
  backend init didn't run" — the core table filled and the app reached raster; it is one missing
  extension proc called without a guard.

## Fix (lightweight first; both knobs exist in this libflutter build)
1. PRIMARY — **disable Impeller → fall back to Skia GL**: Skia's `GrGLInterface` loader is defensive
   (validates the interface, null-checks extension procs before use), so a missing extension proc is
   tolerated. Set `<meta-data android:name="io.flutter.embedding.android.EnableImpeller" android:value="false"/>`
   in the (repackaged) AndroidManifest, or pass the engine shell arg `--no-enable-impeller` /
   `--enable-impeller=false` via the launch path. ("opt-out deprecated" = still honored, just warned.)
2. FALLBACK — **`--enable-software-rendering`**: Skia SOFTWARE raster, bypasses the GL proc table
   entirely → guaranteed first frame (slower). Safest pure bring-up lever if the GL path stays broken.
3. TARGETED (only if GPU rendering is required) — pin the exact NULL proc, then shim it:
   LD_PRELOAD-interpose `eglGetProcAddress` in the app to log every (name → ptr) and flag NULLs on the
   raster thread; the NULL name = slot #468's proc. Then alias it to OH's real proc (if present under
   another name) or provide it via a GLES shim. (I can build this logger — small, same pattern as the
   webview shim's interposers.)

## Deploy (outer loop / claude-2)
Fastest A/B: relaunch LocalSend with Impeller disabled (manifest meta-data or shell arg). If the first
frame renders → confirmed Impeller GLES extension-proc gap; ship with Impeller off (Skia GL) or pursue
the targeted proc shim for GPU-Impeller. If disabling Impeller isn't honored by the launch path, use
`--enable-software-rendering`. To name the proc, deploy the eglGetProcAddress logger and read the NULL.
