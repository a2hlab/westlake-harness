# U12 native cluster — ICU zero-init wall (fd-wifianalyzer + fd-breezyweather)

Offline, no board. Root-causes the two "ICU" U12 keys to a single native defect, proves our **deployed**
`libicu_jni.so` was built **without** the fix, shows the fix's codegen effect at instruction level, and predicts
both keys' first fatal after the fix. The rebuilt candidate (`libicu_jni.so` with the flag) is the one remaining
mechanical step; it is **blocked on the native build closure** (see §6) and ships here as a ready-to-run recipe plus
binary-feature + codegen evidence, which the dispatch explicitly accepts in lieu of the rebuild
("找不到就从二进制特征判断,写明依据").

## 0. The two keys and their observed first fatal (U9 sign-off)
Source: `benchmark/2026-10-01-u10-first-wall/u9-first-wall.json`.

| key | verdict | family | first_fatal (verbatim) |
|---|---|---|---|
| fd-wifianalyzer | dead | java:NullPointerException | `[CHILD_CK] J_invokeStaticMain_main_threw: java.lang.RuntimeException: Unable to start activity ComponentInfo{com.vrem.wifianalyzer/...}` |
| fd-breezyweather | dead | java:NullPointerException | `[CHILD_CK] J_invokeStaticMain_main_threw: java.lang.RuntimeException: Unable to start activity ComponentInfo{org.breezyweather/...}` |

Both: `Caused by: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.Class
java.lang.Object.getClass()' on a null object reference`. cc-t3's total table attributes the null to Locale:
wifianalyzer `String.toUpperCase(Locale)→null`, breezyweather `Locale...getDisplayCountry→null`. The deeper Java
stack frames are cc-t3's attribution (the U9 hilogs are not in this worktree; the local hilogs under
`benchmark/2026-10-01-u7-sweep/**` are an earlier generation where these two apps progressed further — not the U9 wall).

## 1. Root cause — ONE line of source, shared by both keys
`external/icu/.../ScopedIcuLocale.h:39` (AOSP `aosp-14.0.0_r1-art`, snippet in `evidence/scopedicu-source.txt`):

```cpp
UErrorCode err;                                                  // line 39 — NOT initialized
icu::Locale locale = icu::Locale::forLanguageTag(languageTag.c_str(), err);   // line 40
if (U_FAILURE(err)) { return; }                                 // line 41 — garbage err reads as failure
// -> mLocale stays bogus -> valid()==false
```

