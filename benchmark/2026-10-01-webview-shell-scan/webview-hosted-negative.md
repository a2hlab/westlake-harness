# WebView-hosted UI detection — negative result (9 anchors, offline)

Dispatch (ACK(90) latest): write the negative conclusion for the webview-hosted UI detection. Anchors: positive webrtc-check, tutanota, 3 Capacitor; negative caniwebview, jslab, beecount, trickytripper.

## Per-anchor signal hits vs. real UI

| Key | asset_html | loadUrl_asset | Real UI | Result | Reason |
|---|---|---|---|---|---|
| **cv2-timur-webrtc-check** | 2 | 1 | WebView-hosted (WebRTC check page) | ✅ hit | `assets/index.html` + `file:///android_asset/index.html` — main interface is a WebView loading the asset HTML |
| **fd-tutanota** | 1 | 0 | WebView-hosted (Tutanota mail client) | ❌ miss | `assets/index.html` exists but `loadUrl` does NOT point to `file:///android_asset/` (Tutanota loads from network or content://) |
| **cv2-ca-vaults-randomlydie** | 1 | 1 | WebView-hosted (Capacitor) | ✅ hit | `assets/index.html` + `file:///android_asset/index.html` — Capacitor shell |
| **cv2-com-degeder-yam** | 1 | 0 | WebView-hosted (Cordova) | ❌ miss | `assets/index.html` exists but `loadUrl` does NOT point to `file:///android_asset/` (Cordova loads `www/index.html` via content:// or relative path) |
| **cv2-com-paultirk-yatoo** | 1 | 1 | WebView-hosted (Capacitor) | ✅ hit | `assets/index.html` + `file:///android_asset/index.html` — Capacitor shell |
| **cv2-com-caniwebview-android** | 1 | 0 | Own View (CanIUse browser) | ✅ not hit | `assets/html/index.html` exists but no `file:///android_asset/` loadUrl — main UI is own View, not WebView |
| **cv2-eu-dfdx-jslab** | 1 | 1 | Own View (JSLab code editor) | ❌ false positive | `assets/index.html` exists AND `file:///android_asset/index.html` loadUrl exists, but main UI is own View (code editor) — the asset HTML is a welcome/help page, not the main interface |
| **cv2-com-knirirr-beecount** | 0 | 0 | Own View (BeeCount counter) | ✅ not hit | No `assets/index.html`, no `file:///android_asset/` loadUrl — pure native UI |
| **cv2-de-koelle-christian-trickytripper** | 0 | 1 | Own View (Tricky Tripper expense tracker) | ❌ false positive | No `assets/index.html` but `file:///android_asset/` loadUrl exists in dex — likely a library reference (e.g. a help/about page), not the main interface |

## Result

**The two signals (assets/.*index\.html + file:///android_asset/.*\.html) do not separate WebView-hosted UI from own-View UI.** Positive anchors: 3/5 hit (webrtc-check, vaults-randomlydie, yatoo); tutanota misses (loadUrl not asset), yam misses (Cordova loadUrl not asset). Negative anchors: 2/4 false positives (jslab, trickytripper). The signals are too broad: they match any app with an asset HTML file and a loadUrl to it, regardless of whether the WebView is the main interface or a container child.

**The discriminator needs a structural signal** (main Activity's setContentView takes a WebView, or the layout root is a WebView), not just asset presence. This requires dex disassembly (baksmali) or AXML parsing, which is beyond the current offline tooling.

## Method

- `unzip -l <apk> | grep -E 'assets/.*index\.html'` — asset HTML presence.
- `unzip -p <apk> 'classes*.dex' | strings -n 8 | grep -E 'file:///android_asset/[^ ]*\.html'` — loadUrl to asset HTML.
- Anchors: positive webrtc-check, tutanota, 3 Capacitor (vaults-randomlydie, yam, yatoo); negative caniwebview, jslab, beecount, trickytripper.
- tutanota APK at `$WORKSPACES/westlake-inputs/apks/fdroid100/de.tutao.tutanota_396709.apk` (not in corpus-v2/app-inputs).

## Conclusion

WebView-hosted UI detection by asset presence + loadUrl asset is **not reliable** — false positives (jslab, trickytripper) and misses (tutanota, yam) show the signals don't capture the structural property (WebView is the main interface). The next step needs a structural discriminator (main Activity's setContentView takes WebView, or layout root is WebView), which requires dex disassembly or AXML parsing.
