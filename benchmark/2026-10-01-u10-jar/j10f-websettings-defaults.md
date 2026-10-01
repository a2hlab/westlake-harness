# J10f WebSettings defect fix — object/String/enum getters return real AOSP/Chromium defaults (U10)

**Defect:** fd-tutanota (the J8 webview-provider app) died in U9 with `getUserAgentString(...) must not be
null`. `J10fWebSettings.WlWebSettings` was generated with type-zero getters, so every object/String/enum
getter returned `null`; WebView apps call `getSettings().getUserAgentString()` (and font/encoding getters)
and do not null-check.

**Fix (U10):** the 12 null-returning object getters now return the real default (generated from a
`DEFAULTS` map in `gen_websettings.py`, source cited per entry; AOSP =
`frameworks/base/core/java/android/webkit/WebSettings.java` in `westlake-inputs/aosp-14.0.0_r1-src`).
Setters and primitive getters are unchanged. Exactly these 12 methods changed:

| method | old | new default | source |
|---|---|---|---|
| `getUserAgentString()` | null | `Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/125.0.0.0 Mobile Safari/537.36` | WebSettings.java:1395 `getDefaultUserAgent`→`getStatics().getDefaultUserAgent` (native); stock Android-14 WebView UA, Chromium `content::BuildUserAgentFromProduct` format |
| `getDefaultTextEncodingName()` | null | `UTF-8` | WebSettings.java:1351 "The default is \"UTF-8\"" |
| `getStandardFontFamily()` | null | `sans-serif` | WebSettings.java:777 |
| `getFixedFontFamily()` | null | `monospace` | WebSettings.java:792 |
| `getSansSerifFontFamily()` | null | `sans-serif` | WebSettings.java:807 |
| `getSerifFontFamily()` | null | `serif` | WebSettings.java:819 |
| `getCursiveFontFamily()` | null | `cursive` | Chromium AwSettings/WebSettingsClassic generic family |
| `getFantasyFontFamily()` | null | `fantasy` | Chromium AwSettings/WebSettingsClassic generic family |
| `getDefaultZoom()` | null | `ZoomDensity.MEDIUM` | WebSettings.java:613 "default is ZoomDensity.MEDIUM" |
| `getLayoutAlgorithm()` | null | `LayoutAlgorithm.NARROW_COLUMNS` | WebSettings.java:762 "default is LayoutAlgorithm.NARROW_COLUMNS" |
| `getPluginState()` | null | `PluginState.OFF` | WebSettings.java getPluginState @deprecated (plugins no-op) |
| `getDatabasePath()` | null | `""` | WebSettings.java getDatabasePath @deprecated/obsolete (empty, never null) |

**Scope:** only these getters; `git diff` on `J10fWebSettings.java` = 12 insertions / 12 deletions, nothing
else. Baked into U10 jar `37465d6d…` (verified via `strings` on the dex: the UA / `sans-serif` / `monospace`
literals are present). Beneficiary: **fd-tutanota** (added to the U10 window). Generic: any WebView app that
reads these settings now gets a valid default instead of null.
