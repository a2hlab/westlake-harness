# frequent-habits `$float:125835722` — CORRECTED root (ground-truth aapt2 + hilog) + icon-fallback marker

> **CORRECTION (supersedes this file's earlier 2026-10-01 version and board PROGRESS(80) 13:03:54).** The earlier
> claim — "`$float:125835722` = `0x078019ca`, package `0x07` = a runtime shared-library resource the APK→hap
> converter can't resolve (no `RES_TABLE_LIBRARY` 0x0203 handling)" — is **wrong on every count**. It was an
> id-decode asserted *without* checking the APK or the hilog consumer. Two ground-truth reads disprove it:
> (1) `aapt2 dump` — the APK has **only package `0x7f`**, zero rasters, **no library/dynamic-ref table**;
> (2) the hilog — the `$float` error is emitted by **sceneboard (the launcher), from its ACE/ArkUI theme engine**,
> not by the icon path, and the bundle **installed successfully**. Family: `runtime-unverified`.

## 1. Ground truth

### 1a. aapt2 dump (`build-tools/37.0.0/aapt2`, APK `westlake-inputs/corpus-v2/apks/com.frequent.habits_17.apk`)
```
package: name='com.frequent.habits' ... compileSdkVersion='36'
application: label='Frequent Habits' icon='res/BW.xml'     # icon is an XML drawable
Package name=com.frequent.habits id=7f                      # the ONLY package; id 0x7f (app)
# (no "DynamicRefTable" / "Shared libraries" / package id 0x07 anywhere)
```
`res/BW.xml` xmltree → an **adaptive-icon** whose layers are all app-package `drawable/*`:
```
E: adaptive-icon
   background → @0x7f05000e   (drawable/*)
   foreground → @0x7f05000f   (drawable/*)
   monochrome → @0x7f05000f   (drawable/*, Material-You themed layer)
```
The APK has **0 png/webp** under any `res/drawable|mipmap` path — it is a **pure-vector adaptive icon, no raster
in any bucket**. So `0x07` is **neither an in-APK second package chunk nor an external shared library** — it does
not exist. The number `125835722` is an **OpenHarmony hap resource id** (OH's own id scheme); decoding it with
Android's `pkg|type|entry` layout (which produced the bogus "pkg 0x07") was category-confused — different runtime,
different id space.

### 1b. hilog (`…/cv2-hilog/61b/…/cv2-com-frequent-habits/hilog.txt:479`)
```
10:16:46.245  2010 2010  UiTestKit_Server: Inject keyEvent up, keycode:1          # test-injected key
10:16:46.247  2010 2010 E ResourceManager: ref $float:125835722 id not found      # x4
10:16:46.247  2010 2010 W AceResource: Get pattern by name error, name=app_theme_pattern
10:16:46.247  2010 2010 W AceTheme: style app_theme_pattern not contains app_theme_drag_distancethreshold!
```
- **PID 2010 = sceneboard `SCBDesktop6`** (the launcher; cf. `A01b01/HOME: SCBDesktop`, `A01c06/ICON:
  AppIconCommonEvent`, `SCBSystemSceneSession`), **not** the app process and **not** installd.
- The `$float` miss is bracketed by **`app_theme_pattern` / `app_theme_drag_distancethreshold`** — an **ArkUI/ACE
  system *theme* pattern** lookup, fired on a **UiTestKit-injected key event**. `$float:125835722` is an ACE theme
  float resource, resolved by the launcher's `ResourceManager` — it has nothing to do with frequent-habits' icon
  or the APK→hap conversion.
- `install.txt` line 1: **`install bundle successfully.`** The bundle installed.
- Scope: `$float:125835722` / `app_theme_pattern` appear in **only frequent-habits' window out of the 33 app
  windows** in this run — but emitted by the *launcher* during an injected key event, i.e. a launcher/ACE theme
  gap surfacing during that window, not an app-caused error. (Not asserted to be app-specific; the owner is ACE.)

## 2. What this means for the two questions

**Q "$float not found" → NOT an apk_installer bug.** It is a **sceneboard/ArkUI (ACE) theme-pattern resolution
gap**: the launcher's `app_theme_pattern` style is missing a `$float` attribute (`app_theme_drag_distancethreshold`
and the `$float:125835722` it chases). Owner = the ACE/sceneboard theme resources, **not**
`bms/src/adapter/.../apk_installer.cpp`. No installer patch can fix it. Route to the sceneboard/ACE-theme lane.

**Q "no desktop icon" → the icon fallback already exists in apk_installer.cpp; the gap is deploy + observability.**
frequent-habits' icon is a pure-vector adaptive icon = the installer's existing **`DECLARED_XML_ONLY`** class
(added for fd-k9, B7 2026-09-29). On current source the path is:
`ReadIconByManifest` (adaptive compose fails on vector layers → false) → `ReadApkLauncherIcon` (no raster → false) →
`ClassifyIconlessApk` → **`DECLARED_XML_ONLY`** (icon id resolves to `res/BW.xml`, `.xml`, and `ZipHasAnyIconEntry`
is false) → **not** `FAIL_CLOSED` → `ReadTemplatePlaceholderIcon` → packs the template's generic placeholder, under
the `ICONLESS_APK_TEMPLATE_PLACEHOLDER` alarm (`apk_installer.cpp:677`). So **"icon resolve fails → fall back to
the default icon bytes" (Fix A) is already implemented** for this exact case.
- Pre-B7 installers instead hit `return FAIL_CLOSED` ("declared raster present, but unusable") for an
  icon that resolves only to `.xml` → **no placeholder packed → no desktop icon** (while the legacy carrier still
  lets `install bundle successfully` — it "is not an Fn01.A08 verdict source", `apk_installer.cpp:658`).
- **Outer-ring correction (2026-10-01):** the **U8-deployed** `libapk_installer.so` (`7048c7c50a82`) **already
  contains B7**, so on U8 frequent-habits takes the `DECLARED_XML_ONLY → placeholder` path and already emits its
  own install-time log `ICONLESS_APK_TEMPLATE_PLACEHOLDER: apk=… class=…`. So the pre-B7 fail-closed is **not** the
  U8 cause, and **no `apk_installer.cpp` patch is needed** — the existing log IS the activation marker.

## 3. Activation marker: use the installer's existing log (no patch)

The behavioral fallback (`DECLARED_XML_ONLY → ReadTemplatePlaceholderIcon`) and its activation log already ship in
U8's `libapk_installer.so` (`7048c7c50a82`). The new activation-smoke gate asserts the fix fired by grepping that
existing line — **no added `[ICONFB]` marker, no patch** (the earlier `apk_installer-iconfallback-marker.patch` in
this dir was withdrawn as redundant):
- **Existing activation log (`apk_installer.cpp:677`):**
  `ICONLESS_APK_TEMPLATE_PLACEHOLDER: apk=<apk> class=<IconlessApkClass>`
- **Smoke marker regex (`fixes[].markers`):** `ICONLESS_APK_TEMPLATE_PLACEHOLDER: apk=.* class=DECLARED_XML_ONLY`
- **Target group:** `cv2-com-frequent-habits`, `mode: reinstall` (the log is emitted at install time).
- **Known tooling gap (outer ring owns):** install-time logs do not currently reach the captured `hilog.txt`; the
  outer loop is adding that capture so this marker can be asserted by the smoke gate.

Smoke-spec fragment → `iconfb-smoke-fragment.json` (this dir):
```json
{"fixes":[{"id":"ICONFB","key":"cv2-com-frequent-habits",
           "markers":["ICONLESS_APK_TEMPLATE_PLACEHOLDER: apk=.* class=DECLARED_XML_ONLY"]}]}
```

## 4. Handoff / next steps
- **No apk_installer patch to land.** U8's installer (`7048c7c50a82`) already has B7 + the
  `ICONLESS_APK_TEMPLATE_PLACEHOLDER` log; the smoke gate asserts that existing line (fragment in §3).
- **sceneboard / ACE-theme lane:** the `$float:125835722` + `app_theme_pattern` /
  `app_theme_drag_distancethreshold` miss is a launcher ArkUI theme-resources gap; not an apk_installer issue.
- **Outer ring (tooling):** make install-time installer logs reach the captured `hilog.txt` so the
  `ICONLESS_APK_TEMPLATE_PLACEHOLDER` marker can be asserted by activation-smoke.
- **On-board confirm of "no desktop icon"** (deferred to a window): after a frequent-habits reinstall under U8,
  dumpLayout the desktop and check for a `com.frequent.habits` icon node — expect a generic placeholder (B7 present);
  the earlier "no icon node" observation needs re-confirming against the B7-bearing U8 build.

## 5. Status
- Earlier `0x07` shared-library root: **retracted** (aapt2 + hilog ground truth).
- `$float:125835722`: **sceneboard/ACE `app_theme_pattern` theme-float gap** (launcher PID 2010), not the icon,
  not apk_installer.
- Icon fallback (Fix A): **already in source and already deployed** — U8's `libapk_installer.so` (`7048c7c50a82`)
  has B7 (`DECLARED_XML_ONLY → template placeholder`) and emits the `ICONLESS_APK_TEMPLATE_PLACEHOLDER` activation
  log. **No patch needed** (the earlier marker patch was withdrawn); the smoke gate greps that existing log.
- Offline only; no board touched.