ICU's universal contract: **every ICU function early-returns if the incoming `UErrorCode` already indicates failure,
without modifying it.** A `UErrorCode` left uninitialized holds stack garbage; whenever that garbage is `> U_ZERO_ERROR`
(any non-zero that reads as a failure) `forLanguageTag` does nothing, `U_FAILURE(err)` is true, the locale stays bogus,
and `valid()` is false. Because stack garbage is ~random, this fails on **about half** of calls — a native-layer white
lottery. (03678da's own message: "LocaleNative returned null on about half of all calls and Locale.getDisplayName threw
(WiFiAnalyzer)" — the upstream author names one of our two keys directly.)

Both keys route through this **same** constructor:
- fd-breezyweather: `Locale.getDisplayCountry` → `LocaleNative_getDisplayCountryNative` → `ScopedIcuLocale(...)` →
  `!valid()` → `return NULL` (`com_android_icu_util_LocaleNative.cpp:36-48`).
- fd-wifianalyzer: `String.toUpperCase(Locale)` → `CaseMapperNative_toUpperCase` → `ScopedIcuLocale(...)` →
  `!valid()` → `return NULL` (`com_android_icu_util_CaseMapperNative.cpp:42-55`).

The JNI returns `null` to Java; the app's `Activity.onCreate` then invokes a method on that null → the NPE →
`Unable to start activity`. One defect, one binary (`libicu_jni.so`), two keys.

## 2. Our DEPLOYED libicu_jni was built WITHOUT the fix (provenance, airtight)
`evidence/provenance-proof.txt`:
- `vm-copies/westlake-current` HEAD = **532633d** (our deployed source line).
- `git merge-base --is-ancestor 03678da 532633d` → **NO**: the fix commit 03678da is **not** in our deployed source.
- `build_android_native.py @ 532633d` → **0** occurrences of `trivial-auto-var-init` (no zero-init flag at build time).

Binary features of the deployed artifact (`evidence/deployed-binary-features.txt`, sha `4261c09e…`):
- compiler: `OHOS (dev) clang version 15.0.4 (llvm-project feef13a36e78…)` — clang 15, the version that needs the
  opt-in gate (see §3).
- symbols present: `ScopedIcuLocale::ScopedIcuLocale(_JNIEnv*, _jstring*)`, `LocaleNative_getDisplayCountryNative`,
  `CaseMapperNative`, the `icu_72::Locale::getDisplay*` externs — i.e. exactly the buggy call sites, in this binary.
- `auto-var-init` traces: **count=0** — consistent with a build that never passed the flag.

## 3. The fix (03678da) and WHY it needs two flags
`evidence/03678da-zeroinit.patch` — the commit changes **only** `tools/build_android_native.py`, +5 lines, adding
after the `-ffile-prefix-map` line:
```python
'-ftrivial-auto-var-init=zero',
'-enable-trivial-auto-var-init-zero-knowing-it-will-be-removed-from-clang',
```
The second line is **not redundant**: on clang 15 the `=zero` mode is gated behind that internal `-enable-…` switch
(the name encodes that it was a temporary knob). Without the gate, clang 15 would reject/ignore `=zero`. AOSP passed
both for exactly this clang era; the patch mirrors AOSP. (This project builds native code with our pinned clang
15.0.4 feef13a3 — the same provenance as the deployed binary — so both flags are required.)

## 4. Codegen proof — the fix is ONE instruction at the err slot
`evidence/scopedlocale_reduction.cpp` is a faithful reduction of `ScopedIcuLocale.h:39-43` (uninitialized
`UErrorCode`, passed to an ICU-style early-returning function). Compiled for aarch64 two ways; full output in
`evidence/{noflag,zeroinit}.s`, diff in `evidence/codegen.diff`:

```asm
  sub  x1, x29, #4            ; x1 = &err
+ stur wzr, [x29, #-4]        ; ★ err = 0 (U_ZERO_ERROR) — present ONLY with -ftrivial-auto-var-init=zero
  bl   _Z14forLanguageTagPKcRi
  ldur w8, [x29, #-4]
  cmp  w8, #0
```
- **noflag** (= our deployed build): no store to the `err` slot before the call → `forLanguageTag` receives stack
  garbage → ICU early-returns → bogus locale → null → NPE (~half the time).
- **zeroinit** (= 03678da): a single `stur wzr, [x29, #-4]` zeros the slot first → `err = U_ZERO_ERROR` →
  `forLanguageTag` runs normally → valid locale → non-null → **no NPE, deterministically**.

Caveat: the demo uses Homebrew clang 22.1.8 (arm64), which has `=zero` as GA (no gate). It demonstrates the flag's
**codegen effect on the exact pattern**; it does **not** reproduce the clang-15 gate requirement (that rests on §3's
patch + the clang-15 provenance). It is a mechanism demo, not the shipping rebuild.

## 5. Prediction — both keys' first fatal, before vs after the fix (step 4)
| key | native path | before fix (observed) | after fix (predicted) |
|---|---|---|---|
| fd-breezyweather | `getDisplayCountry` → `LocaleNative_getDisplayCountryNative` → `ScopedIcuLocale` | NPE `getClass() on null`, Unable to start activity (dead, ~50% lottery) | ICU `err=0` → valid locale → non-null display string → **NPE cleared**; next wall = whatever follows onCreate (expected: reaches draw; may then meet the generic render-white lottery, a different wall) |
| fd-wifianalyzer | `toUpperCase(Locale)` → `CaseMapperNative_toUpperCase` → `ScopedIcuLocale` | same NPE family, Unable to start activity (dead, ~50% lottery) | same: non-null `toUpperCase` result → **NPE cleared**; next wall as above |

Falsifier: if either key still throws the **same** `getClass()`-on-null NPE after a libicu_jni built with the flag,
the root cause is not (only) the uninitialized `UErrorCode`. Because the fault is a ~50% lottery, judge over a repeat
(a single lit does not prove the fix; a single dead-with-same-NPE does refute it only if reproduced).
`deployed_strings_diff.py` is deferred to the rebuild (it diffs a candidate against the deployed binary — no candidate
yet); `open_site_scan` is not applicable (it maps library-open namespaces, not this JNI-return defect).

## 6. Step 3 (the rebuilt candidate) — DONE on the a2hlab verify tree (see §8); recipe below
> Update 2026-10-02: the rebuild was authorized and executed on the a2hlab VM. Results in §8. The paragraph below
> documents why a *local* build fails and the recipe; the build itself succeeded on the a2hlab verify closure.
`tools/build_android_native.py --library libicu_jni.so` needs a self-contained **workspace** with
`toolchains/{ohos-sdk/native, clang-15}` + the `android-source/` header+source closure. Inventory
(`native/libraries.json`): **16 sources** (incl. `com_android_icu_util_LocaleNative.cpp`,
`com_android_icu_util_CaseMapperNative.cpp`, `westlake/native/src/icu_art_entry.cpp`), **22 include dirs** (19 global
`android-source/*` + 3 ICU dirs), **5 link deps** (`libicuuc/libicui18n/libnativehelper/libbase/liblog.so`).

Neither the local `ws/westlake` (22b9453), `vm-copies/westlake-current` (532633d), nor the OrbStack a2hlab checkout
carries `android-source/` or the toolchains — a local build fails at
`ValueError: Missing declared include directory: android-source/logging/liblog/include`. The route-A frozen toolchain
(clang-15 + sysroot, 2.4 GB) and AOSP source live only on **hw248** (`/opt/wl-src/.work/product-tls-generation/`,
`/home/alvin/aosp-14.0.0_r1-art`); RUNBOOK E.74 requires copying them back and building locally with dockbuild, not
building on hw248.

**Ready-to-run recipe** (once the workspace `$WS` is staged with toolchains + android-source):
```sh
# 1) patch the two flags onto our deployed source build driver
git -C vm-copies/westlake-current apply benchmark/2026-10-02-u12-icu-zeroinit/evidence/03678da-zeroinit.patch
# 2) two byte-identical builds with the flag (SOURCE_DATE_EPOCH/TZ/LC_ALL pinned inside the driver)
for n in a b; do
  python3 vm-copies/westlake-current/tools/build_android_native.py \
    --workspace "$WS" --out out/libicu-zeroinit-$n --target ohos --library libicu_jni.so \
    2>&1 | tee out/libicu-zeroinit-$n.log
done
sha256sum out/libicu-zeroinit-{a,b}/libicu_jni/libicu_jni.so   # must match (byte-identical)
# 3) no-flag reproduce to byte-confirm it matches the deployed 4261c09e (proves deployed lacked the flag)
python3 vm-copies/westlake-current/tools/build_android_native.py \
  --workspace "$WS" --out out/libicu-noflag --target ohos --library libicu_jni.so
```
Persist candidate + logs + toolchain hash to `westlake-inputs/generations/` and hw248 `/home/alvin/` (DIGEST E.7:
never leave a runtime artifact without its source/toolchain closure).

## 7. What was wrong before / rule set this time
- **Before:** these two were logged as generic `java:NullPointerException` dead keys; the null looked app-side.
- **Rule:** a `getClass()`-on-null NPE at `Activity.onCreate` whose cause traces to a `Locale`/`toUpperCase(Locale)`
  call is a **native ICU** wall, not an app bug — `LocaleNative`/`CaseMapperNative` return null via `ScopedIcuLocale`
  when `libicu_jni.so` is built without `-ftrivial-auto-var-init=zero`. Any native library we build and ship must
  carry AOSP's zero-init flags (clang 15 needs both). The `deployed_strings_diff` gate should refuse a candidate whose
  source relies on zero-init when the flag is absent from the build record.

## 8. Build result — authorized a2hlab rebuild (2026-10-02)
User authorized building on the lab infra ("只构建不碰板"). The Android-native verify closure lives on the **a2hlab
OrbStack VM** (`~/a2hlab/ws`: `toolchains/ohos-sdk/native` OHOS clang **15.0.4 feef13a3 — byte-identical version to
the deployed binary**, `android-source` 16 GB, `out/`), not hw248 (which carries only the route-A/appspawn frozen
chain). Built there with `build_android_native.py --workspace ~/a2hlab/ws --target ohos --library libicu_jni.so`
(deps libicuuc/libicui18n/libnativehelper/libbase/liblog auto-built). Source equivalence: the three libicu inputs are
blob-SHA-identical between `ws/westlake@22b9453` and deployed source `532633d`, so the build is equivalent to 532633d
for this library. Determinism env (`SOURCE_DATE_EPOCH=1772755200, TZ=UTC, LC_ALL=C`) pinned inside the driver.

**Two builds per variant, byte-identical:**
| variant | sha256 | bytes | note |
|---|---|---|---|
| no-flag ×2 | `be7697a2…` | 147896 | noflag-a == noflag-b (reproducible) |
| **flag ×2 (candidate)** | `ef14f232…` | 147896 | flag-a == flag-b (reproducible) |

Persisted: hw248 `/home/alvin/u12-icu-cc-wiki-20261002/` + a2hlab `~/a2hlab/ws/out/u12-icu-cc-wiki-20261002/`;
`candidate/{build.log,candidate-manifest.json}`.

**flag ↔ no-flag (the clean, ICU-noise-free comparison) — the fix is pure zero-init codegen:**
- `deployed_strings_diff`: **0 strings added, 0 dropped** (`candidate/strdiff_flag_vs_noflag.txt`).
- exports **71 == 71** identical; undefined/consumer symbols **171 == 171** identical → **ABI and consumers unchanged**.
- library-wide zero-init stores **43 → 52 (+9)**; in `ScopedIcuLocale::ScopedIcuLocale` the flag inserts
  `str wzr, [x29, #0x1c]` — zeroing the `UErrorCode err` slot — immediately before the `forLanguageTag` call; the
  no-flag build has **no** store to that slot (`candidate/ctor-zeroinit-proof.txt`). This is the §4 reduction demo
  confirmed in the real OHOS-clang binary.

**flag ↔ deployed `4261c09e` (the comparison the dispatch named):** `deployed_strings_diff` = **6 dropped, 23 added**
(`candidate/strdiff_flag_vs_deployed.txt`) — but these are **ICU 72 → 75.1 churn** (getISO3Language, metaZones,
zoneinfo64, timezoneTypes, windowsZones…), not zero-init. Cause: the deployed cluster is **icu_72**; the a2hlab
`android-source` is a single vendor snapshot at **ICU 75.1** (`be65bb2`, no 72 ref). So this candidate (`ef14f232`,
icu_75) is **not a drop-in** for the icu_72 deployed cluster, and the clean "only zero-init" diff is the flag↔no-flag
one above, not flag↔deployed.

**For a byte-faithful icu_72 drop-in candidate** (outer-loop decision — it is an *inputs* choice, not a code one):
either (a) stage the Aug-6 icu-72 vendor snapshot that built the deployed cluster (currently overwritten by 75.1 on
a2hlab), or (b) swap `android-source/icu` to hw248's `aosp-14.0.0_r1 external/icu` (72.1) and rebuild — approximate,
and byte-match only if that vendor snapshot carried no local patches. Pick (a) for an exact single-library swap, or
accept a whole-ICU-cluster bump to 75 (bigger change, out of the "only this one library" scope).

**Prediction unchanged (§5):** the candidate clears both keys' `ScopedIcuLocale`→null NPE deterministically (the err
slot is now zeroed before every ICU call); next wall expected to be the generic render-white lottery, judged over a
repeat.

