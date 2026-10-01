# System-service gap on the U9 unified state: which services apps ask for, and which come back null

**What was wrong first.** The first request scan (oc-t4, 21:13) counted a service as "requested" when its name
appeared anywhere in the dex string pool, so `text` (161 keys), `log` (160) and `ears` topped the table — none of
them is a Context service. The rework (21:23) went the other way: only 44 of 166 keys had any row (aegis 0 rows
against 21 real services, antennapod without its 10 `connectivity` call sites), and no script was delivered.
Both were bounced (board R2 21:16, 21:28). This directory replaces them with a reproducible call-site scan.

**Rule this sets.** A service is "requested" only at a `getSystemService` call site; it is a wall only when the
app's own log shows it coming back null. Inventory of what we "provide", read from source, is not enough on its
own (see finding 3).

## Method

- `scan_service_calls.py` — for every `classes*.dex` of every APK of the 166 U9 keys, `dexdump -d` (Android
  build-tools 34) and look up to 6 instructions back from each `getSystemService(String|Class)` invoke on any
  receiver. A `const-string` counts only when it equals an AOSP 14 `Context.*_SERVICE` value (206 values); a
  `const-class` counts when AOSP 14 `SystemServiceRegistry` registers that class under a Context constant
  (135 classes), plus the class -> name pairs of the deployed boot `framework.jar`'s own register*Service calls
  (apex initializers: `TelephonyManager` -> phone, `SubscriptionManager`, `CarrierConfigManager`, ...; 167 classes in
  all, added 22:3x after `getSystemService(TelephonyManager.class)` was found uncounted). Verdicts from `benchmark/2026-10-01-u9-sweep/outer-signoff.json`. Output
  `requested-services.csv` (key, service, call_sites, form, u9_verdict, source) and `service-summary.csv`.
  166/166 keys scanned; 2 keys (cv2-anupam-acrylic, cv2-com-chessclock-android) have no call site at all.
  Spot checks against a hand run: toutiao phone 15 / wifi 5 / input_method 42; antennapod connectivity 10.
- `provided-services.{md,csv}` — cc-wiki's inventory of what our runtime answers non-null, read from
  `vm-copies/westlake-current/framework` with file:line (copied from the cc-wiki worktree, uncommitted there).
- `gap_table.py` — joins the two, adds how AOSP 14 builds each manager (`fetch`: `binder` = the fetcher calls
  `ServiceManager.getService*`; `client` = built in-process; `module` = registered by an apex
  `*FrameworkInitializer`, not in `SystemServiceRegistry.java`) and `u9_not_published_keys` = U9 keys whose
  hilog has `SystemServiceRegistry: No service published for: <name>`. Output `gap-table.csv`.

## Findings (U9, 166 keys)

1. **Fetch-time nulls that log are rare and none is a first fatal.** Across all 166 U9 hilogs the only
   `No service published for:` names are `game` (165 keys — explicit null by design, harmless), `textservices`
   (16 keys, 13 lit), `usb` (3, all lit), `fingerprint` (2, lit), `trust`, `media_metrics`, `storagestats`,
   `dropbox`, `usagestats` (1 key each). None of the 51 non-lit keys has one of these as its first fatal
   (`benchmark/2026-10-01-u9-sweep/u9-first-wall.md`).
2. **`phone` comes back null silently.** `phone` is registered in AOSP by `TelephonyFrameworkInitializer`, not
   in `SystemServiceRegistry.java`; route-A has no fetcher for it and the request returns null with no log line.
   U9 evidence: `x` dies at `NullPointerException: null cannot be cast to non-null type
   android.telephony.TelephonyManager` (`com.twitter.util.telephony.a.run`). 36 keys ask for it (12 lit, the
   lowest lit ratio in the table against the corpus 115/166); Toutiao asks at 15 call sites, behind its native
   walls. `bluetooth`, `wifip2p`, `servicediscovery`, `telephony_subscription_service` are the other apex-module
   names nothing answers (no U9 crash on them yet). *Corrected 22:05:* `wifi` and `media_session` are answered —
   see 3.
3. **Read providers from the deployed JAR, not the source snapshot** (corrected 2026-10-01 22:05). The first
   inventory read `vm-copies/westlake-current`, a snapshot older than the deployed JAR 238ffc14. cc-wiki's dexdump
   of the deployed `oh-adapter-runtime.jar` (`deployed-providers.csv`) shows a B8/B7/fetcher layer the snapshot
   lacks: `B8BindExtras.SERVICES` puts appops/uimode/locale/account/alarm/notification/location/webviewupdate into
   `ServiceManager.sCache`; `B7BindFixes` installs `user`; native `WlShortcutService` answers `shortcut`;
   `WifiFetcher`, `AlarmFetcher`, `AppWidgetFetcher`, `VibratorFetcher` and `[B8-FETCH]` media_session /
   power_exemption / restrictions replace registry fetchers. `autofill` is not provided, but its AOSP fetcher uses
   the nullable `getService` and builds `AutofillManager` anyway, so it is not a null manager. `gap_table.py` now
   takes the deployed list over the snapshot and counts only `getServiceOrThrow` fetchers as `binder`; the
   remaining gaps are `gap-table.csv` rows with `gap=yes` (15), led by `phone`.

## Next

The generic fix this points at is registering the apex-module managers that AOSP builds client-side
(`TelephonyManager(context)` first) with safe local binders — copied from AOSP 14 `TelephonyFrameworkInitializer`,
following the deployed `WifiFetcher` pattern, one JAR cluster for U11, regression-gated by the full compare. First
evidence apps: `x` (phone), `toutiao` (phone, once its native walls clear).
