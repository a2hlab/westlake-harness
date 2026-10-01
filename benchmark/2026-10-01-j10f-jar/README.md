# J10f — concrete WebSettings for WebViewProvider.getSettings() (U9's single JAR)

**Rule (continued from J10e):** every `WebViewProvider` getter whose return type is an *abstract class*
must hand back a concrete instance, not a type-zero null. J10e cleared `setLayoutParams`/`getCookieManager`;
the webview cluster's wall then moved to **`getSettings()`**.

## What J10e left (proven on-board, J10e window 5ea)
beecount + trickytripper lit; the other 5 advanced to a new wall — `WebViewProvider.getSettings()` returns
null (abstract-class return, J8 ZeroHandler) → route-A WebView apps call `getSettings().setJavaScriptEnabled(..)`
at launch:
- caniwebview: `getSettings(...) must not be null`
- jslab, degeder-yam, vaults-randomlydie, paultirk-yatoo: `setJavaScriptEnabled(boolean)' on a null object reference`

## Fix
`J10eWebView.ProviderInstance.getSettings()` → `J10fWebSettings.get()` = a cached concrete
`WlWebSettings`. `WlWebSettings extends android.webkit.WebSettings` and overrides **all 104 abstract
methods** (getters → type-zero defaults, setters → no-op), **generated from AOSP 14 r1 `WebSettings.java`**
by `build/gen_websettings.py` (hand-writing 104 methods — incl. the `@hide`/`@SystemApi`/
`@UnsupportedAppUsage` ones — is error-prone and must match the runtime abstract surface exactly or
`new WlWebSettings()` throws `InstantiationException`). Compiled against a compile-only
`android.webkit.WebSettings` stub (same 104, + the 5 nested enums); d8 only the `adapter/activity`
classes. Marker `[J10f-WEBVIEW] settings stub installed`.

## Build & provenance
| field | value |
|---|---|
| baseline (J10d) | `57d621837eee4d065a49929f0a7f981e811becc4beba988c18b0ab847e67058c` |
| output (J10f = U9 jar) | `a0f8ba4531b3aefe0d61aeb880bb415a57f35f334327388b61768a0ae22f2af8` |
| deterministic | yes — built twice identical |
| class delta | +`J10fWebSettings` (+`$WlWebSettings`) and J10eWebView* (re-applied from the J10d base; J10eWebView now wires getSettings) |
| source | `feat/bms-walls` (`J10fWebSettings.java` generated; `J10eWebView.java` getSettings edit) |
| build | `build/build_j10f.py` + `build/gen_websettings.py` (Mac local: javac 1.8, d8 via openjdk@17, smali/baksmali 2.5.2 Java 8) |
| staged jar | `$WORKSPACES/westlake-generation-j10f-staging/oh-adapter-runtime-j10f.jar` |

## Offline gate
`python3 test_j10f.py` → **5/5** (getSettings→J10fWebSettings wiring, marker, WlWebSettings extends
WebSettings with 104 overrides, install injection carried from J10e).

## Window (pending)
`j10f-plan.json` — 5ea, `--detach`. Smoke `[J10f-WEBVIEW] settings stub installed` (caniwebview) +
`[J10e-WEBVIEW] CookieManager stub installed` (degeder-yam, regression) + controls; `offline_precheck.expect`
confirm/refute; 7-key webview shard (5 getSettings-wall + 2 regression). `runtime_fp` of the J10f overlay
not yet known (jar `a0f8ba45` differs) — outer loop computes it.
