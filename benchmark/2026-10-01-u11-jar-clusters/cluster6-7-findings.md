# Clusters 6 & 7 — investigation before implementing

(Cluster 4 keystore reassigned to cc-wiki; cluster 5 shipped in U11e with dedup.)

## Cluster 6 — pkg-self `getInstallSourceInfo` (yahtzeedicer): **wrong jar for the U11 JAR**

- **Root cause confirmed:** `adapter.packagemanager.PackageManagerAdapter.getInstallSourceInfo(String,int)`
  (`framework/package-manager/java/PackageManagerAdapter.java:1410`) only `logStub(...)` and returns **null**.
  `ApplicationPackageManager.getInstallSourceInfo(pkg)` throws `NameNotFoundException(pkg)` when the IPC returns
  null — exactly yahtzeedicer's crash (`org.secuso.privacyfriendlyyahtzeedicer` on its own package). (Double-load
  of two `PackageManagerAdapter` instances is present but separate; this wall is the null return.)
- **Fix:** `getInstallSourceInfo` returns a synthesized **all-null** `InstallSourceInfo` (unknown initiating /
  originating / installing package — honest "sideloaded, source unknown", fabricates nothing). The AOSP ctor is
  `@hide` so construct by reflection: `InstallSourceInfo(String,SigningInfo,String,String)` with `(null,null,null,null)`.
- **Routing problem (key finding):** `PackageManagerAdapter` lives in **`oh-adapter-framework.jar`**, NOT
  `oh-adapter-runtime.jar` (the "U11 JAR" that `build_u11*.py` produces — verified: 0 `packagemanager` classes in
  U10/U11 runtime jar; the class is in `oh-adapter-framework.jar`). So cluster 6 **cannot** be added via the U11
  JAR build. Two options — **needs an outer decision**:
  1. Fix in `oh-adapter-framework.jar` (1-line source change at PackageManagerAdapter:1410 → return synthesized
     InstallSourceInfo; new freeze-unit file + that jar's build pipeline).
  2. Proxy-hook from `oh-adapter-runtime`: wrap the installed `IPackageManager` (AppSpawnXInit installs
     PackageManagerAdapter as `ActivityThread.sPackageManager`) with a Proxy that intercepts `getInstallSourceInfo`
     → synthesized non-null; everything else delegates. Keeps cluster 6 inside the U11 runtime jar.
  Recommendation: option 2 (proxy-hook) keeps it in the one U11 JAR and needs no second jar build; option 1 is
  cleaner but adds an `oh-adapter-framework` build to the U11 window.

## Cluster 7 — appcompat-theme (fd-api / termux.api): **fix-interaction bug, not a missing fallback**

Root cause is NOT a missing app-theme fallback (that already works). From fd-api's U9 hilog, in order:
- `12587 [WL-THEME-SYNC] parsed appTheme=0x1030237` (the app/alias theme = `@android:Theme.Translucent.NoTitleBar`).
- `12626 [B8-ALIASTHEME] TermuxAPIMainActivity theme re-resolved 0x1030237 -> 0x7f120252` — AliasTargetTheme (J3)
  correctly re-resolves the alias **target** (the real `AppCompatActivity`) to the app's own AppCompat theme
  `0x7f120252`.
- `12635 [J10d-THEME] TermuxAPILauncherActivity theme=0x1030237 (manifest 0x1030237; already set)` — J10dTheme
  (appcompat-actionbar) restores the **alias launcher's** manifest theme back to `0x1030237`.
- `12894 IllegalStateException: You need to use a Theme.AppCompat theme` at `TermuxAPIMainActivity.setContentView`
  → `AppCompatDelegateImpl.createSubDecor`. So the applied theme was the non-AppCompat `0x1030237`, i.e. J3's
  re-resolution to `0x7f120252` was **clobbered**.

**Two single-purpose theme fixes fight on the alias→AppCompatActivity path:** J3 re-resolves the target to an
AppCompat theme; J10d restores the alias's manifest theme; J10d runs last and wins, so the target
`AppCompatActivity` is created with the translucent, non-AppCompat theme. Only visible by reading the ordered
log — statically both files look correct.

**Fix direction (both files non-frozen; ordering/guard, not a new fallback):** make the alias target's
re-resolved AppCompat theme win — either run `AliasTargetTheme.apply` **after** `J10dTheme.restore` in
AppSchedulerBridge, or have `J10dTheme.restore` **skip** an activity whose alias target was re-resolved
(`targetActivity != null` and a target theme already set). Needs the exact call order of the two in
AppSchedulerBridge; a small reorder/guard, no new fallback theme (there is no generic AppCompat theme id to
force — `0x7f120252` is the app's own resource, which J3 already found correctly).

## Status / asks

- **U11e** (clusters 1 phone + 3 ssl-engine + 5 content-provider + dedup) is the current U11 JAR
  (`b093243b…`), shippable; its first board run is also the cluster-5 probe.
- **Cluster 6:** needs the outer's routing decision (oh-adapter-framework build vs runtime proxy-hook) before I
  implement.
- **Cluster 7:** root-caused (J10d clobbers AliasTargetTheme); fix is an ordering/guard between two non-frozen
  files — I can implement once the approach (reorder vs guard) is confirmed.
- Cluster 2 still needs an R8 map / runtime probe (not a gap service).
