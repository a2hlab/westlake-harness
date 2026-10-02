# U14 app-namespace public libraries: expose the AOSP public native libs, and fix the toutiao ICU-74-vs-72 wall

Static analysis, offline, board #90, no board writes (board facts are the outer's read-only reads). This continues the
toutiao ICU triage (`2026-10-03-toutiao-icu-wall`) with two corrections from the outer and the fix for both walls.

## Correction 1 — Wall 2 is an ICU VERSION mismatch, not "unversioned dlsym"
The prior round said tttext `dlsym`s unversioned names. **Wrong.** Disassembly of `brk_open`
(`evidence/brk_open-versiondetect.txt`): it `scandir("/system/usr/icu")`, `atoi`s the `icudt<N>` version, takes the max,
and `%s%s`-builds a **suffixed** symbol name (imports `scandir/alphasort/atoi`; strings `/system/usr/icu`, `icudt`,
`l.dat`, `%s%s`). The board (outer, read-only 61b) has `/system/usr/icu = icudt74l.dat` (ICU **74**), while
`/system/usr/ohos_icu` and `/system/android/etc/icu` are `icudt72l.dat` (ICU **72**). So tttext picks **74**, builds
`ubrk_open_74`, but our deployed Android `libicuuc.so` exports only `*_72` → `dlsym` null → the same `ICUWrapper` `blr 0`
crash. (Wall 1, the app-ns `libicui18n.so` ENOENT, still comes first; both must be fixed for toutiao.)

## Correction 2 — the Wall-1 fix is NOT in app_native_loader.c
`app_native_loader.c` / `libapp_native_loader.so` only *forwards* `app_search_paths`/`app_permitted_paths`; the host-op
`create_configured_namespaces` (ABI v1) has **no app-shared-soname parameter**. The app ns's visible libraries are set
in the **stock host** (`westlake_stock_host_main.c`, `StockCreateConfiguredNamespaces`, registered at `:424`):
```
app:  dlns_create2(app, app_search_paths, LOCAL_NS_PREFERED); dlns_set_namespace_separated(app, true);
      dlns_set_namespace_permitted_paths(app, app_permitted_paths);
      dlns_inherit(app, bridge, bridge_shared_sonames);   <-- app sees from the bridge EXACTLY these sonames
```
The app namespace inherits from the bridge **only** the sonames in `bridge_shared_sonames`. The bridge itself
`dlns_create2(..., CREATE_INHERIT_DEFAULT)` (inherits the platform ns) and permits `/system/android/lib64`, so it can
resolve both our Android libs and platform GL/Vulkan — but it re-exports to the app only that list
(`evidence/appns-inherit-mechanism.txt`). `libicuuc.so` works because it is in the list (or pulled as a NEEDED of a
listed lib); `libicui18n.so`, `libGLESv2/v3.so`, `libvulkan.so`, `libjnigraphics.so` are **not** → ENOENT.

## ① Where /system/usr/icu comes from, and who reads it (evidence/icu-sandbox-and-wall2-fix.txt)
- `/system/usr/icu` is part of the **OHOS base app sandbox** (OH mounts `/system/usr` into every app); our appspawn-x
  config does not remove it. Proven visible in the toutiao sandbox by the crash itself (scandir succeeded, selected 74).
