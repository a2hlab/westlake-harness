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

## 6. Step 3 (the rebuilt candidate) — blocked on the native build closure
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
