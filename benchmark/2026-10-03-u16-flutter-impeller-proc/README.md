# Flutter Impeller GLES ProcTable gap: the pc=0 slot is `glDepthRange` (localsend build 0d216f3f), a desktop-GL double entry OH's GLES driver has no form of — fix = an `eglGetProcAddress` interposer that shims it to `glDepthRangef`

#90, U16 head candidate (Flutter 4 keys), offline. Nothing was deployed to a board. This resolves what the
2026-09-28 RE left `unresolved-exact`: the exact proc behind slot #468, and corrects the fix for it.

## Input

U14 window-1 r2 (three boards). The U14 `eglCreateWindowSurface` interposer works — localsend now gets a non-zero
`EGLSurface` — and ~0.4 s later the `1.raster` thread takes `SIGSEGV, pc=0`, `#01 libflutter.so (0d216f3f…)+0x4b655c`.
`0d216f3f` is the libflutter **GNU build-id** (not a sha256); the corpus copy `0c56c4a4…` (sha256) has build-id
`0d216f3f630e1105…` — i.e. it **is** the crashed build, so the static trace below is on the exact binary.

## ① The slot, and the proc (static, on build 0d216f3f) — `evidence/crash-slot-trace.txt`

- **Crash:** `0x4b6528 adrp x9,0xaee000` (the `.bss` GLES ProcTable base) → `0x4b6550 ldr x8,[x9,#0xea0]` →
  `0x4b655c blr x8`. `0xea0 = 3744 = slot #468`. The slot is 0 → `blr 0` → pc=0.
- **Filler (Phase 2, resolve pass):** the block that fills `0xea0` reads the proc name from `[x19,#0xe88]`
  (`0x7fea64`), calls the resolver (`0x7fea6c bl …` → `0x7fc978`, which wraps `eglGetProcAddress`), and is gated by
  `0x7fea70 cbz x0, …` — on a **NULL** result both stores (`[x19,#0xe98]` func, `[x19,#0xea0]`) are skipped, leaving
  slot #468 = 0.
