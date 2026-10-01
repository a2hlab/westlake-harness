# J10e — enrich the route-A WebView provider (forwarding ViewDelegate + concrete CookieManager) = U9's single JAR

**Rule this lays down:** a route-A "type-zero" interface stub is not enough for framework objects whose
contract is *write-back* or whose return type is an *abstract class*. Two concrete failures the J8 stub
left standing, both proven from the U8 `run_index` cause field by the outer loop:

| wall | keys | why the J8 zero stub fails |
|---|---|---|
| ViewGroup NPE | caniwebview, jslab, beecount, trickytripper | `WebView.java:2658-2659` `setLayoutParams` only calls `mProvider.getViewDelegate().setLayoutParams`; the real provider calls back `WebView.PrivateAccess.super_setLayoutParams` (`WebView.java:2465-2466`) to store it. ZeroHandler no-ops void → `WebView.mLayoutParams` null → `ConstraintLayout.onViewAdded`/`FrameLayout.measureChildWithMargins` NPE on null LayoutParams. |
| CookieManager NPE | degeder-yam, vaults-randomlydie, paultirk-yatoo | `WebViewFactoryProvider.getCookieManager()` (`WebViewFactoryProvider.java:127`) returns the **abstract class** `CookieManager`; ZeroHandler returns null for non-interface → NPE on use. |

## Fix

Re-seed `WebViewFactory.sProviderInstance` with an enriched `WebViewFactoryProvider` proxy
(`J10eWebView.install()`, injected right after the J8 `WebViewProviderFix.install()` call in
`B7BindFixes.apply` — `B7BindFixes.smali:21` then `:23`):

- `createWebView(webView, privateAccess)` → a `WebViewProvider` proxy whose **`getViewDelegate()` forwards**:
  for each `ViewDelegate` method `m(args)`, if `WebView.PrivateAccess` declares a public same-named
  `super_<m>` with identical parameter types, invoke it on the captured `privateAccess`
  (covers `setLayoutParams`→`super_setLayoutParams`, `setFrame`→`super_setFrame`, plus
  onHoverEvent/dispatchKeyEvent/performLongClick/requestFocus/… automatically); otherwise type-zero.
- `getCookieManager()` → a concrete empty `WlCookieManager` (`acceptCookie`=true, `getCookie`=null,
  the rest no-op).

Markers: `[J10e-WEBVIEW] delegate forwards setLayoutParams`, `[J10e-WEBVIEW] CookieManager stub installed`,
and `[J10e-WEBVIEW] enriched WebViewFactoryProvider seeded` (install).

### The @hide trap (why a compile-only stub)

`CookieManager` has 16 abstract methods; **two are `@hide @SystemApi`** — `getCookie(String,boolean)`
(`CookieManager.java:177`) and `hasCookies(boolean)` (`:254`) — and are **absent from the public
`android.jar`**. A subclass built only against `android.jar` would not override them, so the runtime
class stays abstract and `new WlCookieManager()` throws `InstantiationException`. We therefore compile
against a compile-only `android/webkit/CookieManager.java` stub carrying all 16 (incl. the 2 `@hide`),
and d8 **only** the `adapter/activity/J10eWebView*.class` (the stub never enters the dex; the device
supplies the real `CookieManager` as the superclass). `getWebStorage`/`getGeolocationPermissions` stay
null: their public `android.jar` constructors are not accessible to a subclass (the SDK narrows the
AOSP-source `public`), and neither is in the observed NPE corpus.

## Build & provenance

| field | value |
|---|---|
| baseline (J10d) | `57d621837eee4d065a49929f0a7f981e811becc4beba988c18b0ab847e67058c` |
| output (J10e = U9 jar) | `3c1479643420e8c844bf907596f69b1ac8ee42f0a62c2b8695620a7b207f1656` |
| deterministic | yes — built twice identical (`smali assemble -j 1`, zip date 1980-01-01) |
| class delta | **+`adapter/activity/J10eWebView` + 5 inner classes only** |
| source | `feat/bms-walls 142fe0b01` (`J10eWebView.java`) |
| build | `build/build_j10e.py` (Mac local: javac 1.8, d8 via openjdk@17 `--lib android-34/android.jar`, smali/baksmali 2.5.2 on Java 8) |
| staged jar | `$WORKSPACES/westlake-generation-j10e-staging/oh-adapter-runtime-j10e.jar` |

## Offline gate

`python3 test_j10e.py` → **15/15** (self-contained: reads `smali-evidence/`). Proves the install-after-J8
injection, the `super_*` forwarding + markers, and that `WlCookieManager` overrides all 16 abstract
methods (incl. the two `@hide`).

## Window (pending outer-loop schedule)

`j10e-plan.json` — 5ea, `--detach`. Smoke reads `[J10e-WEBVIEW] delegate forwards setLayoutParams`
(caniwebview) + `[J10e-WEBVIEW] CookieManager stub installed` (degeder-yam) + controls;
`offline_precheck.expect` states confirm/refute (retro-17/18); `expect_copies {bridge:2,runtime:2}`;
`before_unlock` rolls back to U8 (`e953c0921536`/`4db882a81732`). 7-key webview shard. `runtime_fp` of
the J10e overlay is **not yet known** (jar `3c147964` differs from every prior) — outer loop computes it.
