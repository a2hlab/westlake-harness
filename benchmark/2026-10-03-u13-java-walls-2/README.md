# U13 Java walls 2: privacybrowser throws inside its own androidx.webkit (our gap is the missing support-library glue, 1 key); fd-api gets a ≤ 10 min disabled-by-default theme probe

#90, offline. Nothing was deployed to a board. The input is two Java walls from the candidate cluster table
(`2026-10-02-candidate-first-fatal-clusters`, window 5).

## 1. cv2-com-stoutner-privacybrowser-standard: `UnsupportedOperationException: This method is not supported by the current version of the framework and the current WebView APK`

### Which code throws it (`first_frame.py` → `first-frame.txt`)

The throw is **not in our jars**. The first frames are `hi0.a`, `bi0.c` and `MainWebViewActivity.z`.
- `hi0`, `bi0` and `fi0` exist only in the APK's own dex: R8-obfuscated androidx.webkit, bundled with the app.
- The message string exists only there too.
- None of them is in the jars the board runs: runtime `5ae3dd29`, stubs `2f365a75`, framework adapter `2257b835`,
  `framework.jar`. Nor are they in the U13 runtime `0482c9b1`.
- The message is androidx.webkit's `WebViewFeatureInternal.getUnsupportedOperationException()`.

### Why it is thrown on our stack (dexdump of the APK)

1. **The app checks first.** `MainWebViewActivity.z` calls `WebViewFeature.isFeatureSupported("ALGORITHMIC_DARKENING")`
   (`bh0.d`). It gets **true**, because that feature (`fi0`) accepts the framework: `fi0.a()` is `SDK_INT >= 33`.
2. **The setter checks something else.** The app then calls `WebSettingsCompat.setAlgorithmicDarkeningAllowed`
   (`bi0.c`). That setter checks **only** `fi0.b()`, "supported by the WebView APK". On SDK ≥ 29 that is just
   "`ALGORITHMIC_DARKENING` is in the WebView's support-library feature list".
3. **Our provider has no support-library glue, so the list is empty.**
   - androidx gets the list from `Class.forName("org.chromium.support_lib_glue.SupportLibReflectionUtil", false,
     WebView.getWebViewClassLoader()).createWebViewProviderFactory()`.
   - Our WebView provider is J10e's `Proxy` (`[J10e-WEBVIEW] enriched WebViewFactoryProvider seeded`).
   - It does not answer `getWebViewClassLoader`, and no jar has the glue class, so androidx falls back to an empty
     feature list.
   - → `UnsupportedOperationException`, out of `onCreate`'s first layout.

On a real device a Chromium WebView APK provides the glue, so both checks agree.

### Should the whole androidx.webkit boundary be filled in? No. (`webkit_scan.py` → `webkit-scan.csv`)

- 19 of the 166 keys bundle androidx.webkit.
- Exactly **1** combines an `ALGORITHMIC_DARKENING` feature check with a call to the throwing setter:
  privacybrowser, 4 checks and 13 setter calls.
- For every other feature the empty list makes `isFeatureSupported` false and the app skips the call. Today's
  behaviour for the other 18 is "feature absent", which is what they handle.
- A full boundary (statics, proxy controller, service workers, safe browsing…) would claim features our stub WebView
  cannot honour, and would turn 18 working keys into new surface.

### Minimal fix, built but not merged into any candidate

**New files, two parts.**

1. `org.chromium.support_lib_glue.SupportLibReflectionUtil`:
   - `createWebViewProviderFactory()` returns an InvocationHandler that claims exactly `{"ALGORITHMIC_DARKENING"}`.
   - `getWebkitToCompatConverter().convertSettings(WebSettings)` returns a handler whose
     `setAlgorithmicDarkeningAllowed` / `isAlgorithmicDarkeningAllowed` forward to the framework's API 33 methods.
     The value is remembered per WebSettings if the provider's WebSettings lacks them.
   - Everything else returns defaults, and androidx never calls it because nothing else is claimed.
   - The boundary method names are verified against the app's dex: `getSupportedFeatures`,
     `getWebkitToCompatConverter`, `setAlgorithmicDarkeningAllowed`, `isAlgorithmicDarkeningAllowed`.
2. `adapter.activity.WebkitSupportGlue`:
   - Re-wraps `WebViewFactory.sProviderInstance` so that `getWebViewClassLoader()` returns the runtime class loader,
     which holds the glue.
   - Every other call forwards to J10e's handler.
   - Needle: right after `J10gWebExtras.install()` in `J10eWebView.install`.

**Artifact:** `oh-adapter-runtime-u13-glue.jar` (`f8788afc…`). It is deterministic, and `deployed_class_diff` vs
`0482c9b1` shows 0 dropped, 0 reshaped, +6 classes, all listed.

**Prediction.**

