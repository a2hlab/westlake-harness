# android.net members missing from adapter-mainline-stubs: a member-only patch for the next JAR round (not deployed)

#90 toutiao wall ② follow-up, offline. `stub_member_gap.py` (2026-10-02-toutiao-wall3-prediction) found that the
route-A stub BCP jar defines `android.net.NetworkInfo`, `ConnectivityManager`, `TrafficStats`, `WifiManager`,
... with only the members someone needed so far. An app call to a member the stub lacks is a `NoSuchMethodError` /
`NoSuchFieldError` at the first call. U10 known answer: toutiao's CronetInit thread died on
`NetworkInfo.getSubtype()`, declared in `adapter-mainline-stubs.jar`. This directory adds the missing members and
leaves every deployed member and class untouched.

## What was wrong first

- **The stubs were checked by class, never by member.** The T8 gates and `deployed_class_diff.py` confirm that no
  class is dropped or reshaped. `NetworkInfo` exists in the jar but has 7 methods: no `getSubtype`, no
  `getTypeName`, and `DetailedState` has no constants at all.
- **The runtime already implements several of these and nobody could reach them.** The runtime JAR's
  `adapter.activity.OnlineConnectivityManager` overrides `registerDefaultNetworkCallback(cb, Handler)`,
  `getBoundNetworkForProcess`, `isDefaultNetworkActive` and `getRestrictBackgroundStatus`, and its
  `OnlineNetworkInfo` overrides `getTypeName`. But ART resolves an app's call against the *referenced* class (the
  stub), so a member missing from the base class is `NoSuchMethodError` even when the receiver's subclass defines
  it. Adding the base members is what makes those overrides reachable.
- **Toutiao-first is not app-count-first.** The members toutiao needs (97) are not the most widely used ones.
  Across the 166 signed keys the most-referenced missing members are `TrafficStats.clearThreadStatsTag`
  (83 apps) and `untagSocket` / `tagDatagramSocket` / `incrementOperationCount` (70 apps), none of which toutiao
  calls. Round 2 of `members.tsv` adds every member referenced by ≥2 apps that has a safe AOSP default.

## Result (numbers from `sweep/`, `gates/`)

| | before (2f365a75 / f3bcc9d7) | after this patch |
|---|---|---|
| missing android.net members referenced by any of the 166 keys | 181 | **48** (each referenced by ≤4 apps) |
| app references to a missing android.net member | 1386 | **55** (1331 covered, 96%) |
| keys referencing ≥1 missing android.net member | 112 | **13** |
| toutiao: missing android.net members | 97 + `State.compareTo` | **0** (`State` is an enum in the jar; `compareTo` resolves on `java.lang.Enum`) |

Gates on the two persisted jars (`gates/gate-on-*.txt`):

| base (board copy) | out jar sha256 | `deployed_class_diff --frozen` | `verify_identity.py` | added code self-check |
|---|---|---|---|---|
| 2f365a75 (T8, if promoted) | `3a12918a…` | rc=0: 0 dropped, 0 reshaped, 0 unlisted added, 0 frozen broken | 1896 deployed members, 0 changed | 0 missing |
| f3bcc9d7 (U9/U10.1, if not) | `646a3199…` | rc=0, same | 1017 deployed members, 0 changed | 0 missing |

Both bases receive the same additions: 138 members in 17 deployed classes plus 8 new classes. The new classes are
`ConnectivityManager$OnNetworkActiveListener`, `DhcpInfo` (+ `$1`), `wifi.SupplicantState` (+ `$1`), and
`WifiManager$WifiLock` / `$MulticastLock` / `$SuggestionConnectionStatusListener`. They are new types that the
added signatures name and that are absent from the deployed BCP. Frozen classes (FZ-007 tagsoup, FZ-008
`SSLSockets`) are untouched.

## How the patch is built (`build_patch.sh`)

The source of truth is `donor/` plus `members.tsv`.

1. `donor/` holds Java files that copy AOSP **android-14.0.0_r1**. Where the deployed stub has no state behind a
   member, the file uses a safe default and says so. Sources come from hw248
   `aosp-14.0.0_r1-art/packages/modules/{Connectivity,Wifi}`, verified at the exact tag (Connectivity `bd692130`,
   Wifi `82d2b854`); per-file sha256 is in `aosp-sources.txt`.
2. The donor files are compiled with javac and d8, then baksmali'd. `merge_smali.py` inserts into the **deployed**
   jar's smali only the members in `members.tsv`. It refuses:
   - any unlisted member or class;
   - a listed member the jar already has;
   - a `<clinit>` on both sides.
3. smali assembles the result, and only `classes.dex` is replaced in a copy of the deployed jar (T8's
   libphonenumber resources stay).

Same smali/baksmali 2.5.2 and API 29 as T8's `build_t8_effective.sh`.

Reproducibility: smali 2.5.2 orders type_list / annotation items differently run to run, so two builds differ in
those sections and in the offsets that point at them. `code` and `class_data` are byte-identical and baksmali
output is identical. The jar SHA is therefore per build. The **merged smali tree hash** is the reproducible
content identity, and three builds reproduced it: `2c6ef4b8…` on 2f365a75, `85420973…` on f3bcc9d7. The deployable
jars are persisted with receipts (`gates/receipt-on-*.json`: input, output and toolchain hashes) at
`$WORKSPACES/westlake-inputs/generations/net-stubs-members-v1/on-{2f365a75,f3bcc9d7}/`, with the merged smali in
`merged-smali/`.

