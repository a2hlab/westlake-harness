# B8 #65 — Westlake fixes ported into the route-A runtime JAR (5cd, generation 6cb40cd6)

## What was wrong before, and the rule this sets

The earlier assumption was that porting the seven Westlake bind-time fixes (INVENTORY
items 1–4, 6, 7, 15) into the runtime JAR overlay would light the white-window and B7
apps. It does not, and the run below says exactly why: **on generation `6cb40cd6` the
native symbol `adapter.activity.AppSchedulerBridge.nativeParseManifestJson` has no JNI
implementation** (`UnsatisfiedLinkError`, "No implementation found … tried
`Java_adapter_activity_AppSchedulerBridge_nativeParseManifestJson`"). The bridge's
manifest parse is what fills `AppBindData.providers`; without it every child logs
`[B43-BIND] providers populated: 0`, so `androidx.startup.InitializationProvider` never
runs and the app's own `<application android:name>` is never applied — a bare
`android.app.Application` is instantiated instead of the app subclass.

Rule this sets: **a bind-time projection that answers "self-package provider" queries
(items 1–2) is inert on a generation whose manifest-parse JNI is missing, because nothing
populates the provider set that would trigger those queries.** Items 1–3 must be driven
from a Java-side manifest parse, not left to depend on the native `nativeParseManifestJson`.
Measure the trigger, not just the hook.

**r8b closes it (this batch).** `ManifestJsonFallback` parses the APK's binary
`AndroidManifest.xml` (via `XmlResourceParser` keyed by `android.R.attr` resource id — the
AOSP PackageParser idiom; helpers copied from 00.Workspace `ManifestComponentProjection`)
and emits the SAME JSON the native side would (schema copied from the native producer
`bms/.../package-manager/jni/apk_manifest_jni.cpp`). One smali injection overwrites the
`manifestJson` register in `AppSchedulerBridge.ensureBindApplication` with
`orFallback(manifestJson, bundleName)` — no new `setField`, the isomorphic JSON is fed back
through the bridge's own path, so the existing `buildProvidersFromManifest` and
`applyManifestFieldsToAppInfoLocal` populate providers and set `appInfo.className`/`theme`.
On r8b `d5000c4e` (baseline `250958dc`) **all seven items are effective on-board** (item 1
13 apps, item 2 1 app, item 3 14 apps with metaData filled>0, item 4 3 apps, items 6/7/15
16 processes); `providers populated` went from 0 to 3–9 per app; the ClassCast / Koin
"custom Application" wall is gone (the app's Application subclass is now instantiated).

## Evidence (board run, screenshots are ground truth)

- Board `5cd1e3dd00000000000000000923012c`, generation
  `6cb40cd610…b9cddb0` (#66, deployed `active_verified`; single route ART `59e1bb45`,
  route `openjdkjvm` `8b462862`, bridge `84695d62`, provider `3aa5d169`, JAR `250958dc`).
- Overlay: r8b `d5000c4e` (baseline = the generation's own JAR `250958dc`), one stacked
  bind-mount layer; rollback unmounts only that layer. (r7b `c432d987` was the prior overlay,
  identical except it lacks `ManifestJsonFallback` — items 1–3 were zero there.)
- Per-item marker counts (`results.json:effective`), r8b: **item 1 13 apps, item 2 1 app,
  item 3 14 apps (metaData filled>0)** — all three now triggered; item 4 (nativeLibraryDir)
  3 apps; items 6/7 (LocalServiceBinders) and item 15 (CompatChangeTable) 16 processes each
  (14 apps + 2 controls). All seven ported items are effective on-board.
- No regression: HelloWorld and ZigZag both fully lit with the r8b overlay mounted
  (`runs/b8r8b-ctl-20260929T144035/…/helloworld/final.jpeg`, `…/zigzag/final.jpeg`), live
  pids at t+20.

All 14 apps cross `bindApplication` and reach `ScheduleLaunchAbility` + first frame
(`nativeQueueBuffer`), then crash in the activity's `onCreate`. Visual verdict from the
final screenshots: **0/14 lit** (each falls back to the launcher). But r8b advanced most of
them past their r7b wall to a new, later one:

| r8b first cause (class) | apps | vs r7b |
|---|---|---|
| Flutter native loader `path is outside app domain: …/libflutter.so` | fd-fluffychat, fd-immich, fd-kitchenowl, fd-libre, fd-saber | unchanged — generation work (#67 `libapp_native_loader`) |
| SQLite `SQLiteConnection.nativeOpen` UnsatisfiedLinkError | fd-android, fd-k9 | **advanced** from "KoinApplication not started" — Koin now starts (#67 SQLite JNI) |
| Theme.AppCompat / resource inflate | opencamera, fd-minetest, fd-catima | app-level theme now set, but the **activity** theme (OH `abilityJson`, not `nativeParseManifestJson`) still isn't AppCompat |
| WorkManager not initialized | ooniprobe | **advanced** from ClassCast — `AndroidApplication` now instantiated |
| JNA `libjnidispatch.so` not in resource path | fd-fennec_fdroid | **advanced** from ClassCast — `FenixApplication` now instantiated |
| DI null (`OrderingManagerInteractor`) in SplashActivity | burgerking | **advanced** past the Theme.AppCompat wall |
| `INotificationManager.createNotificationChannelGroups … null` (no "notification" stub) | fd-etar | unchanged — service stub not in the item set |

Per-app first-cause lines and the seven marker lines are in `evidence/<app>.txt`; the raw
`runs/` tree is gitignored. r7b run: controls `b8r7b-ctl-20260929T135518`, apps
`b8r7b-apps-20260929T135720`. r8b run: controls `b8r8b-ctl-20260929T144035`, apps
`b8r8b-apps-20260929T144232`.

## Remaining walls (not in the items-1–4/6/7/15 set)

- **Flutter app-domain** (5 apps) and **SQLite `nativeOpen`** (2 apps): generation/native
  side — #67 (`libapp_native_loader.path_is_in_app_domain`, `liboh_android_runtime` SQLite JNI).
- **Activity-level Theme.AppCompat** (3 apps): the per-ability theme comes from OH's
  `abilityJson` in `configureActivityInfo`, not from `nativeParseManifestJson`; setting
  `appInfo.theme` was necessary but not sufficient.
- **WorkManager / JNA / DI / notification service**: app-specific later walls surfaced only
  after the custom-Application wall was crossed.

## Files

`INVENTORY.md` (outer survey) · `make_inventory.py` → `inventory.json` (23 items: 7 ported
records, 16 not-ported reasons) · `b8-apps.json` (control + 14-app manifest) · `summarize.py`
(`summarize.py <controls-run> <apps-run> [build-tag]` → `results.json` + `evidence/`) ·
`verify.py` (spec-checks: inventory/not_ported/effective/white_window/lit/no_regression).

r8b overlay sources live in `bms/src/adapter/framework/activity/java/` — the new
`ManifestJsonFallback.java` plus the r7b helpers; the build + one-call smali injection are in
`../2026-09-29-bms-link-entry-walls/build.py` (`build.py r8b b5` → `build-result-r8b.json`,
overlay `d5000c4e`), deployed with `../2026-09-29-bms-link-entry-walls/deploy.py`
(`B7_BUILD=r8b python3 deploy.py apply|rollback|status`).
