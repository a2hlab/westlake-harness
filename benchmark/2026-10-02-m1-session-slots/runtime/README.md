# M1, route (c): fix in the runtime's compat shim; U13 runtime candidate `18763dd4` = aa149019 + M1

The outer chose (c) on 2026-10-02: the deployed bridge `84695d62` has no source, so the fix goes into
liboh_android_runtime. The N10b smoke-markers recipe reproduces that library per object, and only
`android_graphics_compat_shim.o` changes. It is combined with cc-wiki's `aa149019` (`asset_manager.o`) into one U13
runtime candidate.

**Result:**

| variant | sha256 | meaning |
|---|---|---|
| control | `ac59dec0…` | deployed, reproduced from source |
| m1 | `18a77eaa…` | M1 only |
| **u13** | **`18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae`** | aa149019 + M1; built twice, byte-identical |

- Objects: 69; u13 differs from ac59dec0 in exactly `android_graphics_compat_shim.o` and `asset_manager.o`.
- Exports: identical. Undefined symbols: + `dl_iterate_phdr` only.
- Strings: + the `[M1-COPY]` marker only.
- Open sites: 198 = 198.

## 1. The failing lookup is decided in the runtime (static)

Call chain (N2 compat shim source `b94f69e4`; its object `40aa2f5f` is the one in deployed ac59dec0, and the control
build recompiles it from that source to the same ac59dec0):

```
BBQ_nativeUpdate (shim :490-529)  /  BBQ_nativeGetSurface lazy path (:543-583)
  -> static oh_wm_get_native_window(sessionId)                         shim :445   <- the fix point
     -> g_oh_wm_get_native_window_fn = dlsym(dlopen("liboh_adapter_bridge.so", RTLD_NOW|RTLD_NOLOAD))   shim :398-440
        -> bridge oh_wm_get_native_window -> getOhNativeWindow: "unknown sessionId=N" (resolved copy's sessions_ miss)
           -> readProcessWindowTarget: single slot, null unless N is the last published session
  <- nullptr -> runtime logs "BBQ.update: getOhNativeWindow(sessionId=%d) returned null" (:519) and later
     "BBQ.getSurface: ohNativeWindow null … returning empty Surface" (:574-576)
```

Every log line of the failure is the runtime's, except `unknown sessionId`.

| deployed string | runtime ac59dec0 | bridge 84695d62 |
|---|---|---|
| `BBQ.create name=` | 1 | 0 |
| `returning empty Surface` | 1 | 0 |
| `ohNativeWindow null (sessionId=` | 1 | 0 |
| `OHNativeWindow=%` | 4 | 0 |
| `unknown sessionId=` | 0 | 1 |

The bridge's single-slot read returns its answer to this runtime function, and the empty Surface is the runtime's
decision on a null. So a runtime-side fallback covers the failure.

In the 367 replayed lookups (`../proof.json`), each `unknown sessionId` is paired by thread with the runtime's
`returned null` / `→ OHNativeWindow=` line. Example: wikipedia white r2, L21582–21587, session 702.

## 2. The change (`patch/android_graphics_compat_shim.cpp.patch`, one function + helpers)

`oh_wm_get_native_window` returns the resolved copy's answer as before. Only when it is **null** does it ask the
other loaded instances of `liboh_adapter_bridge.so`:

1. **Find our own copy.** `dl_iterate_phdr` finds the instance whose executable `PT_LOAD` holds the resolved function.
2. **Collect the other copies.** It collects the other instances whose code at the same offset is byte-identical for
   32 bytes, i.e. the same file. The address must lie in that instance's executable segment before it is read.
3. **Call only after the scan.** Nothing is called inside the `dl_iterate_phdr` callback, which holds the loader
   lock.
4. **Ask each copy.** Each collected copy's `oh_wm_get_native_window(sessionId)` is asked in turn. The copy that ran
   createSession holds the window in its `sessions_` and answers. On a hit the runtime logs
   `[M1-COPY] sessionId=%d resolved by bridge copy base=%p (resolved copy base=%p returned null)`.

`dl_iterate_phdr` on the board libc `fd3c4701` (`ld-musl-aarch64.so.1` @0x8a0e4, disassembled) walks the
process-global `head` DSO list without any namespace test. The only branch, on dso+0x1d8, substitutes the phdr
pointer. The OH musl source (`porting/linux/user/ldso/dynlink.c`, hw248 OH7 tree) is the same loop. So the second
bridge copy, loaded into another namespace, is listed.