Semantics, per class (AOSP line numbers in each donor file):
- `NetworkInfo` has no fields in the stub; the runtime's `OnlineNetworkInfo` overrides `getType`/`isConnected`. The
  added getters derive from those virtual getters:
  - `getTypeName` is AOSP's `getNetworkTypeName` table;
  - `getDetailedState` is CONNECTED or DISCONNECTED from `isConnected()`;
  - `getSubtype` is 0 (NETWORK_TYPE_UNKNOWN).
- `NetworkInfo.DetailedState` stays a plain class, because changing its super to `Enum` is a reshape the gate
  forbids. It gets AOSP's 13 constant names as `==`-comparable instances.
- `ConnectivityManager`:
  - the Handler/timeout overloads delegate to the stub's existing 2-arg methods (overridden by the runtime);
  - `getAllNetworkInfo` / `getNetworkInfo(int)` / `isDefaultNetworkActive` derive from `getActiveNetworkInfo()`;
  - `getRestrictBackgroundStatus` = 1 (DISABLED);
  - the listener methods are no-ops.
- `TrafficStats`: counters return `UNSUPPORTED` (-1), the AOSP answer when unavailable. The thread tag and uid
  return -1, the AOSP initial value (the deployed `setThreadStatsTag` is a no-op). Tag/untag and count calls are
  no-ops.
- `Network`: handle 0 (NETID_UNSET, as AOSP for a Network without a netId). `fromNetworkHandle` validates like AOSP.
  `openConnection`, `getAllByName` and `getSocketFactory` use the default network.
- `LinkProperties`, `RouteInfo`, `IpPrefix`, `LinkAddress`, `NetworkCapabilities.getTransportInfo` and
  `NetworkRequest` return the values of the AOSP default-constructed object (empty lists, null, false; a request
  with no requirements is satisfied by any network).
- `WifiInfo` returns the AOSP default-constructed WifiInfo (`<unknown ssid>`, INVALID_RSSI, redactions 1|2|4).
- `WifiManager` reports Wi-Fi as enabled, consistent with the runtime's connected-Wi-Fi report. For the rest it
  answers as AOSP answers an app without privileges: empty scans and configured networks, `startScan` and
  `setWifiEnabled` refused. `calculateSignalLevel` is verbatim; WifiLock/MulticastLock keep AOSP's reference counting.
- `ScanResult` and `WifiConfiguration` add only fields whose AOSP initial value is the Java default.

Deliberately not added (each referenced by ≥2 apps):
- `SSLSockets.setEchConfigList`: `SSLSockets` is frozen (FZ-008); adding it needs the outer loop's freeze-change
  approval.
- `WifiConfiguration.allowedKeyManagement` / `enterpriseConfig`: AOSP's constructor makes them non-null, and the
  deployed constructor cannot change, so they would ship as `null`.

## Prediction: whose first fatal moves

**None.** The 166 U9 hilogs and the 124 U10 + U10.1 window hilogs contain exactly one android.net member error:
toutiao `NetworkInfo.getSubtype` on the background CronetInit thread (U10). The U9 and U10 first-wall tables
have no android.net `NoSuchMethodError` first fatal. The callers of the most-referenced members are background
network paths: `androidx.core.net` TrafficStats/ConnectivityManager compat, Firebase installations, Google Mobile
Ads, `androidx.media3.datasource`, `androidx.work` constraints. Several of these turn a thrown error into a failed
task instead of an uncaught exception, which is why the hilogs stay silent. So the expected window effect is:

- **lit set unchanged** (additions only; deployed members byte-identical in smali);
- **toutiao:** the `No virtual method getSubtype()I in class Landroid/net/NetworkInfo;` line disappears and the
  TTNet `NetworkChangeNotifier` initializes. Cronet itself stays unavailable (`libsscronet` `__cmsg_nxthdr`), and
  wall 0/1/3 of `2026-10-02-toutiao-wall3-prediction` still come first;
- **functional, unverified:** background network features in the 112 referencing keys stop failing silently.

The window check is a log marker, not a lit count: `NoSuchMethodError|NoSuchFieldError ... in class Landroid/net/`
must occur 0 times across all keys. Per-key rows are in `predictions.csv`.

Risk:
- Code that used to catch the error now gets AOSP-shaped defaults: 46 of toutiao's 275 android.net call
  sites catch an `Error` locally.
- `registerDefaultNetworkCallback(cb, Handler)` now reaches the runtime's online implementation, which delivers
  `onAvailable`. Apps that waited for a callback start networking and may meet the next walls (TLS, metasec).

## Deploying it (not done here)

`adapter-mainline-stubs.jar` is a boot-classpath jar, so this needs an ART boot-image rebake with the FZ-005
toolchain on hw248 plus T8's gates (rb / t4b / G1 / G2). Bake on the jar the boards will run (2f365a75 if T8 is
promoted, else f3bcc9d7). Re-run `deployed_class_diff.py --frozen` against that exact board copy before the window.

## Files

- `donor/`: AOSP-copied member sources, one file per class, with AOSP line numbers per member.
- `members.tsv`: the exact allowlist (133 `member`, 5 `support`, 8 `newclass`), with round 2 marked.
- `merge_smali.py`, `build_patch.sh`, `verify_identity.py`: the build and the identity gate.
- `sweep.py`, `sweep/{members,apps}.csv`: the 166-key ranking before and after the patch.
- `gates/`: class-diff, identity and self-check output for both persisted jars, the build receipts, and the
  sweep summary.
- `predictions.csv`: per key, members missing before and after, observed errors, and the predicted change.
- `test_net_stub_patch.py`: merge rules (4 synthetic) plus 3 real-jar known answers (both bases); 7 tests.
- `aosp-sources.txt`: AOSP project commits and per-file sha256.
