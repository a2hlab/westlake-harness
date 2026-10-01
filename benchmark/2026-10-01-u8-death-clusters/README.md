# U8 non-lit death clusters (66 keys, offline)

Dispatch (board ACK(90) 14:38:37): cluster the U8 non-lit keys by innermost Caused-by + first frame (native crashes use the faultlog stack's first non-system frame). Boards untouched. Method: `first_fatal.py` (0944217a4) + `cluster_first_cause.py` (innermost cause, wrapper RuntimeException never a key).

## Total

U8 signed 166 keys: **99 lit, 67 non-lit** (dead 53, alive-white-window 8, alive-launcher-foreground 3, alive-black-window 1, app_failed 3). The 67 non-lit keys are clustered below.

## Clusters (sorted by keys blocked, descending)

| Cluster | Keys | Coverage | Notes |
|---|---|---|---|
| **other** | 37 | not covered by N10b/J10b/N11 | Various distinct first-causes (NullPointerException, UnsatisfiedLinkError, ClassNotFoundException, signal crashes, system-exit). See clusters.json for per-key cause + first frame. |
| **n11-double-load-white-window** | 12 | **N11** (two bridge/runtime copies → unknown sessionId → white window) | fd-AppManager/fd-app/fd-noice/termux/fd-mobile (alive-white-window), fd-shatteredpixeldungeon/fd-uhabits/cv2-org-andresoviedo-dddmodel2 (alive-white-window), cv2-anupam-acrylic (alive-launcher-foreground), x (alive-black-window). Mechanism from double-load analysis: createSession goes to runtime CL bridge, getOhNativeWindow goes to default-namespace bridge → unknown sessionId → empty Surface → white. |
| **j10b-appcompat-actionbar** | 6 | **J10b** (appcompat action-bar ISE) | cv2-com-codedead-advancedpassgen/codedead-deadhash/deva-knot/emmanuelmess-itsdicey/maxistar-textpad (dead), cv2-org-secuso-privacyfriendlymemory/privacyfriendlyyahtzeedicer (alive-launcher-foreground). All `IllegalStateException: This Activity already has an action bar supplied by the window decor` at `AppCompatDelegateImpl.setSupportActionBar`. |
| **getactivityinfo-namenotfound** | 4 | not covered | cv2-com-aptasystems-dicewarepasswordgenerator/tomato timerdroid/woefe-shoppinglist/ruesga-android-wallpapers-photophase. `ApplicationPackageManager.getActivityInfo(:570)` throws `NameNotFoundException` for the app's own Activity. |
| **no-termination** | 3 | not covered | cv2-com-bytehamster-flowitgame (dead, no-observed-termination), fd-fennec_fdroid/firefox (dead, process-disappeared-cause-unknown). No first-fatal found in hilog. |
| **app_failed-input** | 3 | not covered (input gate) | cv2-com-page-bizzle/trianguloy-clipboardeditor/frequent-habits (app_failed). Input resolution failure before install; no hilog. |
| **n10b-flutter-libandroid** | 2 | **N10b** (Flutter private preload libandroid.so) | fd-kitchenowl/localsend (dead). `UnsatisfiedLinkError: Flutter private preload libandroid.so: Error loading shared library` at `Runtime.load0`. |

## Coverage by in-flight fixes

- **N10b** covers: n10b-flutter-libandroid (2 keys). The `n10b-emboss-asset` cluster (Typeface VM / NDK AssetManager / Emboss) is **empty** in U8 — those walls were already passed in U7/U8 or are not present in this cohort.
- **J10b** covers: j10b-appcompat-actionbar (6 keys).
- **N11** covers: n11-double-load-white-window (12 keys) — the double-load root cause (two bridge/runtime copies → unknown sessionId → white window), per double-load analysis in `whitewin-diff/double-load/`.
- **Not covered**: other (37 keys), getactivityinfo-namenotfound (4), no-termination (3), app_failed-input (3).

## Evidence

- Per-key first_fatal results: `/tmp/u8-death-results.json` (copied to `clusters.json` evidence).
- Run dirs: `westlake-harness-t4/benchmark/2026-10-01-u8-sweep/{5ea,61b}-seq-{v1,cv2}/`.
- outer-signoff: `benchmark/2026-10-01-u8-sweep/outer-signoff.json` (master).
- double-load mechanism: `benchmark/2026-10-01-u8-flaky-repeat/whitewin-diff/double-load/REPORT.md`.

## Correction: dicewarepasswordgenerator (getactivityinfo-namenotfound, confirmed)

cc-t3 said dicewarepasswordgenerator is action-bar ISE in U8/J10. Re-checked against the same U8 hilog (`westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5ea-seq-cv2/20261001T122134-78628011/5ea34a4500000000000000000324012c/cv2-com-aptasystems-dicewarepasswordgenerator/hilog.txt`):

- **Fatal exception (main_threw, 12:34:04.731):** `RuntimeException: Unable to start activity ComponentInfo{…MainActivity}: java.lang.IllegalArgumentException: android.content.pm.PackageManager$NameNotFoundException: ComponentInfo{…MainActivity}` (line 48692).
- **Caused-by chain:** `IllegalArgumentException(NameNotFoundException)` at `android.support.v4.app.NavUtils.getParentActivityName(NavUtils.java:215)` → `AppCompatDelegateImplV9.onCreate` → `AppCompatActivity.onCreate`.
- **Action-bar ISE in same hilog:** grep `already has an action bar` → **0 matches**; grep `IllegalStateException` → **0 matches**.
- **Verdict:** NameNotFoundException is the fatal exception; no action-bar ISE exists in this hilog. cc-t3 likely confused with another key or a J10 run. Initial assignment to `getactivityinfo-namenotfound` is correct.

## Subdividing 'other 37'

Groups with ≥2 keys sharing a single framework-fixable root (exception class + first non-system frame package/library):

| Group | Keys | Common frame | Fix note |
|---|---|---|---|
| **UnsatisfiedLinkError@Runtime.loadLibrary0** | 4 (chessclock-android, fd-im-vector-app, burgerking, mindustry) | `at java.lang.Runtime.loadLibrary0(Runtime.java:1082/1093)` | Single fix: make the adapter manifest / namespace export the missing library or SONAME alias (same family as libz.so / libmediandk work) |
| **NPE@CapacitorCordovaCookieManager** | 2 (cv2-ca-vaults-randomlydie, cv2-com-paultirk-yatoo) | `at com.getcapacitor.cordova.CapacitorCordovaCookieManager.<init>` | Single fix: make `android.webkit.CookieManager.getInstance()` non-null in the adapter (webview provider registration) |
| **NPE@ViewGroup.measureChildWithMargins** | 2 (cv2-com-knirirr-beecount, cv2-de-koelle-christian-trickytripper) | `at android.view.ViewGroup.measureChildWithMargins(ViewGroup.java:7001)` | Single fix: ViewGroup$MarginLayoutParams construction path in the adapter |
| **NPE@ViewGroup$LayoutParams.<init>** | 2 (cv2-com-caniwebview-android, cv2-eu-dfdx-jslab) | `at android.view.ViewGroup$LayoutParams.<init>(ViewGroup.java:8238)` | Single fix: same family as above — ViewGroup$LayoutParams construction NPE in the adapter |
| **NPE@app-MainActivity-onCreate** | 2 (fd-tutanota, toutiao) | `at de.tutao.tutanota.MainActivity.onCreate(SourceFile:191)` / `at com.ss.android.article.news.activity.MainActivity.<init>(SourceFile:327715)` | App-specific; not a single framework fix |

## Fixable groups (派修-ready)

### ① UnsatisfiedLinkError@Runtime.loadLibrary0 (4 keys)

Per-key missing library, loader, board presence, minimal fix:

| Key | Missing lib | Loader | Board presence | Minimal fix |
|---|---|---|---|---|
| cv2-com-chessclock-android | `libmediandk.so` | System.loadLibrary (app native lib) | not in /system/android/lib64 or /system/lib64 (5ea checked) | add libmediandk.so to the adapter manifest / route-a (LIBMEDIANDK-PLAN.md; N11 native version) |
| fd-im-vector-app | `libz.so` | DT_NEEDED of app lib (librealm-jni.so) | not in /system/android/lib64 or /system/lib64 (only libzone_util.z.so, libziparchive.so — different libs) | SONAME alias: libz.so → libshared_libz.z.so (OH zlib in /system/lib64/chipset-sdk-sp; LIBZ-PLAN.md) |
| burgerking | `libz.so` | DT_NEEDED of app lib (libmmkv.so) | same as above | same SONAME alias |
| mindustry | `slCreateEngine` symbol (in libOpenSLES.so or libaudioengine.so) | DT_NEEDED / symbol relocation of app lib (libarc.so) | libOpenSLES.so not checked; slCreateEngine is the OpenSL ES engine creation symbol | provide libOpenSLES.so (or a shim exporting slCreateEngine) in the adapter manifest / route-a; if it exists, add it to the app namespace search path |

### ② ViewGroup NPE ×4 — same root

Both sub-groups share the same root: the adapter's layout-inflation / layout-params path produces **null LayoutParams** (or null MarginLayoutParams) for views that should have them. The NPE is a symptom of null LayoutParams being passed into `ViewGroup$LayoutParams.<init>` or `measureChildWithMargins`.

| Sub-group | Keys | Common frame | Cause chain | Framework fix point |
|---|---|---|---|---|
| measureChildWithMargins | cv2-com-knirirr-beecount, cv2-de-koelle-christian-trickytripper | `at android.view.ViewGroup.measureChildWithMargins(ViewGroup.java:7001)` | NPE: read `MarginLayoutParams.leftMargin` on null in `measureChildWithMargins` → `FrameLayout.onMeasure` → `View.measure` → … (repeated measure cycles) | `ViewGroup.measureChildWithMargins` should not NPE when `MarginLayoutParams` is null; skip the margin or return zero margins |
| LayoutParams.<init> | cv2-com-caniwebview-android, cv2-eu-dfdx-jslab | `at android.view.ViewGroup$LayoutParams.<init>(ViewGroup.java:8238)` | NPE: read `LayoutParams.width` on null in `LayoutParams.<init>(LayoutParams)` → `MarginLayoutParams.<init>` → `ConstraintLayout$LayoutParams.<init>` → `ConstraintLayout.generateLayoutParams` → `ConstraintLayout.getViewWidget` → `ConstraintLayout.onViewAdded` → `ViewGroup.dispatchViewAdded` → `ViewGroup.addViewInner` → … (inflation of `layout/fragment_webview.xml` line #56) | `ViewGroup$LayoutParams.<init>` should not NPE on null source; default to MATCH_PARENT/WRAP_CONTENT |

**Single framework fix** (one line in the layout-params construction path): when `ViewGroup.getLayoutParams()` or `ViewGroup.generateLayoutParams()` returns null for a view added without explicit params, default to `MATCH_PARENT` (width) / `WRAP_CONTENT` (height) instead of passing null into the LayoutParams copy constructor or measure path. This addresses both sub-groups with one change.

## Root cause of ViewGroup NPE ×4 (outer-determined, confirmed)

Outer loop's finding (ACK(90) 15:05:04 retro): the **WebView stub's `ViewDelegate.setLayoutParams` is a zero-value no-op** — a real provider would call `PrivateAccess.super_setLayoutParams`, so the WebView's LayoutParams are **always null** (AOSP 14 `WebView.java:2658-2660`). When the WebView is added to a ConstraintLayout, `ConstraintLayout.generateLayoutParams` calls `ConstraintLayout$LayoutParams.<init>(ViewGroup$LayoutParams)` which dereferences `source.width` — NPE. When the WebView is measured inside a FrameLayout, `ViewGroup.measureChildWithMargins` reads `MarginLayoutParams.leftMargin` — same null, same NPE.

### Per-key stack excerpts

**caniwebview** (`westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-cv2/20261001T122904-44eb39c6/61b0657200000000000000000324012c/cv2-com-caniwebview-android/hilog.txt`):
```
Caused by: java.lang.NullPointerException: Attempt to read from field 'int android.view.ViewGroup$LayoutParams.width' on a null object reference in method 'void android.view.ViewGroup$LayoutParams.<init>(android.view.ViewGroup$LayoutParams)'
    at android.view.ViewGroup$LayoutParams.<init>(ViewGroup.java:8238)
    at android.view.ViewGroup$MarginLayoutParams.<init>(ViewGroup.java:8559)
    at androidx.constraintlayout.widget.ConstraintLayout$LayoutParams.<init>(ConstraintLayout.java:3430)
    at androidx.constraintlayout.widget.ConstraintLayout.generateLayoutParams(ConstraintLayout.java:1950)
    at androidx.constraintlayout.widget.ConstraintLayout.getViewWidget(ConstraintLayout.java:1532)
    at androidx.constraintlayout.widget.ConstraintLayout.onViewAdded(ConstraintLayout.java:1003)
    at android.view.ViewGroup.dispatchViewAdded(ViewGroup.java:5157)
    at android.view.ViewGroup.addViewInner(ViewGroup.java:5329)
    at android.view.ViewGroup.addView(ViewGroup.java:5104)
    at android.view.ViewGroup.addView(ViewGroup.java:5076)
    at android.view.LayoutInflater.rInflate(LayoutInflater.java:1139)
    at android.view.LayoutInflater.inflate(LayoutInflater.java:694)
    at com.caniwebview.android.databinding.FragmentWebviewBinding.inflate(FragmentWebviewBinding.java:60)
    at com.caniwebview.android.ui.webview.WebViewFragment.onCreateView(WebViewFragment.kt:63)
```
Child class: `android.webkit.WebView` (type-zero stub). Call site: `androidx.constraintlayout.widget.ConstraintLayout.generateLayoutParams(ConstraintLayout.java:1950)` → `ConstraintLayout$LayoutParams.<init>(ConstraintLayout.java:3430)`.

**jslab** (`westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-cv2/20261001T122904-44eb39c6/61b0657200000000000000000324012c/cv2-eu-dfdx-jslab/hilog.txt`):
```
Caused by: java.lang.NullPointerException: Attempt to read from field 'int android.view.ViewGroup$LayoutParams.width' on a null object reference in method 'void android.view.ViewGroup$LayoutParams.<init>(android.view.ViewGroup$LayoutParams)'
    at android.view.ViewGroup$LayoutParams.<init>(ViewGroup.java:8238)
    at android.view.ViewGroup$MarginLayoutParams.<init>(ViewGroup.java:8559)
    at androidx.constraintlayout.widget.ConstraintLayout$LayoutParams.<init>(ConstraintLayout.java:3418)
    at androidx.constraintlayout.widget.ConstraintLayout.generateLayoutParams(ConstraintLayout.java:1950)
    at androidx.constraintlayout.widget.ConstraintLayout.getViewWidget(ConstraintLayout.java:1532)
    at androidx.constraintlayout.widget.ConstraintLayout.onViewAdded(ConstraintLayout.java:1003)
    at android.view.ViewGroup.dispatchViewAdded(ViewGroup.java:5157)
    at android.view.ViewGroup.addViewInner(ViewGroup.java:5329)
    at android.view.LayoutInflater.inflate(LayoutInflater.java:694)
    at eu.dfdx.jslab.databinding.FragmentMainBinding.inflate(FragmentMainBinding.java:49)
    at eu.dfdx.jslab.ui.main.PlaceholderFragment.onCreateView(PlaceholderFragment.java:57)
```
Child class: `android.webkit.WebView` (type-zero stub). Call site: `androidx.constraintlayout.widget.ConstraintLayout.generateLayoutParams(ConstraintLayout.java:1950)` → `ConstraintLayout$LayoutParams.<init>(ConstraintLayout.java:3418)`.

**beecount** (`westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5ea-seq-cv2/20261001T122134-78628011/5ea34a4500000000000000001123012c/cv2-com-knirirr-beecount/hilog.txt`):
```
Caused by: java.lang.NullPointerException: Attempt to read from field 'int android.view.ViewGroup$MarginLayoutParams.leftMargin' on a null object reference in method 'void android.view.ViewGroup.measureChildWithMargins(android.view.View, int, int, int, int)'
    at android.view.ViewGroup.measureChildWithMargins(ViewGroup.java:7001)
    at android.widget.FrameLayout.onMeasure(FrameLayout.java:194)
    at android.view.View.measure(View.java:27122)
    at android.view.ViewGroup.measureChildWithMargins(ViewGroup.java:7008)
    at android.widget.FrameLayout.onMeasure(FrameLayout.java:194)
    at android.view.ViewGroup.measureChildWithMargins(ViewGroup.java:7008)
    at android.widget.LinearLayout.measureChildBeforeLayout(LinearLayout.java:1608)
    at android.widget.LinearLayout.measureVertical(LinearLayout.java:878)
    at android.widget.LinearLayout.onMeasure(LinearLayout.java:721)
    at android.view.ViewGroup.measureChildWithMargins(ViewGroup.java:7008)
    at android.widget.FrameLayout.onMeasure(FrameLayout.java:194)
```
Child class: `android.webkit.WebView` (type-zero stub) — the WebView is added to a FrameLayout without explicit layout params (or its container is measured with null MarginLayoutParams because the WebView's LayoutParams are null). Call site: `android.view.ViewGroup.measureChildWithMargins(ViewGroup.java:7001)`.

**trickytripper** (`westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-cv2/20261001T122027-e3c3b085/5cd1e3dd00000000000000000923012c/cv2-de-koelle-christian-trickytripper/hilog.txt`):
```
Caused by: java.lang.NullPointerException: Attempt to read from field 'int android.view.ViewGroup$MarginLayoutParams.leftMargin' on a null object reference in method 'void android.view.ViewGroup.measureChildWithMargins(android.view.View, int, int, int, int)'
    at android.view.ViewGroup.measureChildWithMargins(ViewGroup.java:7001)
    at android.widget.FrameLayout.onMeasure(FrameLayout.java:194)
    at android.view.View.measure(View.java:27122)
    at android.view.ViewGroup.measureChildWithMargins(ViewGroup.java:7008)
    at android.widget.FrameLayout.onMeasure(FrameLayout.java:194)
    at android.view.ViewGroup.measureChildWithMargins(ViewGroup.java:7008)
```
Child class: `android.webkit.WebView` (type-zero stub). Call site: `android.view.ViewGroup.measureChildWithMargins(ViewGroup.java:7001)`.

### AOSP 14 ViewGroup.java line alignment

| Line | Content |
|---|---|
| `ViewGroup.java:7001` | `final int childWidthMeasureSpec = getChildMeasureSpec(parentWidthMeasureSpec, …)` — reads `lp.leftMargin` from a null `MarginLayoutParams` |
| `ViewGroup.java:8238` | `this.width = source.width;` — copy constructor `ViewGroup$LayoutParams.<init>(ViewGroup$LayoutParams source)` reads `source.width` from a null `source` |

### Minimal patch draft (for cc-t3)

The zero-value `ViewDelegate.setLayoutParams` in the WebView stub must call through to `PrivateAccess.super_setLayoutParams` instead of being a no-op. One line:

```java
// In the WebView stub's ViewDelegate.setLayoutParams (adapter source, ~02cbace-WebViewUpdateServiceAdapter.java):
// change from:
//   public void setLayoutParams(ViewGroup.LayoutParams params) {}
// to:
//   public void setLayoutParams(ViewGroup.LayoutParams params) { PrivateAccess.super_setLayoutParams(params); }
```

**Activation log line (one line, grep-able):**
```
[WEBVIEW-STUB] setLayoutParams forwarded to PrivateAccess.super_setLayoutParams — WebView LayoutParams non-null
```
When this line appears in a lit round, the WebView's LayoutParams are non-null and the NPE is gone.

## other subdivision v2 (run_index cause field, e953c0921536)

Excluded already-assigned (WebView-stub 4, missing-lib 4, appcompat 7, getactivityinfo 4). Remaining groups with ≥2 keys sharing a framework-fixable root:

| Group | Keys | Cause | Fix note |
|---|---|---|---|
| **ClassNotFoundException@kotlinx.coroutines.CoroutineStart** | 14 (cv2-com-nononsenseapps-notepad, fd-fluffychat, fd-kitchenowl, fd-libre, fd-meet, fd-musicplayer, fd-saber, cv2-com-ath0-rpn, cv2-com-bytehamster-flowitgame, cv2-com-kaajjo-libresudoku, cv2-org-linaro-glmark2, localsend, ppsspp, subwaysurfers) | `java.lang.ClassNotFoundException: kotlinx.coroutines.CoroutineStart` | Single fix: kotlinx-coroutines-core jar in boot class path or app namespace; same family as J7b coroutine fixes |
| **NullPointerException@various** | 8 (cv2-com-paultirk-yatoo, cv2-ca-vaults-randomlydie, cv2-com-degeder-yam, fd-breezyweather, fd-client, cv2-com-stoutner-privacybrowser-standard, cv2-timur-webrtc-check, fd-tutanota) | Various NPEs (CookieManager.setAcceptThirdPartyCookies, CookieManager.getInstance, ViewGroup, etc.) | Multiple distinct NPEs; yatoo/vaults-randomlydie/degeder-yam are CookieManager-related (WebView provider); others are app-specific |
| **reflect.InvocationTargetException@reflection** | 5 (cv2-com-trianguloy-clipboardeditor, cv2-com-nbossard-packlist, fd-immich, fd-plus, toutiao) | `java.lang.reflect.InvocationTargetException` (reflection call failed, cause chain varies) | Wrapper exception; check inner cause per key. Some are Method.invoke on missing classes (same family as ClassNotFoundException) |
| **RuntimeException@provider-init** | 4 (cv2-com-lcdcode-moodcairns, cv2-dev-obfusk-jiten-webview, mcdonalds, vlc) | `java.lang.RuntimeException: Unable to get provider androidx.startup.InitializationProvider / Unable to start activity …` | androidx.startup provider initialization failure; same family as mcdonalds earlier (fd 31 fd-san). Check inner cause per key |
| **UnsatisfiedLinkError@mozglue** | 2 (fd-fennec_fdroid, firefox) | `java.lang.UnsatisfiedLinkError` (mozglue: `__gnu_strerror_r` or similar) | Same as earlier firefox/fennec libmozglue `__gnu_strerror_r`; already in N10b shim candidates |
| **IllegalStateException@misc** | 2 (fd-api, cv2-com-github-dfa-diaspora-android) | `java.lang.IllegalStateException` (various) | App-specific; not a single framework fix |

## other subdivision v3 (run_index rebuilt index, e953c0921536)

Outer confirmed the v2 `ClassNotFoundException@kotlinx.coroutines.CoroutineStart` ×14 group was an **index artifact** (cause field took the first caught probe exception, not the fatal one). Rebuilt index used. Excluded already-assigned (WebView-stub 4, missing-lib 4, appcompat 7, getactivityinfo 4, WebView-cookie 3). CNF group removed. cause=None keys grouped by first_fatal (native crash / JNI abort listed separately).

### Groups with ≥2 keys sharing a framework-fixable root

| Group | Keys | Cause | Fix note |
|---|---|---|---|
| **NullPointerException@various** | 5 (fd-breezyweather, fd-client, cv2-com-stoutner-privacybrowser-standard, cv2-timur-webrtc-check, fd-tutanota) | Various NPEs (CookieManager-related or app-specific) | Multiple distinct NPEs; WebView-cookie 3 already assigned to WebView stub cluster; not a single framework fix |
| **RuntimeException@provider-init** | 4 (cv2-com-lcdcode-moodcairns, cv2-dev-obfusk-jiten-webview, mcdonalds, vlc) | `java.lang.RuntimeException: Unable to get provider androidx.startup.InitializationProvider / Unable to start activity …` | androidx.startup provider initialization failure; same family as mcdonalds earlier (fd 31 fd-san). Check inner cause per key |
| **IllegalStateException@misc** | 2 (fd-api, cv2-com-github-dfa-diaspora-android) | `java.lang.IllegalStateException` (various) | App-specific; not a single framework fix |

### cause=None keys (grouped by first_fatal)

| Group | Keys | Cause | Fix note |
|---|---|---|---|
| **jni_abort** | 6 (fd-fluffychat, fd-immich, fd-libre, fd-saber, cv2-org-linaro-glmark2, subwaysurfers) | `F C00f00/appspawn-x: [java_vm_ext.cc:591] JNI DETECTED ERROR IN APPLICATION` (JNI abort) | JNI abort; check inner cause per key (missing native lib or invalid JNI call) |
| **fdsan_signal** | 2 (fd-kitchenowl, localsend) | `I C02d11/DfxFaultLogger: Reason:Signal:DEBUG SIGNAL(FDSAN)` | fdsan signal; same family as mcdonalds fd 31 fd-san |
| **sigsegv_sigabrt** | 2 (cv2-com-ath0-rpn, subwaysurfers) | `I C02d11/DfxFaultLogger: Reason:Signal:SIGSEGV(SIGABRT)(SEGV_MAPERR/SI_TKILL)` | Native crash; check faultlog stack top non-system frame per key |
| **no_first_fatal** | 10 (cv2-com-nbossard-packlist, cv2-com-nononsenseapps-notepad, fd-fennec_fdroid, fd-meet, fd-musicplayer, fd-plus, cv2-com-bytehamster-flowitgame, cv2-com-kaajjo-libresudoku, firefox, ppsspp, toutiao) | cause=None and first_fatal=None (no termination found in hilog) | no-observed-termination; process-disappeared-cause-unknown or no fatal found |

## provider-init ×4 拆分(outer-determined, confirmed)

Outer loop's finding (ACK(90) latest): the four provider-init keys have four distinct innermost causes, not one framework fix.

| Key | Innermost cause | Cluster / fix candidate | Notes |
|---|---|---|---|
| **vlc** | Theme attribute resolution failure (`android.view.InflateException` on a theme attr that the adapter's theme/resources can't resolve) | **J10d** (theme attr resolution) | AppCompat theme attribute lookup fails in the adapter's resource resolution path. |
| **dev-obfusk-jiten-webview** | `ConstraintLayout$LayoutParams.widget` is null (the WebView stub's widget field is null when ConstraintLayout tries to use it as a constraint target) | **J10e** (WebView stub widget field) | Same family as the WebView stub cluster — the stub's widget/LayoutParams/widget-field is null, this time hit via ConstraintLayout's constraint resolution instead of measure/add. |
| **cv2-com-lcdcode-moodcairns** | `javax.crypto.AEADBadTagException` (GCM mac check failed) when the app's keystore master key can't be decrypted | **单列** (keystore master key decryption) | Android Keystore master key unwrap fails in the adapter's keystore/crypto path. Not a framework fix shared with other keys; check the adapter's keystore provider / hardware-backed key store stub. |
| **mcdonalds** | Native library `dlopen_ns` failed (missing shared library or symbol, same family as the UnsatisfiedLinkError cluster) | **missing-lib** (already in UnsatisfiedLinkError cluster) | Same as earlier mcdonalds fd 31 fd-san; the provider init fails because a native lib can't load. Already in the missing-lib cluster's fix path (SONAME alias / provide the lib). |

### Innermost cause per key (from run_index / hilog)

- **vlc**: `RuntimeException: Unable to start activity …: android.view.InflateException: Binary XML file line #… in com.videolan.vlc:layout/…: Failed to resolve attribute at index …` — theme attr resolution failure in the adapter's resource path.
- **dev-obfusk-jiten-webview**: `RuntimeException: Unable to start activity …: java.lang.NullPointerException: Attempt to read from field 'int androidx.constraintlayout.widget.ConstraintLayout$LayoutParams.widget' on a null object reference` — ConstraintLayout's widget field is null (WebView stub).
- **cv2-com-lcdcode-moodcairns**: `RuntimeException: Unable to get provider androidx.startup.InitializationProvider: javax.crypto.AEADBadTagException: mac check in GCM failed` — keystore master key unwrap fails.
- **mcdonalds**: `RuntimeException: Unable to get provider androidx.startup.InitializationProvider: java.lang.UnsatisfiedLinkError: dlopen_ns failed for …: Error loading shared library libz.so: (needed by …)` — native lib missing.

### Minimal fix draft

- **vlc** (J10d): make the adapter's theme/resource resolution return the attribute (or a safe default) instead of throwing InflateException on missing theme attrs.
- **jiten-webview** (J10e): make the WebView stub's `widget` field non-null (or ConstraintLayout skip constraint resolution when widget is null).
- **moodcairns** (keystore): make the adapter's keystore provider return a valid master key (or a deterministic test key) for AEAD unwrap.
- **mcdonalds** (missing-lib): same SONAME alias / provide the lib as the UnsatisfiedLinkError cluster.

**Activation log line (one line, grep-able):**
```
[PROVIDER-INIT] androidx.startup InitializationProvider created OK — keystore master key unwrap succeeded / theme attr resolved / WebView widget non-null / native lib loaded
```
When this line appears in a lit round, the provider-init path succeeded for that key.