## 9. ICU-72 rebuild (authorized: aosp-14.0.0_r1 72.1) — GATE 1 pass, GATE 2 STOP
Per the ICU-72 ruling, rebuilt libicu_jni against hw248 `aosp-14.0.0_r1 external/icu` (72.1) in an **isolated**
workspace `~/a2hlab/ws-icu72` (per the correction: the shared `android-source/icu` was NOT swapped — ws-icu72
symlinks the shared toolchains/westlake/android-source and points only `android-source/icu` at the 72.1 tree, with a
patched `build_android_native.py` copy; the shared tree stayed at 75.1 throughout). Scope = **only libicu_jni**:
`libraries.json` copy set `deps:[]` + `libraries:[the 5 deployed icu_72 .so]`, so the deps are NOT rebuilt — libicu_jni
compiles against 72.1 headers and links against the deployed icu_72 libicuuc/libicui18n/libnativehelper/libbase/liblog.
The 72.1 bridge set matches the deployed (both lack `UResourceBundleNative.cpp`, which the 75-era libraries.json added);
that one source was dropped from the copy's list. Two byte-identical builds (`candidate-icu72/`, persisted
hw248:/home/alvin/u12-icu-cc-wiki-20261002/icu72):
- no-flag ×1: `d30419a3…` 145816 B
- **flag ×2 (candidate): `76acad17…` 147400 B** (byte-identical) — zero-init confirmed: ctor gains
  `str wzr,[x29,#0x1c]` before `icu_72::Locale::forLanguageTag`; no-flag has none.

