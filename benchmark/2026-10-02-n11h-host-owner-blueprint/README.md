# N11h host-owner blueprint — design only

**The attribution must be corrected before a patch is approved.** N11g's live callback and two remaining bridge/runtime load bases establish that its child callback change is insufficient. They do **not** establish a separate host plain-default `dlopen` site. The deployed U9 host contains no such direct call for these owners. This blueprint proposes a measurable host **namespace-sharing** change, not removal of a nonexistent host open. No patch, build, package, device command or board lock was produced.

## 1. Artifact-bound location evidence

Base is deployed/signed U9 appspawn-x **`1d3b08816969369a1941a3877a8a3d6addf604dd830bd3753bbd883ea74aa8b3`**, from `$WORKSPACES/westlake-generation-u9-j10g-238ffc14/native/payload/runtime/appspawn-x`. This exact ELF was used for the disassembly, dynamic section, symbols and strings below. Its donor source `$WORKSPACES/westlake-harness-bms-deploy/benchmark/2026-09-30-n4-native/src/westlake_stock_host_main.c` is byte-identical to U9 `native-checks/n4-host.c` (**`7fe4369d26d5c832099177984a0d1fc7d75c0deabc40ef5f7237ab593ab2cd47`**). `../2026-10-01-n11-single-owner/host-build-receipt.json` records a byte-identical baseline reproduction of 1d3b0881. That is an existing receipt; no new compilation was run for this design.

All six direct open sites in the actual ELF are recorded in `evidence/u9-host-load-calls.json`:

| Function / PC | Actual operation | Implication |
| --- | --- | --- |
| `main` / `0xc51c` | `dlopen(plugin_path, 6)` = NOW\|NOLOAD, source :629 | Child-plugin handle lookup after module installation; it cannot freshly load bridge/runtime. |
| `StockCreateConfiguredNamespaces` / `0xcb2c` | `dlopen_ns(bridge_namespace, bootstrap_soname, 2)` | An explicit bridge-domain bootstrap. Its dependencies can be independently loaded if the resident sealed owners are not shared. |
| Same / `0xcc90` | `dlopen_ns(app_namespace, ABI_path, 258)` | Flutter/native-private ABI load; not a default open. |
| Same / `0xcd70` | `dlopen_ns(app_namespace, runtime_path, 258)` | Selected Flutter/native-private runtime publication; HelloWorld is outside that package list. |
| Same / `0xce10` | `dlopen_ns(app_namespace, OpenSLES_path, 258)` | Selected native-private audio path; not a default open. |
| `StockOpenNamespace` / `0xd098` | `dlopen_ns(app_namespace, path, mode)` | Generic host app-domain opening; no exact-owner special case in deployed U9. |

`evidence/u9-host-load-call-sites.txt` preserves instructions and argument setup; full selected functions are separate small disassemblies. The host's dynamic section has SONAME `appspawn-x`, no bridge/runtime DT_NEEDED and no RUNPATH. Its strings contain the runtime path/private sharing list, but **no `liboh_adapter_bridge.so` string** and no legacy `INPUT-RT-CL-CHILD` string. Absence of a string alone is not proof; it corroborates the full direct-call census and source.

The callback ownership is separate: `westlake_android_child_plugin.c:702` assigns `child_services.open_sealed_exact = WLSCPL_OpenPreparedNamespace`; the following fields point to host `StockCreateConfiguredNamespaces` and `StockOpenNamespace`. `open_sealed_exact` is a **service-table role**, not a function implemented by the host executable. U9 child dc73a28d has a local `WLSCPL_OpenPreparedNamespace`; it has no exported `g_owner_handles` accessor. N11f/g's static handle array cannot be directly accessed by a host-only U9 patch. See `evidence/child-service-table.txt` and `evidence/u9-child-owner-symbols.txt`.

N11g's measured PID 6873 remains decisive: ART/JVM 1 each; bridge at `7ef6080000 / 7efddc0000`; runtime at `7ee0700000 / 7ef6240000`, counted by load base. Its callback emitted `route=sealed/resident` and branch 0. These prove callback execution and duplicate owners, **not the dynamic creator of every later mapping**. A host indirect call, an OH dependency constructor, a NativeLoader-created domain, or a child `dlopen_ns` dependency resolution cannot be assigned a specific minting PC from maps alone. No instruction in this census supports the requested claim that a host plain-default open of these owners has already been proved.

## 2. Proposed minimal host change

**Preferred candidate: publish the already-resident sealed owners into the host-created domains before their first load, then return only the resident owner for exact protected requests.** Change only the adapter host namespace callbacks and small local helpers in the source corresponding to 1d3b0881. Keep U9 child dc73a28d, provider 0509fe23, runtime ac59dec0, bridge 84695d62, ART/JVM, all JARs/images, installation chain and other native artifacts unchanged. N11g is no longer active; do not silently stack its child into this host-only experiment.

