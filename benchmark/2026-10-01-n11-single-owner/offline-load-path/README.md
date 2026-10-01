# N11 deployed-load-path audit

The prior hypothesis that runtime-ClassLoader creation caused the second bridge was too late. In HelloWorld PID 9790, bridge JNI_OnLoad occurs at **15:18:14.738**, while B8 reports runtime-CL namespace creation at **15:18:15.283**. N11's StockOpenNamespace marker never fires. This does not indict the controls: outer read all four HW/ZZ screenshots as own UI, and U8 rollback was complete.

## Deployed entry, not legacy donor source

`artifact-identity.txt` binds provider **0509fe23**, bridge **84695d62**, native loader **fb9dc937** to the N11 deployment receipt. `binary-identities.json` and disassembly preserve the actual ELF inputs. The frozen provider uses `child_main_after_stock.cpp`, whose reinjection does **NOLOAD only**. It has no legacy `[INPUT-RT-CL-CHILD]` fresh-load fallback. The b68 `adapter_bridge_identity.cpp` is the deployed-generation unsealed implementation, unlike the SHA-admission donor source.

The actual provider admission helpers are real plain-dlopen entry points: **LoadVerifiedAdapterBridge at 0xcec8**, **LoadVerifiedAndroidRuntime at 0xcf2c** both pass flags **2** to `dlopen@plt`. `registerNativeMethods` at 0x8f60 calls the latter at 0x8fe8, then resolves and invokes startReg. The nativeHiLog binding in preload uses `adapterBridgeHandle_` returned by the former. This path precedes B8 and bypasses ANL StockOpenNamespace. These callsites are recorded in `provider-entry-disassembly.txt` and `provider-callsite-disassembly.txt`; source segments and SHA are in `source-excerpts.txt` / `source-identities.json`.

For bootstrap loads, actual BCP DEX `OHEnvironment.<clinit>` calls `System.loadLibrary("oh_adapter_bridge")`. Null-ClassLoader OpenNativeLibrary goes to SystemLoader, whose OpenExact indirect-branches through g_sealed_open, installed by WLAR_InstallHostRuntimeServices. The child callback ends in a sibling branch to plain dlopen. That is also not the ANL host callback. J9 `adapter.activity.B7BindFixes` creates its domain later and System.loads TLS/HTML/gapfill; it does not load the bridge. The first extraction used the wrong B7 descriptor and yielded no class; the corrected descriptor and both input-JAR SHA are recorded rather than treating empty output as evidence.

## Which owner each caller actually used

PID **9790** registered Java window JNI at **bridge base 0x7f12c80000** (`nativeCreateSession_impl`: logged 0x7f12d7035c minus ELF 0xf035c). Provider nativeHiLog uses the same owner (`0x7f12d3990c`, 846 symbol offset 0xb990c). Compat shim resolves **another base 0x7f050c0000** (`oh_wm_get_native_window`: logged 0x7f0519f9e4 minus ELF 0xdf9e4). Thus the provider admission handle/Java JNI and compat's NOLOAD handle diverge. `address-derivation.json` contains the arithmetic. Do not mix those addresses with the separate probe PID **11302** ASLR layout.

The probe maps independently show two load-address instances per owner, even though each pair has the **same inode**. Two native-loader mappings also exist (android and route-a). Counting unique files/inodes would miss this failure. **The exact namespace/call stack at first versus second mapping creation is not logged**, so this audit proves the real plain admission entries and divergent handles, not a captured dlopen creation stack or a claim that B8 made the second instance.

## Reachable N11b hook and proposed discriminator

N10b `RealOpenLocalNow` is present in deployed child dc73a28d at 0x40f0. It preloads both owners and emits **[N10b-JNI-OWNER] at 15:18:14.457**, before native-loader init / JNI registration. N11b inserts direct **default -> westlake.sealed.child** inheritance of exactly `liboh_adapter_bridge.so:liboh_android_runtime.so` at this already-exercised point. OH6.1 `dynlink.c` 2408-2445 searches only direct inheritance; 2572 checks fstat before mapping, and 4975+ implements dlns_inherit. It checks both default NOLOAD handles equal the preloaded owners and fails closed; it never fresh-loads to make a lookup succeed. This covers default early admission and bootstrap callers before runtime-CL creation, without modifying frozen provider 0509 or relying on the unobserved ANL-open hook. A child-only candidate tests the hypothesis; existing wrong default residents will refuse initialization rather than silently continue.

Future plan `offline_precheck.expect`:

- **confirm**: `[N11b-EARLY-OWNER]` before JNI registration, bridge/runtime exactly one load-address instance, provider's JNI pointers and compat WM pointer in the same bridge mapping; HW/ZZ own t20 UI, then wikipedia/noice five rounds with unknown-session and screenshot outcomes.
- **refute**: early sharing/handle check refuses, marker absent, owners still duplicate, pointers diverge, or controls regress; stop at smoke and verified rollback U8.

No board access or new screenshot claim was made by this audit. U9 uses accepted N10b and its separate installer candidate; it does not wait for N11b.
