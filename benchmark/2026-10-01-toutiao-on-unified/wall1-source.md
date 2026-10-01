# Wall 1 source — make `libstdc++` resolvable in the app private namespace (generic, for cx-bms U10 native)

**Wall:** Toutiao `libflipped.so` (DT_NEEDED `libstdc++.so`) fails its private-namespace closure; DIGEST
558: "fails libflipped→libstdc++ private closure despite U8 globally deploying that SONAME shell." The lib
is deployed; the gap is that the **app private namespace does not inherit it**.

## The mechanism (pinned, current U9 code)
On route-A the app's private linker namespace inherits a fixed set of system SONAMEs from the bridge
namespace; a SONAME not in that set is unresolvable inside the app namespace:
1. **`bms/src/adapter/framework/native-loader-oh/policy/native_bridge_policy.v1.json:36` `shared_sonames`** —
   the authoritative list. **Current value (6):** `libandroid.so`, `libEGL.so`, `liblog.so`,
   `libmediandk.so`, `libz.so`, `libwestlake_bionic_pthread_bridge.so`. **`libstdc++.so` is ABSENT**
   (so is `libc++.so`, but apps bundle their own `libc++_shared.so`; `libflipped` needs the *system*
   `libstdc++.so`).
2. `bms/src/adapter/framework/native-loader-oh/src/native_loader.cpp:99,120` —
   `config->bridge_shared_sonames = OwnPolicy(policy::kBridgeSharedSonames)` reads that list.
3. `bms/src/adapter/framework/appspawn-x/.../src/westlake_stock_host_main.c:201-222` — builds the app
   namespace: `dlns_create2(app_namespace, app_search_paths, LOCAL_NS_PREFERED)` + `dlns_set_namespace_separated(true)`
   + `dlns_set_namespace_permitted_paths(app_permitted_paths)` + **`dlns_inherit(app_namespace,
   bridge_namespace, bridge_shared_sonames)` (:217)**. Only the sonames in `bridge_shared_sonames` are
   inheritable from the bridge namespace into the app namespace.

**So:** `libstdc++.so` is staged in U9 (`native/payload/android/lib64/libstdc++.so`, sha `7e06cd8b…`;
"globally deployed") but is NOT in `shared_sonames`, so `dlns_inherit` never exposes it to the app private
namespace, and `libflipped`'s closure cannot resolve it.

## Old route = evidence this resolution is correct (not a literal line to copy)
tt-rt.tar (2026-09-28, the working route) ran Toutiao, so `libstdc++` WAS resolvable in its app namespace
then. The old route is the CLAMP48/appspawn-x architecture (its namespace set lived in the old host, not
this policy json), so there is no single old line to bit-copy; the current U9 generic equivalent is the
`shared_sonames` list above. The copy is the *decision* (system `libstdc++` belongs in the app-inheritable
set), proven by the old route; the U9 landing point is `native_bridge_policy.v1.json`.

## Implementation rule for cx-bms (U10 native, one version with the shim)
- **Change exactly one thing:** add `"libstdc++.so"` to `shared_sonames` in
  `native_bridge_policy.v1.json` (and rebuild `libapp_native_loader.so` / whatever bakes the policy, which
  cx-bms owns). Do NOT add `libc++.so` (apps carry `libc++_shared`); do NOT touch the other 6.
- **Which key benefits:** any app whose bundled `.so` DT_NEEDs the *system* `libstdc++.so` — Toutiao
  `libflipped` is the trigger; the full consumer set is oc-t4's `libstdcxx-consumers.csv`.
- **Other-app impact:** additive — adding one inheritable SONAME removes nothing; apps that never
  reference `libstdc++` are unaffected (they simply never inherit-resolve it). **Verify no second copy is
  loaded:** `libstdc++.so` exists twice in the payload (`android/lib64/libstdc++.so` and
  `android/lib64/westlake_native/libstdc++.so`) — the bridge namespace must resolve ONE (cf. DIGEST N3b:
  a second resident copy is its own wall). Pick the `android/lib64/libstdc++.so` the bridge's
  `bridge_search_paths` already covers.
- **Regression controls (single-variable compare_runs + non-regressing full sweep, AGENTS freeze rule):**
  (a) controls `helloworld`, `zigzag` (must stay lit); (b) 2 already-lit C++-native apps that do NOT need
  system `libstdc++` (e.g. a Flutter/NDK app from the U9 lit set) to prove the extra inherited SONAME
  causes no change; (c) Toutiao (`com.ss.android.article.news`) to confirm `libflipped→libstdc++` resolves
  and wall 1 clears. Gate: U9-vs-U10 full compare shows zero regression.
- **Then re-assess wall 2** (`MainActivity enableGlobal null`, app-map state) on-board — expected to fall
  out of wall 1; add NO Boolean stub.

## Not this round
This is the source/spec for review. cx-bms builds it into U10 native (with the shim, one version),
regression-gated. No deploy here.
