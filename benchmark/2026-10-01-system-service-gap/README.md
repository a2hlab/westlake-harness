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
  (135 classes). Verdicts from `benchmark/2026-10-01-u9-sweep/outer-signoff.json`. Output
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
2. **Apex-module services come back null silently.** `phone`, `wifi`, `bluetooth`, `media_session`,
   `wifip2p`, `servicediscovery`, `telephony_subscription_service` are registered in AOSP by
   `Telephony/Wifi/Bluetooth/MediaFrameworkInitializer`, not in `SystemServiceRegistry.java`, and none of them
   ever shows up as unpublished — the request returns null with no log line. Verified for `phone` only; the
   others share the mechanism but have no U9 crash to prove it. U9 evidence: `x` dies at
   `NullPointerException: null cannot be cast to non-null type android.telephony.TelephonyManager`
   (`com.twitter.util.telephony.a.run`). Requests: phone 35 keys (12 lit), wifi 30 (8 lit) — the lowest lit
   ratios in the table (corpus average 115/166). Toutiao asks for phone at 15 call sites and wifi at 5, behind
   its native walls.
3. **The source inventory is incomplete.** `user` (104 keys), `appops` (103), `locale` (72), `autofill` (63),
   `shortcut` (58) are fetched through a binder, are not in `provided-services.csv`, and `OHServiceManager`'s
   default branch returns null — yet no U9 hilog logs them as unpublished. Something else answers them (or the
   deployed JAR differs from the vm-copies snapshot). Until that is pinned, treat the `gap` column for `binder`
   rows as unverified; the hilog column is the evidence.

## Next

The generic fix this points at is registering the apex-module managers that AOSP builds client-side
(`TelephonyManager(context)` and friends) with safe local binders — copied from AOSP 14
`TelephonyFrameworkInitializer` / `WifiFrameworkInitializer`, one JAR cluster for U11, regression-gated by the
full compare. First evidence apps: `x` (phone), `toutiao` (phone/wifi, once its native walls clear).