| key | prediction |
|---|---|
| privacybrowser | **This first fatal disappears (high).** The next wall is unknown: the web area is our stub WebView, so lit-by-screenshot is low-medium. |
| the other 18 androidx.webkit keys | 0 moves. Regression watch: they now see one feature in the list. |
| all other keys | `WebView.getWebViewClassLoader()` returns the runtime loader instead of nothing. No key in the corpus is known to use it. |

## 2. fd-api: `You need to use a Theme.AppCompat theme`. Offline cannot settle it; it gets a probe.

### What is settled statically (`theme_scan.py` → `theme-scan.csv`)

- **The style chain is fine.** The launch theme `0x7f120252` `Theme.BaseActivity.DayNight.NoActionBar` reaches
  AppCompat through `Theme.MaterialComponents.Light.DarkActionBar`. Its default bag is empty (parent only), but 17 lit
  keys share that shape, so it is not the cause.
- **What is unique to fd-api:**
  - its application theme is `@android:style/Theme.Material.Light` (`0x01030237`, a framework theme, not AppCompat);
  - it launches through an activity-alias.
- Lit alias apps (fd-calendar, fd-notes, fd-gallery, fd-filemanager) all have app-local, AppCompat-based application
  themes. A route that hands the Activity its *application* theme instead of the alias target's would be invisible for
  them and fatal for fd-api.
- The logs only prove the *ActivityInfo* was corrected (`[B8-ALIASTHEME] 0x1030237 -> 0x7f120252`). They do not show
  what the Activity instance holds when AppCompat checks.

### The probe (`probe-plan.md`)

- **Artifact:** `oh-adapter-runtime-u13-probe.jar` (`6957f3f9…`) = `0482c9b1` + `adapter.activity.ThemeProbe` + one
  needle after `ProviderAuthorityRefs.resolve`.
- **Disabled by default:** armed only when OH parameter `debug.westlake.theme_probe` lists the package. This runtime's
  `SystemProperties.get` is OH `GetParameter`.
- **What it logs:** in `onActivityPreCreated` (just before `onCreate` → `setContentView`):
  - the Activity's `getThemeResId()`, its `mActivityInfo` theme and the application theme;
  - how its theme resolves `app:windowActionBar` (the attribute AppCompat checks) and `android:windowActionBar`, with
    the source style;
  - `obtainStyledAttributes(...).hasValue`, the API 29 attribute-resolution stack, the base-context chain, `uiMode`
    and the AssetManager's APK paths.
- It is read-only.
- **Board plan:** fd-api plus fd-calendar as control (same alias pattern, lit), ≈ 8 min inside the U13 window.
  `param set` arms it, the two single-key runs follow, then it is disarmed. If the `armed` line is missing, abort.
  The plan includes a result table that maps each outcome to its fix layer: JAR alias-theme path, native resources,
  or AppCompat context.
- **Prediction:** 0 moves. Disarmed it is behaviour-identical to `0482c9b1`; armed it only prints.

## Artifacts (persisted at `$WORKSPACES/westlake-inputs/generations/u13-walls2-v1/`, `SHA256SUMS`)

| jar | contents | sha256 |
|---|---|---|
| `oh-adapter-runtime-u13-probe.jar` | 0482c9b1 + ThemeProbe | `6957f3f977b178cb…` |
| `oh-adapter-runtime-u13-glue.jar` | 0482c9b1 + webkit glue | `f8788afcdff3f55b…` |
| `oh-adapter-runtime-u13-both.jar` | both | `6790d5001d66bf76…` |

All three are runtime-PathClassLoader jars: a single-file replacement with no boot-image rebake.
`build_walls2.py` builds each twice, byte-identical, using the pinned toolchain of `2026-10-02-u12-jar-plan`.

## What was wrong in the earlier reading

- **privacybrowser.** U12's table filed it as "no WebView support-library boundary, JAR, large". It is one feature
  whose two androidx checks disagree on our stack, and one key needs it. The fix is a single-feature glue, not the
  boundary.
- **fd-api.** "Alias theme re-resolved and still rejected" read the ActivityInfo log as the Activity's theme. Those are
  different objects. The empty-bag hypothesis is refuted by 17 lit keys.

## Rules this round sets

- **Name the jar or class that owns the first frame before choosing a fix layer.** Check our jars and the APK's dex
  (`first_frame.py`). An R8-obfuscated first frame (`hi0.a`) usually belongs to the app's bundled library, and the
  wall is then what that library *asks of* us.
- **For androidx feature walls, check both sides of the gate.** `isFeatureSupported` can pass on the framework side
  while the setter requires the WebView side. Count which keys hit that exact mismatch before building any boundary.

## Files

- Scans:
  - `first_frame.py` → `first-frame.txt`;
  - `webkit_scan.py` → `webkit-scan.csv`, `webkit-scan.txt`;
  - `theme_scan.py` → `theme-scan.csv`, `theme-scan.txt`.
- `src/`: ThemeProbe, WebkitSupportGlue, SupportLibReflectionUtil.
- Build and gates: `build_walls2.py`; `gates/class-diff-{probe,glue,both}.txt`.
- `probe-plan.md`, `results.json`.
