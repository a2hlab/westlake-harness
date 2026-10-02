# Toutiao ICU wall: the app namespace ships an incomplete AOSP public-library set (+ a symbol-versioning wall behind it)

Static analysis, offline, board #90, no board action. Toutiao's long-wait trial (cx-t0, 61b, U10.1T8) shows a white
t20 then back-to-desktop; the hilog ends in a SIGSEGV. This digs the crash, the namespace that caused it, and the second
wall behind it, and predicts U13. **Correction carried from the outer (01:51):** both U10.1T8 and U13 ship
`libicui18n.so` in the payload (`= libicui18n.z.so`, `40766b54`); `errno=2` is **ENOENT in the app namespace**, not a
missing file. So U13's first-fatal does **not** move — predicted 0.

## The crash (evidence/crash-hilog.txt, evidence/icuwrapper-disasm.txt)
```
01:38:33.474  load libicui18n.so failed, namespace=westlake.anl.app.29496.2, errno=2
01:38:34.329  #00 pc 0  Not mapped
              #01 libtttext_lite.so  ttoffice::tttext::ICUWrapper::ICUWrapper()+100
              #02 libart.so art_quick_generic_jni_trampoline   #03 nterp_helper
```
`libtttext_lite.so` (Toutiao's text engine) resolves ICU itself: it imports `dlopen/dlsym/dlerror`, and its `ICUWrapper`
ctor calls a lazily-bound ICU function pointer. Disassembly (`ICUWrapper::ICUWrapper` @ `0x1be50`):
- At ctor **+0x64** (`0x1beb4`, the crash frame): `blr x8`, where `x8 = ldr [x23, #0x2a0]` — a global function pointer at
  `0x442a0`. **There is no `cbz x8` before the `blr`** — the null is never checked.
- The args (`w0=0, x1=&locale, x2=0, w3=0, x4=&UErrorCode`) are an `ubrk_open(type, locale, text, len, *status)` call.
- The pointer is filled lazily (`brk_open` init behind a `__cxa_guard`): it `dlopen`s the ICU libs and `dlsym`s the
  cohort into `[0x442a0..]`. If init can't fill it (a lib didn't load, or a `dlsym` returned null), the pointer stays
  **null** and the ctor's `blr` jumps to 0 → `pc=0`.
- `dlopen` sonames (string table order = fallback order): `libkryptoni18n.so` (ByteDance's own ICU — **not bundled in
  this apk**) → `libicui18n.so` → `libicuuc.so`. `dlsym` names are **unversioned**: `ubrk_open`, `u_charType`,
  `u_hasBinaryProperty`, `icudt`, … — no `_NN` suffix anywhere in the binary.

## Why libicui18n.so is invisible — the app-ns public-library gap (evidence/appns-publiclib-gap.txt)
`westlake.anl.app.<pid>.N` is a restricted namespace built by `app-native-loader/src/app_native_loader.c` via
`create_configured_namespaces(... bridge_shared_sonames, ... app_search_paths, app_permitted_paths)`. The app ns gets
its own apk lib dir and a **bridge** soname allowlist — but **no argument carries the AOSP public-library set into the
app ns**. So the app can name only its own apk libs plus whatever is transitively pulled by the libs it links.

The outer's U12 census (`scripts/lab/dlopen_failures.py`, master `854c05ae0f`) lists exactly the `westlake.anl.app`
ENOENTs; cross-referenced against **AOSP 14 `public.libraries.android.txt`**
(`hw248:/home/alvin/aosp-14.0.0_r1-art/system/core/rootdir/etc/`), all of them are public libraries an app is allowed to
`dlopen` — `libicui18n.so`, `libvulkan.so`, `libGLESv2.so`, `libGLESv3.so`, `libjnigraphics.so` — **except**
`libandroidio.so`/`libjavacore.so` (ART-internal, not public → a separate issue). `libicuuc.so` is also public and it
*works*, only because it is DT_NEEDED by `liboh_android_runtime` + `libandroidfw` + `libminikin` (all app-reachable) and
is pulled in transitively; `libicui18n.so` is NEEDED only by `libminikin`/`libicu_jni` (loaded in the bridge/runtime ns,
not re-exported to the app ns by soname) → ENOENT. The runtime itself loads both ICU libs, but `RTLD_LOCAL` in its own
ns (`westlake_icu_overrides.cpp:378/385`), so those copies aren't nameable from the app ns either.