Design steps, not an applied diff:

1. In the specialized child, use `dlns_get("westlake.sealed.child", ...)` to select the existing owner namespace. Look up both exact canonical owner paths there with `dlopen_ns(..., RTLD_NOW|RTLD_LOCAL|RTLD_NOLOAD)` and require non-NULL handles. This is an existing-object query, not an open that may create a fresh copy. Preserve current PID/name/argument/mode guards. Missing owner yields the existing typed namespace failure and a live diagnostic, never default fallback.
2. In `StockCreateConfiguredNamespaces`, add the direct bridge-domain → sealed-owner edge **before** its bootstrap `dlopen_ns`. Add the app-domain → sealed-owner edge before any private ABI/runtime/app load. Share only `liboh_adapter_bridge.so:liboh_android_runtime.so`, preserving all current non-owner libraries.
3. For native-private branches that already inherit from the sealed namespace, form the union in the **original single call**: keep runtime/bionic/log/libc++ and add bridge. Do not issue a second `(child, same parent)` inheritance call: OH 6.1 replaces that edge's whitelist, as U10's OrganicMaps regression proved. Existing default edges, allowed paths, `LOCAL_NS_PREFERED`, app→bridge permissions and private package selection remain intact.
4. In `StockOpenNamespace`, recognize only the two exact canonical owner paths or their exact basenames. Return a NOLOAD resident handle from the sealed namespace; no application-domain fresh open and no default retry for these two. All other requests retain the exact existing `dlopen_ns(app_namespace, path, mode|RTLD_LOCAL)` behavior.
5. Emit actual-call logs through the host's existing strong HiLog channel: `[N11h-HOST-OWNER] action=resident-check|inherit target=... owner=... handle=... rc=...`, and `[N11h-HOST-OPEN] action=resident|reject path=... target=... handle=...`. Entry alone is insufficient: smoke requires a real configured-domain inheritance and both resident checks. Record actual target names and path; never print that single-copy succeeded merely because a handle exists. If the protected open branch is reached, its live marker is required too.

Mechanism donor: `../2026-10-01-n11-single-owner/src/host.c` (`N11ShareJniOwners`, `N11OwnerPath`, host callback changes) and real-work `WLSCPL_InheritAndroidRuntimeV1` at `src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/src/sealed_child_provider_loader.c:366–410`. The former compiled and reproduced the U9 baseline, but its single-owner behavior was **not signed successful**; borrow the local mechanism, not a claim that the fix is verified. The latter shows the existing resident-runtime publication pattern. No generic process-wide handle registry is needed.

Recorded OH6.1 musl source, commit **02dd8d82887b040b85a4294e9a5039f016fd607a**, `../2026-10-01-n10b-child/evidence/oh61-dynlink-linux.c:2408–2445, 2572–2590`, checks directly inherited resident DSOs by name/inode before mapping. It is one-hop sharing, and cannot merge a duplicate already created. Consequently installation before the first bridge bootstrap load is essential. The source supports the mechanism, not proof of current runtime path selection.

Do not redirect `libandroid.so` by matching SONAME. U9's distinct `libandroid.so` shim has a runtime-like SONAME; exact pathname/product identity wins. Its dependency resolution should use the new resident edge, while loading that shim itself keeps the old path. Do not add all OH libraries or change system SONAMEs.

Alternative: add an explicit owner-accessor/service ABI from child to host and return `g_owner_handles`. It provides authoritative identity but requires coordinated child+host change, structure-size/version checks and reference-lifetime agreement. U9 cannot satisfy it unchanged. **Not selected** for the one-host observation. Linking default→sealed would also affect every default-domain dependent and is not selected. Missing resident handles must refute the candidate rather than trigger either alternative automatically.

## 3. Before-build and artifact gates

Implementation requires outer review of this corrected attribution and preferred mechanism first. Reproduce U9 1d3b0881 byte-identically using the archived N4/INET host object recipe; refuse a generation mismatch. Co-build only the adapter host translation unit. Do not rebuild the frozen stock spawn/fork/security objects, change GID3003, product TLS, pthread operations, service installation, socket decoding, fork sequencing or native provider registration.

After approval, audit the **final executable**, not just source tests:

