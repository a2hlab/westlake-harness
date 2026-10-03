# M1 freeze granularity — how to register, and the file split

## The rule (FROZEN.md "What gets frozen, and at what granularity")
- A single-purpose artifact (installer pair, a standalone shim library): freeze the artifact SHA.
- A fix **inside a multi-purpose artifact** (the runtime JAR, `liboh_android_runtime.so`): freeze the
  **source file(s)** that implement it (git blob id), **not** the whole artifact, so other fixes can still
  land. **If the fix sits inside a shared file, move it into its own file first, verify again, then freeze.**
- New fixes go into new files. Nothing is added to a frozen file.

## Where M1 sits today (why it is not yet freezable as-is)
M1 is compiled into the multi-purpose `liboh_android_runtime.so`, and its source lives **inside the shared**
`android_graphics_compat_shim.cpp` — a file that also holds the SQLite weak stub, the AAssetManager lazy
init, the BBQ Surface path, and the EGL loader. So:
- **Freezing the whole `.so`** is wrong (it would lock every other U13 fix in that runtime; a later JAR/
  native fix could not land without tripping the frozen check).
- **Freezing the shared `.cpp` blob** is wrong (freezing a shared file freezes unrelated code; a later edit
  to the SQLite stub in the same file would trip the frozen check and block an unrelated fix).

The M1 change is already **cleanly isolated** as a patch hunk (`@@ -442 +442,90 @@`, git blob
`7521ab2b`): a self-contained `namespace { ... }` block (`m1_*` helpers + `m1_native_window_from_other_copies`)
plus one call site where the shim's resolved bridge copy returns null. It adds only `#include <link.h>`,
the `dl_iterate_phdr` undefined symbol, and the `[M1-COPY]` string — no other coupling (A' proof, commit
`64d7e6594b`: exports identical, open-sites 198==198).

## Recommended: split M1 into its own file, then freeze that blob (preferred)
1. Move the `@@ -442 +442,90 @@` block into a new file, e.g.
   `bms/src/adapter/framework/android-runtime/src/android_graphics_m1_copy.cpp`
   (the `m1_*` helpers + `m1_native_window_from_other_copies(int32_t sessionId)`), exposing one function;
   leave in `android_graphics_compat_shim.cpp` only the one-line call at the null-miss site
   (`if (void* nw = m1_native_window_from_other_copies(sessionId)) return nw;`).
2. Rebuild the runtime; **re-verify** the single-variable way the receipt already demonstrates — the new
   `android_graphics_m1_copy.o` carries the M1 code, `android_graphics_compat_shim.o` returns to the
   baseline `40aa2f5f` (minus the one call line), the runtime stays functionally `18763dd4` (abi-identical,
   `[M1-COPY]` still emitted, dl_iterate_phdr still the only new undef). Re-run the 3 apps (fd-uhabits /
   wikipedia / noice) — each must stay lit / past the wall.
3. Freeze the **source blob of `android_graphics_m1_copy.cpp`** (like FZ-003/004/006/007/008: a source blob
   with `branch`/`commit` + `:repo_path`, checked by `check_frozen.py --git`). This is the clean,
   future-proof granularity: other shim fixes keep landing; only the M1 file is frozen.

## Fallback: register now as `.o` + source blob (if the split is deferred)
If U13 must be promoted before the split is done, register M1 provisionally by pinning, together:
- the **source blob** `8ad95199` of the R3 `android_graphics_compat_shim.cpp` snapshot (branch master,
  commit `64d7e6594b`) **and** the **M1 needle blob** `7521ab2b` (so the exact lines are recoverable), plus
- the **object** `android_graphics_compat_shim.o = 612236be` (vs baseline `40aa2f5f`), and
- the **runtime** `liboh_android_runtime.so = 18763dd4` as context (not frozen whole).
This is weaker than a dedicated-file blob (it pins a shared file's whole content, so an unrelated edit to
that file would need a version bump), so it should be treated as temporary: **do the split at the first U15
runtime rebuild** and move the freeze to the dedicated file's blob. Precedent: FZ-003 froze a standalone
`.cpp` source blob for a runtime `.o` fix — M1 should reach the same shape via the split.

## check_frozen wiring (for whoever registers)
- Add the entry to `knowledge/frozen/frozen.json` (`entries[]`) + the readable row in `FROZEN.md`.
- Source blob entry uses `branch: master` (or the split commit) + `repo_path` so `check_frozen.py --git`
  verifies from any checkout (the M1 source is on `master`, like FZ-003/004 are pinned on their branches).
- Register FIRST, deploy SECOND (FROZEN.md); report in the morning summary. Registration is the outer's,
  after U13 promotes to the unified state.