**GATE 1 — imported ICU symbols all `_72` and identical to deployed: PASS.** 56 icu-undefined symbols, every one
`icu_72`, set identical to the deployed `4261c09e` (diff empty, per-version-bucket counts identical). The icu-72
approach is sound.

**GATE 2 — overall ABI/consumer == deployed: FAIL → STOP (per "不一致就停并报").** The candidate carries exports and
imports the deployed lacks — and this is a **current-vs-deployed build-config drift, not an ICU-version or build-setup
artifact** (the earlier icu75 candidate `ef14f232` has the exact same surface):

| | deployed 4261c09e | both candidates (icu75 & icu72) |
|---|---|---|
| `JNI_OnLoad` | plain `JNI_OnLoad` | `JNI_OnLoad_icu_bridge` (renamed by the `JNI_OnLoad=` define) + `JNI_OnLoad_icu` |
| `register_libcore_icu_ICU` | absent | present (libcore_icu_ICU.cpp compiled in) |
| `uloc_*_72` imports | none | 9 (`uloc_getDefault_72`, `uloc_getScript_72`, …) |

Root: the deployed `4261c09e` was built from an **older** libicu_jni config (no `libcore_icu_ICU.cpp`; `JNI_OnLoad`
not renamed). The current `native/libraries.json` (blob `18d6ab09`, identical at 532633d and 22b9453) added
`libcore_icu_ICU.cpp` and `defines: JNI_OnLoad=JNI_OnLoad_icu_bridge`. So no build from the current source config can be
ABI-identical to the deployed binary, regardless of ICU version. `deployed_strings_diff` candidate↔deployed = 5
dropped / 14 added (the libcore_icu_ICU strings + a few 72.1-vendor deltas) — far smaller than the icu75 churn, and
consistent with this config delta. Evidence: `candidate-icu72/symbol-gate.txt`, `strdiff_icu72flag_vs_deployed.txt`.

