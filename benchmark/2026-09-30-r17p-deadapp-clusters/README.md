# r17p dead-app first-fatal-signature clusters (2026-09-30)

Machine-readable clustering of the ~39 apps that were `alive t5=no` in the r17p full-66 sweeps on
5ea and 61b (`benchmark/2026-09-30-r17p-{5ea,61b}-sweep/`). Each app's signature is taken from its
`J_invokeStaticMain_main_threw:` fatal chain (Caused-by root), NOT a whole-file grep — the
`kotlinx.coroutines.CoroutineStart` CNF is our own `primeCoroutineStart` warm-up (non-fatal) and was
excluded to avoid false clusters.

`clusters.json`: sorted by app count. Layer field = ownership guess (native/boot/JAR/app-internal).

**Summary (25 clusters, 39 apps):**
- **native → cx-t0 (~20):** libflutter.so ULE (6), EGL BAD_ALLOC (3), dlopen_ns app native libs
  (nextcloud/unciv-gdx/im-vector-realm/mindustry-arc), WebView missing (tutanota
  `WebViewFactory.getProvider`), font native (uhabits `AssetManager.nativeOpenAssetFd`), GLImpl
  (shatteredpixel), AudioProductStrategy (opencamera), JNA (firefox/fennec), cppcrash (antennapod/fitness).
- **JAR-fixable → r17s:** RestrictionsManager null (fd-meet) → `restrictions` fetcher stub (built,
  r17s `606dd2e3`); Theme.AppCompat ISE (fd-api) + ConstraintLayout InflateException (vlc) →
  theme/resource projection (open).
- **app-internal (parked):** getClass()-on-null DI (breezyweather/wifianalyzer create, catima resume),
  null-array (fd-reader), app NPEs (organicmaps/osmand/mcdonalds).
- **already fixed (sweep predates them):** etar (PowerExemption → r17q), markor (InvalidDisplay → r17r).
- **foreground-gate / no main-throw (check screenshots):** burgerking, feeder, ppsspp.