- Our Android ICU is separate: `appspawn_x.cfg` sets `ICU_DATA=/system/android/etc/icu` (icudt72l) and the payload
  ships ICU-72 `libicuuc/libicui18n`. So the app has both an ICU-72 dir (ours) and an ICU-74 dir (OH's); tttext
  hard-codes the OH one.
- **Who else reads `/system/usr/icu`:** our Android payload libs — **none** (open-site scan of `bundle-v3` returned
  nothing), so a per-app remap does not disturb our payload. OH platform libs (on `/system/lib64`, not scannable here)
  do use `/system/usr/icu` = 74 → any `/system/usr/icu` change **must be per-app**, never global.

## ② Wall-2 minimal fix (version mismatch) — options + double-copy
- **(a, recommended)** Per-app sandbox: bind-mount an icudt72l dir (`/system/android/etc/icu` or `/system/usr/ohos_icu`)
  over `/system/usr/icu` **for the Android app domain only**. tttext then finds 72 → `_72` → matches our libs.
  Blast radius minimal (per-app, data-dir only). **Double-copy: none** (a data-dir bind-mount, not a library load).
- **(b, fallback)** Add `_74` alias exports to our Android `libicuuc/libicui18n` (alias cohort → `_72` impls). Keeps one
  library (no second copy) but touches a shared artifact and makes ICU-72 code answer as 74 (safe for the stable C ABI
  tttext uses, but a blanket promise). **Double-copy: none.**
- **(c)** Bump the Android ICU to 74 (full version bump; re-binds the runtime's `_72` cohort — biggest blast radius) or
  repoint tttext (needs apk edit — rejected). Not minimal.

## ③ Wall-1 fix — expose the AOSP public libs to the app ns (recipe/win-u14-appns-public-libs.patch)
Add the missing public sonames to the app↔bridge inherit. The patch augments the `dlns_inherit` list in
`StockCreateConfiguredNamespaces` with the AOSP-public set
`libicui18n.so:libicuuc.so:libGLESv2.so:libGLESv3.so:libvulkan.so:libjnigraphics.so` (leaving the bridge's own
`allowed_libs` unchanged). **`libandroidio.so`/`libjavacore.so` are excluded** (not in
`public.libraries.android.txt`; ART-internal — exposing them risks double-loading ART internals).
- **Double-copy: none.** `dlns_inherit` shares the bridge's already-resolved copy, and the bridge inherits the single
  DEFAULT-ns platform copy. (The *wrong* fix — adding `/system/android/lib64` to the app ns `app_search_paths` — would
  load a fresh second `libicui18n.so` + `libicuuc.so` into the app ns, distinct from the runtime's `RTLD_LOCAL` copy →
  two ICU heaps.)
- **Byte-reproduce target correction:** the dispatch said reproduce `libapp_native_loader.so` first (N10b). But that lib
  holds no soname list — the change is in the **stock host** artifact (the `stock_child_plugin` / appspawn-x host that
  provides `StockCreateConfiguredNamespaces`). The N10b byte-reproduce + patch must target that artifact. The exact
  per-app populator of `config.bridge_shared_sonames` (assembled in `native_loader_registry.cpp`; the in-source default
  is `{"libc.so","liblog.so"}`) should be pinned too, in case the list is better extended there.

## Prediction table (by first-fatal; evidence/… + 2026-10-03-toutiao-icu-wall)
| key | first-fatal | needs |
|---|---|---|
| **toutiao** | libicui18n.so ENOENT → ICUWrapper | **Wall 1 (public-lib)** + **Wall 2 (ICU 74↔72)** — both; neither alone lights it |
| **fd-stk** | libGLESv2.so ENOENT (via libSDL2) | Wall 1 |
| **subwaysurfers** | libGLESv3.so ENOENT (via libvkquality) | Wall 1 |
| fd-fluffychat, fd-immich, fd-kitchenowl, fd-saber, localsend | GetLongField/AAssetManager (U13 `18763dd4`) | U13 asset fix now; Wall 1 as a **second** wall (no Vulkan/GLES) once they reach the renderer |
| x (twitter) | libGLESv2 present but UnsatisfiedLinkError may be caught; white root unconfirmed | TBD |

## Honest status
- The patch (`recipe/win-u14-appns-public-libs.patch`) applies against the current `westlake_stock_host_main.c` (context
  verified at the `dlns_inherit` site, line 217). **The byte-faithful reproduce + build of the U14 native candidate was
  NOT run this turn** — the dispatch's repro target (`libapp_native_loader.so`) is the wrong artifact (it carries no
  soname list), so the correct target (the stock-host plugin) and its N10b recipe must be confirmed before building.
  That build is the next concrete step.
- No board writes. Board ICU facts are the outer's read-only reads; `/system/usr/icu` visibility in the app sandbox is
  proven by the crash. Sources read read-only from `westlake-harness-bms`, `vm-copies/apks-77`,
  `westlake-harness-u7-executor`.

## Files
- `evidence/brk_open-versiondetect.txt` — Wall-2 correction: the scandir/atoi/%s%s version-detect disasm + the 74-vs-72 data.
- `evidence/appns-inherit-mechanism.txt` — the `dlns_inherit(app, bridge, bridge_shared_sonames)` mechanism + the real fix location.
- `evidence/icu-sandbox-and-wall2-fix.txt` — /system/usr/icu provenance, who-reads, the Wall-2 fix options.
- `recipe/win-u14-appns-public-libs.patch` — the Wall-1 patch (app-ns public-lib exposure), context-verified.
- `results.json`, `landing-paths.txt`.