**So the root cause is one gap: the app ns does not expose the AOSP public-library set; `libicuuc` masking it is luck of
the dependency graph.**

## First-fatal per key — proximity ≠ cause (evidence/enoent-to-fatal.txt)
The outer's `--near-fatal 3` flags ENOENTs within 3 s of the fatal (same pid), but a near ENOENT is only the wall if it
*causes* the fatal. Tracing ENOENT → what-happened-between → fatal in each hilog:

| key(s) | ENOENT soname | public? | between ENOENT and fatal | first-fatal = this ENOENT? |
|---|---|---|---|---|
| **toutiao** (long-wait) | libicui18n.so | yes | ICUWrapper calls the unbound ICU fn-ptr immediately | **YES** (SIGSEGV) — but see Wall 2 |
| toutiao | libjnigraphics.so | yes | survived; fatal is libicui18n 8 s later | no |
| **fd-stk** | libGLESv2.so | yes | libSDL2 `dlopen_ns` fails → F02-A12 | **YES** (causal) |
| **subwaysurfers** | libGLESv3.so | yes | libvkquality `dlopen_ns` fails → SIGABRT, nothing recovers | **YES** (causal) |
| x (twitter) | libGLESv2.so | yes | libtwittermedia → `UnsatisfiedLinkError` (catchable); x signed white | **unconfirmed** |
| fd-fluffychat, fd-immich, fd-kitchenowl, fd-saber, localsend | libvulkan.so | yes | Vulkan ENOENT → **GLES also fails to load** (OpenGLWrapper) → survived → fatal is `GetLongField`→`JniAbort` from `libflutter.so` | **no** — fatal is the Flutter GetLongField/AAssetManager wall (`2026-10-02-u13-flutter-abort-3`, fixed U13 `18763dd4`) |
| antennapod, fd-client, fd-tusky, fd-tutanota | libandroidio.so / libjavacore.so | **no** | ART-internal, not public; fd-client is lit on U12 | no — separate root cause |

**Latent second wall for the Flutter keys:** their libvulkan ENOENT is pre-fatal noise *today*, but the same gap also
makes **GLES** unavailable ("Failed to load GLES library"). Once the GetLongField wall is cleared (U13 `18763dd4`), these
keys reach the renderer and hit "no Vulkan, no GLES" in the app ns — so the public-lib fix is needed for them too, just
not as their first fatal.

## Wall 2 (behind the namespace): symbol versioning
Even with `libicui18n.so` made visible, Toutiao `dlsym`s **unversioned** `ubrk_open`, but the deployed ICU
(U10.1T8 **and** U13) exports **only `_72`-renamed** names (`ubrk_open_72`, `u_charType_72`, `uloc_setDefault_72`;
`evidence/appns-publiclib-gap.txt`). `dlsym(handle, "ubrk_open")` → null → the **same** `blr 0` crash. Our ICU is built
with renaming on (`U_DISABLE_RENAMING=0`); Toutiao expects unrenamed ICU or its own `libkryptoni18n.so` (not bundled
here). So the namespace fix alone does **not** light Toutiao.

## Prediction for U13
- **Toutiao first-fatal does NOT move on U13 (= 0).** U13 has the same app-ns config and the same `_72`-only ICU; both
  the ns wall and the symbol wall are unchanged. Matches the outer's "U13 先当 0".