**Outer decision needed (an inputs/architecture question, not code):** is the drop-in target (a) the deployed
`4261c09e` exactly — then it must be rebuilt from the *deployed-era* libicu_jni config (no libcore_icu_ICU, plain
JNI_OnLoad), which is a config rollback beyond this task; or (b) the **current** generation config — then the icu72
candidate `76acad17` IS correct (icu_72 imports match deployed, zero-init applied, current export surface) and the
deployed `4261c09e` is simply an older build. I stopped at the gate rather than ship a candidate whose entry-point
symbol (`JNI_OnLoad` vs `JNI_OnLoad_icu_bridge`) differs from the deployed binary the dispatch named.

## 10. ICU-72 ruling (a) single-variable: deployed-era config — ABI reproduced, byte-match NOT achievable (STOP)
Ruling (a): target = the deployed `4261c09e` config + only `-ftrivial-auto-var-init=zero`. The deployed-era libicu_jni
config is NOT in git history (libicu_jni first appears at `fe965fb` already carrying libcore_icu_ICU + the JNI_OnLoad
rename). Reconstructed it from the deployed's ABI fingerprint: current 16 sources **minus** `icu_art_entry.cpp`
(defines `JNI_OnLoad_icu`→`register_libcore_icu_ICU`), `libcore_icu_ICU.cpp`, `UResourceBundleNative.cpp`, and
**dropping** the `JNI_OnLoad=JNI_OnLoad_icu_bridge` define = **13 sources**, link against the 5 deployed icu_72 .so.