- **Name (Phase 1, construction):** entries are a 0x28 (40)-byte stride (`…0xe60, 0xe88, 0xeb0…`); `0xea0` is
  entry-`0xe88` + 0x18. Entry `0xe88`'s `.name` is set at `0x7fd3d4 adrp x1,0x1bc000; add x1,x1,#0xc64` → the C string
  at `0x1bcc64`:

  | entry base | name vaddr | **proc name** |
  |---|---|---|
  | 0xe60 | 0x1b5bc8 | glClearDepth |
  | **0xe88 (slot #468)** | **0x1bcc64** | **`glDepthRange`** |
  | 0xeb0 | 0x1c263e | glFenceSync |

  **Slot #468 = `glDepthRange`.**

## ② The driver: `glDepthRange` is absent in every form — `evidence/driver-oracle-glDepthRange.txt`

From the prior on-board oracle (5cd, OH 6.1.0.31, Mali-G57 `GL_VERSION v1.r32p0`; the U13 unified state runs the same
OH image and did not touch the GLES driver):

| name | eglGetProcAddress (oh) | dlsym libGLESv2 | dlsym libGLESv3 |
|---|---|---|---|
| **glDepthRange** | **NULL** | **NULL** | **NULL** |
| glDepthRangef | 0x7f3bae4f1c | 0x7f3c157274 | 0x7f3c0e0b00 |
| **glClearDepth** | **NULL** | **NULL** | **NULL** |
| glClearDepthf | 0x7f3bae4284 | 0x7f3c156944 | 0x7f3c0dfba0 |

`glDepthRange`/`glClearDepth` are the **desktop-GL double-precision** entries; GLES has only the `f` float variants.
They are NULL on `eglGetProcAddress` **and** on `dlsym` (so they are among the 59 `oh_null`, not the 41 `oh_gap` that
are dlsym-forwardable). **The 2026-09-28 RE's blanket "dlsym-forward" would leave this slot a no-op**, not a correct
`glDepthRange` — the real fix for this class is a **semantic shim to the `f` variant**.

## ③ Fix (design, built-as-source; not deployed) — `src/flutter_egl_getprocaddress.c`

Add an `eglGetProcAddress` interposer to the **Flutter-private `westlake_flutter/libandroid.so`** — the same level-1
object the U14 `flutter-egl-window` fix put `eglCreateWindowSurface` into, and the only place in libflutter's lookup
order that wins before platform `libEGL` (U14's rule). **New file; no frozen source edited.** On a NULL
`eglGetProcAddress` result it resolves, in order:

- **(B) desktop double → `f` variant shim:** `glDepthRange(GLclampd,GLclampd) → glDepthRangef`,
  `glClearDepth(GLclampd) → glClearDepthf` (the `f` procs are dlsym-resolved from libGLESv2/v3). **This covers the
  crash slot.**
- **(A) the 41 extension procs → dlsym-forward** from libGLESv2/v3 (the RE's case, unchanged).
- **(C) residual `gl*` → logged no-op stub**, so no slot is ever left 0 (defence in depth; `pc=0` cannot recur).

ABI caveat: the raw proc is stored at entry+16 and the crash call goes through a shared dispatcher at entry+24; the
shim uses the **desktop** `glDepthRange` signature because that is the resolved name. Crash-prevention (slot non-null)
is ABI-independent; correct depth-range needs the right arg widths — confirm from the dispatcher (`[sp,#0x20]` in
`JNI_OnLoad`) at build time and flip the two params to `GLfloat` if Impeller calls with float args.

**Build/deploy:** rebuild `ee2fb82c` faithfully (frozen clang `feef13a3` on hw248, same-length root, path-only diffs,
×2 identical), add this file, deploy **only** to `westlake_flutter/libandroid.so` — the identical `westlake_native/`
copy for the 13 native-cluster packages stays unchanged. **This builds on the U14 libandroid change** (same file); if
U14 freezes that file, this goes through the frozen "add new functionality, original behaviour preserved" path
(eglGetProcAddress is new; eglCreateWindowSurface unchanged). One read-only `sha256sum` of the deployed
`westlake_flutter/libandroid.so` settles its on-board identity before building (N6/U14 blind-spot: that underlay dir is
not in the runtime fingerprint).

## ④ The 4 keys do NOT share slot #468 — but one interposer covers them all — `evidence/builds-gap-class.txt`

The four Flutter keys are **four different engine builds** (build-ids: localsend `0d216f3f`, kitchenowl `889a1df3`,
fluffychat `495e7110`, libre `fdf0a0a6` = saber), so the crash **offset/slot is per-build** — only localsend is
`0xea0`/`glDepthRange`; the others, if run to this wall, fault at a different slot. But **all six Flutter builds**
reference `glDepthRange` and `glClearDepth`, import `eglGetProcAddress`, and carry the Impeller backend string — i.e.
they share the **same gap class**. A single `eglGetProcAddress` interposer resolves the whole class, so it is **not
slot-specific** and covers all four regardless of their differing layouts.

**Prediction (first fatal moves past the Impeller GLES ProcTable):**

| key | with the fix |
|---|---|
| localsend | past `glDepthRange` (slot #468). High. |
| fd-kitchenowl, fd-fluffychat, fd-libre | past their own gap-class slot (same mechanism, different offset). High on moving the first fatal; lit low–medium (next unknowns: Vulkan fallback already-logged-ENOENT, plugins, texture upload). |
| fd-immich, fd-saber | 0 here — immich dies earlier at libcronet `ATrace_beginSection`; saber shares libre's build but was not in the U13/U14 mover cohort. |

**Predicted movers: 4** (the named keys), via fix generality — not a shared slot.

## Rules this round sets

- **A proc name alone does not tell you the fix — check the driver both ends.** `glDepthRange` is NULL on
  `eglGetProcAddress` *and* `dlsym`; it is a desktop-GL double entry GLES never had. The fix is a shim to the `f`
  variant, not a dlsym-forward. (Corrects the 2026-09-28 RE, which would have no-op'd it.)
- **"same crash offset across apps" needs equal build-ids.** libflutter builds differ per app; the ProcTable slot for
  a proc is per-build. Scope a proc-indexed fix to the proc name via `eglGetProcAddress`, not to a byte offset.
- **The outer's "0d216f3f" was a GNU build-id, not a sha256.** Match build-ids when a crash cites a hash that is not
  in the corpus by sha.

## Files

- `evidence/crash-slot-trace.txt` — crash site, Phase-1/Phase-2 filler, name-string resolution (verbatim objdump).
- `evidence/driver-oracle-glDepthRange.txt` — board driver_table rows for glDepthRange/glClearDepth and the `f` variants.
- `evidence/builds-gap-class.txt` — build-ids + gap-class markers for all six Flutter builds.
- `src/flutter_egl_getprocaddress.c` — the eglGetProcAddress interposer (design).
- `results.json`.