## 3. No-op for single-session apps, and the exact set that changes

- **Single session.** The fallback runs only on a null from the resolved copy. In the 98 single-session runs every
  lookup was answered non-null (`../proof.json` claim b, 0 violations), so their path is byte-for-byte the old one:
  `nw != nullptr` → return it.
- **Multi-session.** A lookup that is null today is rescued now iff some other copy still holds the session, i.e. it
  was created and not destroyed. That is the same condition as the bridge-slot design. The lookups that change are
  the same 43 listed in `../proof.json` / `../predictions.csv`:
  - white: noice, fd-uhabits, dddmodel2;
  - lottery: wikipedia, fd-noice;
  - 10 lit keys on the regression watch.

## 4. Build (`build_runtime_u13.py` on a2hlab, the N10b smoke-markers recipe)

Same object cache (`.work/n4-registration-order`), frozen toolchain (`.work/product-tls-generation/frozen`) and
smoke-markers sources as `smoke-markers/build-runtime.py`. Sources are swapped by path in the recipe text; nothing in
the shared `.work` tree is edited (cc-wiki patched asset_manager in place and restored it).

| variant | what | sha256 |
|---|---|---|
| baseline | N10b baseline recipe | `216b68fb…` = U8 (asserted) |
| control | candidate recipe, `compat_shim.o` + `asset_manager.o` recompiled from the original sources | `ac59dec0…` = deployed (asserted) |
| m1 | control + M1 shim | `18a77eaa…` |
| u13 | m1 + cc-wiki asset_manager patch (applied with `git apply` to a copy) | `18763dd4…` |
| u13-repeat | same | `18763dd4…` (asserted) |

**Logs, written at run time:**
- `$WORKSPACES/westlake-inputs/generations/u13-runtime-m1-v1/logs/build-session.log` (live tee);
- `build/<variant>/build.log` (driver output per variant).

Run 1 stopped after the baseline on a script error (a missing `W` in an eval). Its log was overwritten through the
OrbStack mount cache; see `logs/r1-script-error.NOTE.txt`.

**Persisted:**
- `generations/u13-runtime-m1-v1/liboh_android_runtime-{u13-18763dd4,m1only-18a77eaa}.so`;
- hw248 `/home/alvin/u13-runtime-m1-cc-t3/` (both .so, session log, per-variant logs; SHAs read back).

## 5. Acceptance (`acceptance.py` → `acceptance.txt`, same checks as aa149019)

| check | u13 vs ac59dec0 | m1 vs ac59dec0 |
|---|---|---|
| objects differing (of 69) | `android_graphics_compat_shim.o`, `asset_manager.o` (= aa149019's `e448f07a`) | `android_graphics_compat_shim.o` |
| vs aa149019 | `android_graphics_compat_shim.o` only | – |
| exports (`nm -D --defined-only`) | identical | identical |
| undefined | + `dl_iterate_phdr` (board libc fd3c4701 exports it) | same |
| `deployed_strings_diff` | + `[M1-COPY]…` (see below) | same |
| `open_site_scan` | 198 = 198, normalized identical | same |

**Strings diff.** The tool reports 3 dropped / 4 added. One added is the marker. The other 3 pairs are layout, checked
by the script:
- each is an equal-length twin of a dropped one;
- one is the readelf `[ offset]` label of a `.rodata` string, pushed by exactly 0x5d = len(marker)+1;
- two are `.rodata` jump-table relative offsets whose bytes happen to print, e.g. `0xffff5e12` → `0xffff5e0f` before
  `St12length_error`.

No text string is dropped or changed.

## U13 composition and hand-over

- u13 = `aa149019` + `android_graphics_compat_shim.o`; the other 67 objects are unchanged.
- cc-wiki's aa149019 is superseded by this combined candidate only if both lanes agree. The board note asks cc-wiki
  which of us publishes the final one; until then both SHAs stand:
  - aa149019 alone (asset_manager);
  - 18763dd4 (both).
- On the board, M1 shows as `[M1-COPY]` lines in the 4 lottery/white keys and no `[M1-COPY]` in single-session apps.
  Judge by t20 k/n per `../predictions.csv`.
