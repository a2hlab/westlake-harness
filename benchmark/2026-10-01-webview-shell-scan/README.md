# webview-shell-scan — which corpus-v2 apps are WebView shells (white-window on route-A)

**Why:** J10g got the last 3 webview apps past their launch crashes, but the outer-loop screenshot read
found them **white** — they are **Capacitor/Cordova shells**: the whole UI is HTML rendered by a Chromium
WebView, and route-A has no Chromium renderer. So "wall passed, no fatal" ≠ lit for a shell. This scan
systematically finds every such shell in corpus-v2 and checks that no `lit`/`lit?` U9 prediction is
secretly one (which would be a mislabelled white window).

## Result (numbers first)
- Scanned **100 / 100** corpus-v2 APKs.
- **3 shells, all Capacitor**: `cv2-ca-vaults-randomlydie`, `cv2-com-degeder-yam`, `cv2-com-paultirk-yatoo`
  — exactly the three J10g targets. 0 Cordova-only shells.
- **lit / lit? predictions that are shells: NONE.** Every shell is already predicted `alive-white-window`
  in `predictions-v4.csv`, so the U9 lit set carries no hidden white window.

| key | shell | prediction | evidence |
|---|---|---|---|
| cv2-ca-vaults-randomlydie | capacitor | alive-white-window | `assets/capacitor.config.json` + `assets/public/index.html`; dex `BridgeActivity` |
| cv2-com-degeder-yam | capacitor | alive-white-window | `assets/capacitor.config.json` + `assets/public/index.html`; dex `BridgeActivity` |
| cv2-com-paultirk-yatoo | capacitor | alive-white-window | `assets/capacitor.config.json` + `assets/public/index.html`; dex `BridgeActivity` |

## Signals (per `scan_webview_shells.py`)
- **Capacitor**: `assets/capacitor.config.json` or `assets/public/index.html`; dex string `BridgeActivity`.
- **Cordova**: `assets/www/index.html` or `assets/www/cordova.js` or `assets/cordova.js`; dex `CordovaActivity`.
- Classified `capacitor` > `cordova` > `none`. Every detected shell carries at least one concrete marker
  (not a guess). Full table: `per-key.txt`; machine form: `results.json`.

## Anchors (test_webview_shell_scan.py, 7/7)
- **Positive** (must be shells): randomlydie, degeder-yam, paultirk-yatoo → all `capacitor`.
- **Negative** (must NOT be shells): caniwebview, jslab → both `none` (they embed a WebView *view* but are
  native-UI apps, so J10e/f lit them for real).

## Rule this lays down
A corpus app whose UI is an HTML bundle behind BridgeActivity/CordovaActivity cannot be "lit" by a J-layer
JAR fix on route-A — the fix only removes the launch crash; lighting it needs a WebView renderer. Count
such apps as **alive-white-window**, not lit, and don't schedule more J-layer windows chasing them.