- `artifact_identity.py`: full deployed-base SHA/build identity, candidate provenance and host/child generation-binding agreement. Preserve U9 unlocked-loader semantics; no invented hash lock or admission change.
- ABI/consumer/calls: 0 removed exported symbols and 0 structural drift; all existing consumer/service-slot layouts intact. Only the two namespace callbacks plus new small helper functions may change call sets. `main`, `InstallPluginHostServices`, frozen stock spawn/security/thread functions remain unchanged. New lookup/log imports must be explicitly listed and justified.
- DT_NEEDED ordered list, SONAME `appspawn-x`, RUNPATH/RPATH, flags, init/TLS surfaces: identical. Any additional dependency needs separate approval; no broad link-order change.
- `deployed_strings_diff` against 1d3b0881: preserve service/socket names, generation strings, system paths, default/private library lists and established markers. Every removal/addition gets an evidence-backed classification; only new exact-owner list/diagnostics or reviewed binding metadata may differ. Raw nonzero output must remain available even if its reviewed form passes.
- Read-only/object identity and final callsite audit: no new plain default open for owners, no loss of INET, TLS/product-TLS, namespace PID guards or frozen behavioral witnesses. Negative cases: absent sealed namespace/owner, malformed path/name, GLOBAL mode, alias `libandroid.so`, and non-owner requests. Same-parent inheritance occurs once with the complete old+new whitelist. Failed logging is ineffective smoke, not success.
- N1/N2 on the final manifest/sidecar plus full DT_NEEDED consumer closure; no REJECT after manifest-bound outer exceptions. Inherited NOLOAD findings are reviewed for the actual new site, not copied merely by function name. `check_frozen.py --package`, baseline frozen witnesses and strict production executor dry-run all pass before locking.

Candidate SHA, manifest, prospective runtime fingerprint, exceptions and executable window plan are **unknown/not produced** in this design. Do not construct a runnable plan with placeholders.

## 4. Proposed 61b window and retreat

Observation only, <=30 minutes, stop new keys at minute 20. Before LOCK check VM (`orb -m a2hlab true`), target availability and ws bind mount; any failure aborts before lock. Use master `board_run --detach` after approval. After lock first assert signed U9 318 assertions, empty diff/absent, runtime **a2919b793eb6**, BOOT **4db882a81732**. Start continuous hilog before changing the one host. Activation may restart only appspawn-x via existing transaction primitives; no foundation/installer/board restart.

Apply the one host transaction, verify exact candidate SHA in parent and child views, plus unchanged U9 child and all 318 identities except the approved host path. Host changes may alter the runtime fingerprint: compute candidate expectations from the final composition and fail unknown/mismatched values. Probe filenames and load bases, not distinct inode/path count.

Hard smoke: actual host resident-check/inherit markers, ART/JVM/bridge/runtime each **one load base**, HW and ZZ t20 process facts and screenshots. Entry strings or namespace edges alone do not pass this gate. The marker must identify the real classloader/domain path; a missing configured-domain marker refutes reachability, not prove the route unnecessary. Any additional load base or owner miss stops before observations and runs finish.

If smoke passes, prioritize the four session-miss targets `fd-noice`, `fd-uhabits`, `noice`, `cv2-org-andresoviedo-dddmodel2`, then Wikipedia and existing canaries (`fd-k9`, `fd-com-amaze-filemanager`, `fd-libretube`). Clean reinstall; shots 5/20; facts unchanged; unknown keys remain unknown. Use a prediction table written before dispatch. Outer reads t20 and signs `predict_vs_actual`; this lane supplies no lit count. A target that remains white or any control/canary/Wikipedia regression refutes the proposed gain under the approved oracle.

`before_unlock` always finishes back to signed U9: stop own capture, drain child processes through existing guarded cold_stop/OrganicMaps rollback handling, restore original host bytes/mount stack, verify 318 + dual fingerprints + parent/child views, run recovery HW/ZZ smoke, final 318 recheck, then unlock. Never bypass a live-child guard or kill the parent with SIGKILL. A failed rollback/smoke/final retains lock and reports the exact failing step. A host startup failure must immediately restore the saved U9 executable before retrying parent startup. Unexpected board reboot or USB loss pauses the window and uses the approved RUNBOOK recovery; no on-device persistent service is added.

## 5. Blast radius and rebasing

The host is the executable serving every BMS spawn, so one namespace mistake can break every app, not just the white-screen targets. Main risks: inheritance installed too late, whitelist replacement dropping libsurface/bionic/log, classloader borrowing lifetime, wrong alias/SONAME owner, stale fork-time namespace/handle caches, lookup permission failure, and control-group load-order regressions. Restrict state to the specialized child's existing namespaces, keep ordinary paths/flags and stock spawn objects unchanged, log real paths and measure actual mappings. Keep the one-host rollback package and signed U9 recovery smoke ready before apply. No production rollout is implied by a successful short window.

If U10.1 is later promoted, **rebase on host r3 65cc3535** and its actual final deployed SHA, preserving resident-compat, INET, SoundPool policy and all current native-domain edges. Redo baseline reproduction, callbacks/calls/strings/NEEDED/consumer audits, frozen gates, manifest exceptions, identity/fingerprint and window plan. Never overwrite r3 with a rebuilt 1d3b0881 host. The present proposal is tied only to U9.