**Config IS correct — exports reproduce the deployed surface exactly** (`/usr/bin/diff`, authoritative — the DevEco OH
`diff` on PATH rc0's silently on differing files, RUNBOOK; all ABI diffs here re-run with `/usr/bin/diff`):
- no-flag `4f55ebf2` (134080 B) vs deployed `4261c09e` (132752 B): **exports IDENTICAL (63=63)** — 9 registers, plain
  `JNI_OnLoad`, no `register_libcore_icu_ICU`. undefined 160=160, differing only by `__android_log_*@LIBC` (version
  annotation) and one libc++ inlining delta (`memmove` vs a `basic_string` copy-ctor) — contract-equivalent.
- flag candidate `1e206531` (135568 B, byte-identical ×2): exports identical to no-flag, plain `JNI_OnLoad`, icu
  imports all `icu_72`, zero-init present (ctor `str wzr,[x29,#0x1c]` before `icu_72::forLanguageTag`).

**Byte-match vs `4261c09e`: NOT achievable → STOP (per "必须逐字节相同…做不到就报差在哪、停").** The residual is pure
build-provenance, not config (`deployed_strings_diff`):
1. embedded source paths — deployed `/data/aosp/external/icu/...` vs ours `/src/android-source/icu/...`: the deployed was
   built from a **real AOSP tree at `/data/aosp`** with `-ffile-prefix-map=…=/data/aosp`, not westlake's `android-source/`
   layout + `=/src`.
2. vendor log strings in deployed, absent in aosp-r1 72.1: `libicu_jni JNI_OnLoad`, `libicu_jni JNI_OnUnload` (the
   deployed's bridge had load/unload logging the stock 72.1 source does not).
3. libc++ inlining delta (`memmove` vs `basic_string` ctor) — a slightly different libc++ than the ohos-sdk one.

**Conclusion:** the deployed `libicu_jni.so` was **not built by `build_android_native.py`** — it came from a different
build system (a real AOSP checkout at `/data/aosp`, vendor-patched bridge, different libc++). So a *byte-identical*
reproduction is impossible without the deployed's original AOSP build inputs, which are not in any repo here. What IS
achievable and in hand: an **ABI-identical** deployed-era candidate `1e206531` (deployed export surface + plain
JNI_OnLoad + icu_72 imports) carrying exactly one added variable, `-ftrivial-auto-var-init=zero`. Stopping at the
byte-match gate; outer to decide whether ABI-identical + the single zero-init variable suffices, or whether to source
the deployed's original AOSP build inputs for a byte-exact build. Evidence: `candidate-icu72dep/symbol-gate-usrbindiff.txt`.