- **Next fail after ICU (if both walls were cleared):** the next public-lib ENOENT in the same ns — `libjnigraphics.so`
  (already ENOENTs for toutiao at 01:38:25) is the leading candidate once text/image init proceeds.
- **Keys the public-lib fix moves as their FIRST fatal:** `fd-stk` (GLESv2), `subwaysurfers` (GLESv3); possibly `x`
  (confirm the white root). It does **not** change the first fatal of the Flutter-vulkan keys (that is GetLongField,
  fixed separately by U13 `18763dd4`) or the libandroidio/libjavacore keys (ART-internal, not public).
- **…but the public-lib fix is still required for the Flutter keys as a SECOND wall:** after U13's GetLongField fix they
  reach the renderer and need GLES/Vulkan, which the same gap withholds. So completing the public-lib set + U13's
  asset_manager fix are complementary; neither alone lights fd-fluffychat/fd-immich/fd-kitchenowl/fd-saber/localsend.

## Minimal fix (and the double-copy question)
1. **Complete the app-ns public-library set.** Add the AOSP public sonames the census shows missing — `libicui18n.so`,
   `libGLESv2.so`, `libGLESv3.so`, `libvulkan.so`, `libjnigraphics.so` — to the app ns as **linked shared libraries from
   the platform/default ns** (the same mechanism that already makes `libicuuc.so` reachable), in the config passed to
   `create_configured_namespaces` (the appspawn-x stock child plugin / the deployed appspawn namespace config that
   supplies the app ns's shared-soname list — `app_native_loader.c` only forwards it). Because these resolve to the
   **already-loaded platform copy by soname**, this does **not** create a second copy. The wrong fix — adding
   `/system/android/lib64` to the app ns `app_search_paths` — would let the app ns load a **fresh second copy** of
   `libicui18n.so` (and pull a second `libicuuc.so`) distinct from the runtime's `RTLD_LOCAL` copy → two ICU states /
   data heaps → mismatch. Prefer the soname link, not a search path. Do **not** add `libandroidio`/`libjavacore` (not
   public, ART-internal — exposing them risks double-loading ART internals).
2. **(Toutiao only, Wall 2)** the ns fix is necessary but not sufficient: our ICU must also satisfy the unversioned
   `dlsym`. Either build the deployed `libicuuc.so`/`libicui18n.so` with unversioned aliases (`U_DISABLE_RENAMING=1` or
   an alias cohort), or supply the `libkryptoni18n.so` Toutiao looks for first. That is a separate artifact change
   (the ICU libs or the apk), independent of the namespace.

## Rule this round sets
`errno=2` on a `dlopen` is "not nameable in this namespace", not "file absent" — check the namespace's accessible/
public-lib set before concluding a lib is missing. For app-on-OH, the app ns must carry the AOSP public-library list;
one public lib working (`libicuuc`) can mask the gap when it rides in as a transitive dependency. And a `dlopen` success
does not imply the later `dlsym` succeeds — symbol versioning is a second, independent wall.

## Files
- `evidence/icuwrapper-disasm.txt` — ICUWrapper ctor disasm (the unchecked `blr x8` at +0x64), imports, dlopen/dlsym
  strings (unversioned), fallback order.
- `evidence/crash-hilog.txt` — the ns ENOENT + SIGSEGV backtrace (relativized paths).
- `evidence/appns-publiclib-gap.txt` — app-ns construction, AOSP 14 public list, the U12 census with public?/first-fatal,
  the DT_NEEDED pull explaining libicuuc-vs-libicui18n, the RTLD_LOCAL runtime load, and the `_72`-only export proof.
- `results.json`, `landing-paths.txt`.

## Boundaries
Offline, no board, nothing deployed. Sources read read-only (the apk in `vm-copies/apks-77`, the U13 ICU payload in
`westlake-harness-bms`, the hilog in `westlake-harness-u7-executor`, the native-loader source in `westlake-harness-bms`,
AOSP 14 on hw248). The fix points are for the runtime/appspawn owners; this is static triage only.
