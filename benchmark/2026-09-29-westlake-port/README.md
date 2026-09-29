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

Rule for the next lane: **a bind-time projection that answers "self-package provider"
queries (items 1–2) is inert on a generation whose manifest-parse JNI is missing, because
nothing populates the provider set that would trigger those queries.** Items 1–3 must be
driven from a Java-side manifest parse (the `SelfComponentFallback.load` path already reads
`AndroidManifest.xml`), not left to depend on the native `nativeParseManifestJson`.
Measure the trigger, not just the hook.

## Evidence (board run, screenshots are ground truth)

- Board `5cd1e3dd00000000000000000923012c`, generation
  `6cb40cd610…b9cddb0` (#66, deployed `active_verified`; single route ART `59e1bb45`,
  route `openjdkjvm` `8b462862`, bridge `84695d62`, provider `3aa5d169`, JAR `250958dc`).
- Overlay: r7b `c432d987` (baseline = the generation's own JAR `250958dc`), one stacked
  bind-mount layer; rollback unmounts only that layer.
- Controls run `b8r7b-ctl-20260929T135518`, apps run `b8r7b-apps-20260929T135720`.
- Per-item marker counts (`results.json:effective`): item 4 (nativeLibraryDir) 3 apps;
  items 6/7 (LocalServiceBinders: appops/uimode/locale/account/alarm) and item 15
  (CompatChangeTable) 16 processes each (14 apps + 2 controls); **items 1/2/3 zero** — built
  but never triggered (see rule above).
- No regression: HelloWorld and ZigZag both fully lit with the overlay mounted
  (`runs/…/helloworld/final.jpeg`, `runs/…/zigzag/final.jpeg`), live pids at t+20.

All 14 apps now cross `bindApplication` and reach `ScheduleLaunchAbility` + first frame
(`nativeQueueBuffer`), then crash in the activity's `onCreate`. Visual verdict from the
final screenshots: **0/14 lit** (each falls back to the launcher). The walls collapsed
from scattered bind-time failures into five clean `onCreate` classes:

| class | first cause | apps |
|---|---|---|
| custom Application not instantiated | `ClassCastException: android.app.Application cannot be cast to <app>.Application`; `IllegalStateException: KoinApplication has not been started` | ooniprobe, fd-fennec_fdroid, fd-android, fd-k9 |
| Flutter native loader | `UnsatisfiedLinkError: path is outside app domain: …/app_lib/libflutter.so` | fd-fluffychat, fd-immich, fd-kitchenowl, fd-libre, fd-saber |
| Theme.AppCompat | `IllegalStateException: You need to use a Theme.AppCompat theme (or descendant)` | burgerking, fd-minetest, opencamera |
| resource inflate | `InflateException … requires your app theme to be Theme.AppCompat` | fd-catima |
| missing service | `NullPointerException: INotificationManager.createNotificationChannelGroups … null` (no "notification" stub) | fd-etar |

Per-app first-cause lines and the seven marker lines are in `evidence/<app>.txt`; the raw
`runs/` tree is gitignored.

## Next (proposed r8b, pending outer-loop sign-off)

One Java-side manifest fallback closes the top class and finally triggers items 1–3: when
`nativeParseManifestJson` fails or providers is empty, use the manifest projection already
loaded by `SelfComponentFallback` to (a) set `AppBindData.appInfo.className` from
`<application android:name>` so the app's Application subclass is instantiated, and (b)
populate `AppBindData.providers` from the manifest (Westlake's manifest fallback, filtered
by process). (a) is beyond the literal item list — flag for the outer loop. The Flutter
native-loader wall and Theme.AppCompat are separate walls (generation / later batch).

## Files

`INVENTORY.md` (outer survey) · `make_inventory.py` → `inventory.json` (23 items: 7 ported
records, 16 not-ported reasons) · `b8-apps.json` (control + 14-app manifest) · `summarize.py`
(`summarize.py <controls-run> <apps-run>` → `results.json` + `evidence/`) · `verify.py`
(spec-checks: inventory/not_ported/effective/white_window/lit/no_regression).
