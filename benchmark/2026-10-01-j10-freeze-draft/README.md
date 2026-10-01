# J10d/e/f freeze-registration DRAFT (not registered)

Draft freeze entries for the three signed J-layer app-lighting fixes, for the outer loop to review and
copy into `knowledge/frozen/frozen.json` (assigning real `FZ-` ids). **This benchmark does NOT modify
`frozen.json`.** `frozen-entries-draft.json` holds the entries; `sources/` has a copy of each
single-purpose source file for reference.

## The three units (each ≥2 apps past the wall, ≥1 lit at t20 — the tiered-freeze bar)
| draft id | API frozen | source (feat/bms-walls) | verified (lit t20) |
|---|---|---|---|
| FZ-J10d-DRAFT | activity themed by its manifest `*.NoActionBar` theme, not the app parent theme | `J10dTheme.java` blob `f7429baf` | knot, dicewarepasswordgenerator (outer read: 10/12 cluster lit) |
| FZ-J10e-DRAFT | route-A WebView ViewDelegate forwards to `PrivateAccess.super_*` + `getCookieManager()` concrete | `J10eWebView.java` blob `996437513b` | beecount, trickytripper |
| FZ-J10f-DRAFT | `WebViewProvider.getSettings()` returns a concrete WebSettings | `J10fWebSettings.java` blob `177a8938` | caniwebview, jslab |

Each entry pins its source by **git blob id on `feat/bms-walls`** (so `check_frozen.py --git` validates it),
carries the root-cause→fix `mechanism`, the `source_record`, the marker, and the window evidence
(facts line + t20 screenshot path) per verified app.

## Caveat flagged for the outer loop (why "draft")
`J10eWebView.java` at the current HEAD (`8ff080357a`) **also carries the J10f `getSettings` routing and
the J10g `getServiceWorkerController`/`sPackageInfo` logic** — the WebView work was layered into one file
as it evolved. A strict single-concern freeze should either:
1. register the whole WebView-provider-enrichment unit as one entry **after J10g is signed** (J10g is not
   in this draft — the outer loop asked for d/e/f only), or
2. split `J10eWebView.java` into `J10eViewDelegate.java` + `J10eCookieManager.java` before freezing FZ-J10e.

Until then, FZ-J10e-DRAFT pins the whole file blob and documents that its *frozen behaviour* is the
ViewDelegate-forwarding + CookieManager parts only.

## Not done here (by design)
No `frozen.json` edit, no FZ-id assignment, no source split (would touch the live `feat/bms-walls` files).
Those are the outer loop's calls on review.
