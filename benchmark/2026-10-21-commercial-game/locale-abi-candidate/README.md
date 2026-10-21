# G30 source/owner first slice

G28 failed at `_ctype_@LIBC` relocation in `libyuanshen.so` (hilog L3259), followed by Unity load failure, unbound JNI and exit 1. Existing exports on disk did not prove visibility. This proposal targets that first fatal for **genshin only as a prediction**; integer locale imports are a same-source static cluster, not additional observed failures. No build or device action has occurred.

## Proposed wiring

Keep G26 host/ANL bytes. Add an exact independent copy of the existing 56-line `bionic_locale_compat.c` to the existing native ABI build, and add only `_ctype_`, `strtoll_l`, `strtoull_l` to its derived `LIBC` version script. Keep original `native_abi.c`, stdio, atfork/FD, constructors and exports. The candidate replaces only the native-path d205 component; no new leaf, namespace, GLOBAL operation, runtime/audio publication or Flutter ABI replacement. This component is shared by the existing native cluster, so behavior/ABI preservation is required beyond the predicted Genshin benefit.

All following source paths and exact bytes are pinned in `source-index.json`; numbered text is in `source-excerpts.json`.

1. G26 `app_native_loader.c:63–90,464–482` selects exact package components under the domain mutex. `flutter_domain.inc:22–32` puts `westlake_native` before app paths and selected load directory; no system root is added. Its `:38–51` creates the existing app/bridge pair with the existing shared names plus Genshin mediandk.
2. Host `candidate-stock-host.c:184–229` creates the bridge inheriting default and opens its pthread bootstrap with NOW|LOCAL. This is not the proposed locale owner.
3. Host `:246–284` creates the separated LOCAL_NS_PREFERED app namespace and its existing direct default/sealed-child inheritance edges. `:295` resident GLOBAL is gated to a different package subset; Genshin does not gain it. `:311` audio GLOBAL is gated to Mindustry/PPSSPP. `:329–334` retains the bridge inheritance edge.
4. Host `:345–356` already opens the exact absolute `westlake_native/libwestlake_native_abi.so` into the selected app namespace with NOW|GLOBAL. **This existing open-site is the proposed locale owner/publication**, not a new search edge. Host `:360–372` rejects app GLOBAL requests and opens the actual target LOCAL; ANL `:485–489` selects this prepared domain.
5. `zlib-route.h` and `resident-compat.h` are also pinned: their existing conditional search adjustment/NOLOAD probes remain unchanged. Host plugin NOLOAD (`:653`) is outside this per-app locale addition. No library-presence or early maps observation is used to establish a final relocation winner.

## ABI and reuse

`_ctype_` must be an 8-byte OBJECT pointer to a 257-byte table: EOF at 0, byte c at c+1. ASCII flags and zero high-byte entries come from the existing local implementation, not a new classification algorithm. The two integer functions forward to `strtoll/strtoull`, preserving their return/endptr/errno behavior and intentionally ignoring locale, as that existing source specifies. Original upstream AOSP byte provenance is not independently verified by its comments.

The G28 exact local ELF comparison already found all three exports in b8a (unversioned) and db31 (`LIBC`), but none in d205. This does not prove either former object wins in the failing app namespace. Their complete source-to-build chains remain unclosed here; copying the whole pthread provider or Unity stubs would introduce unrelated behavior. Reuse the isolated locale TU instead. `__assert2` stays secondary/caught background and is excluded. `__sF` and `__ctype_get_mb_cur_max` are not duplicated. Unversioned provider behavior is platform-dependent, not an assumed linker rejection.

## Baseline before candidate

The original N4 source, two-object recipe, historical log and local d205 ELF are present and SHA-pinned. Original recipe compiles both real source objects and links with the existing LIBC/LIBC_O map. Local frozen clang/lld, two relevant headers and libc/pthread inputs were read and hashed (see `baseline-input-audit.json`). This is a **partial input audit**, not a complete dependency/toolchain closure.

Historical U14 reproduction produced `554bf6bc…`, documenting equal allocated/code sections with path/debug differences. It is **not** a successful d205 exact baseline gate. After outer acceptance, first reconstruct the original path/debug/argv conditions in an isolated output and require full d205 SHA before compiling a locale candidate; retain any mismatch and original logs. Do not substitute U14 or its expanded exports. No historical script that mutates an old output will be executed.

Planned actual-function tests: all 257 classifications, pointer-vs-array ABI, signed/unsigned boundaries and overflow, bases/signs/no conversion/endptr/errno and supported locale behavior; wrong type/table/version rejection; complete old dynamic-symbol tuple/NEEDED and original constructor/atfork/FD/stdio comparison. Runtime namespace resolution and game frames remain UNKNOWN. These tests are not yet run.

## Checkpoint status

Contract rendering and lint ran rc0; this is a source proposal, not full task completion. Branch creation returned rc128 (shared refs write denied); private original argv/stdout/stderr/rc are retained and no retry was made. Work remains on the original branch with new files only. No build, REA, device, game modification or push.
