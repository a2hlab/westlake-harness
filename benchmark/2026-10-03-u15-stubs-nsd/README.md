# U15 stubs = U14 stubs 87cf65cc + android.net.nsd (AOSP 14 r1) = `94a94905` (×2): moves immich past the bind VerifyError; immich stays dead on the libcronet ATrace wall

#90, JAR/BCP, offline. Nothing was deployed to a board.
- The stubs were built on the Mac with the ScanCallback recipe.
- The behaviour test ran on hw248's host ART.
- The wall: `2026-10-03-u13-dead-keys-recheck` (cc-wiki 947c10fbbd). immich's bind fails with
  `VerifyError: Verifier rejected class A2.b … cannot access instance field boolean b7.a.D from object of type
  Unresolved Reference: d7.c`, because route-A BCP has 0 `android/net/nsd` classes.

## 1. What immich actually references (`evidence/immich-nsd-refs.txt`; APK 36b0d136 = the board's)

**The plugin.** It is the Flutter mDNS plugin **bonsoir** (`fr.skyost.bonsoir`).

**App classes that implement NSD interfaces.** Each of these classes is unresolvable without its interface, and each
extends `b7.a`:

| app class | implements |
|---|---|
| `d7.c` | `NsdManager$DiscoveryListener` |
| `c7.a` | `NsdManager$RegistrationListener` |
| `d7.a` | `NsdManager$ResolveListener` |

**Other references.**
- `NsdManager`: `discoverServices(String,int,DiscoveryListener)`, `registerService(NsdServiceInfo,int,RegistrationListener)`,
  `resolveService(NsdServiceInfo,ResolveListener)`, `stopServiceDiscovery`, `unregisterService`. There is also an
  `NsdManager` field in `b7.a`.
- `NsdServiceInfo`: `<init>`, get/set ServiceName / ServiceType / Host / Port, `getAttributes`, `setAttribute`.

**The fatal one.** `getSystemService("servicediscovery")` is only in `A2.b.onMethodCall`, i.e. when Dart calls the
channel. The fatal event is not a call but **linking `A2.b`** during `androidx.startup.InitializationProvider`. The
verifier must prove `d7.c` is a `b7.a`, and `d7.c` cannot be resolved without `NsdManager$DiscoveryListener`.

**Minimal set for the first fatal.** The three listener interfaces, because `d7.c` / `c7.a` / `d7.a` all have the same
shape. Their method signatures need `NsdServiceInfo`, and they are nested in `NsdManager`. So the minimal set is
`NsdManager` (outer + 3 interfaces) and `NsdServiceInfo`.

## 2. The classes (`stubs/donor/`, source `aosp/`)

**Source.** AOSP android-14.0.0_r1 `packages/modules/Connectivity` **bd692130**, `framework-t/src/android/net/nsd/`.
- Local and a2hlab had no copy, so it was sparse-fetched on hw248 from the TUNA mirror (lookup order: local → a2hlab
  → hw248 → download).
- `aosp/` keeps the two files byte-identical to the fetch.

| class | content |
|---|---|
| `NsdServiceInfo` (+ `$1` = CREATOR) | **the AOSP file verbatim** (`f9173b9b`). Its dependencies resolve in the deployed BCP: `ArrayMap` and `com.android.net.module.util.InetAddressUtils` (same `parcelInetAddress` / `unparcelInetAddress` signatures) in framework.jar 3e106350, `android.net.Network` in the stubs. |
| `NsdManager` + `$DiscoveryListener`, `$RegistrationListener`, `$ResolveListener`, `$StopOperationFailureCode`, `$ResolutionFailureCode` | **AOSP lines verbatim** from NsdManager.java `6e30cf2e`: header 1-17, public constants 140-172 / 250-251 / 660-693, the two failure-code annotation types 695-710, the three listener interfaces 712-783 (including ResolveListener's two AOSP 14 default methods). A private constructor and immich's 5 public methods with their AOSP signatures. |

**What `NsdManager` leaves out, and why.**
- The AOSP binder client (INsdManager, executors, `ServiceInfoCallback`) is not present.
- **No `NsdManager` instance can exist on route A.**
  - framework.jar's `SystemServiceRegistry` calls `ConnectivityFrameworkInitializerTiramisu.registerServiceWrappers()`.
    In the deployed stubs that method is **empty**, so no NSD fetcher is registered.
  - `getSystemService("servicediscovery")` therefore logs `Unknown manager requested` and **returns null**.
  - That is AOSP's own answer when the NSD binder is absent: the module registration hits `ServiceNotFoundException`,
    and the fetcher returns null with "Manager wrapper not available".
  - This change keeps that answer: it adds no registration.
- The 5 methods exist so callers verify. Without an instance they are unreachable; their body throws
  `UnsupportedOperationException("NSD service is not available")`.

**Compile-only** (never merged into the jar): the hidden `android.annotation.{IntDef,NonNull,Nullable,SdkConstant}`,
`android.compat.annotation.UnsupportedAppUsage`, and the `InetAddressUtils` signatures.

## 3. Build: `adapter-mainline-stubs-u15-nsd.jar` = **`94a949053ec8c5a520a9a228b64ae8adb861977f92a6b5f63fa689214c4628fe`**

**Recipe.** `build_stubs_nsd.py` = `2026-10-03-bt-le-scancallback/build_stubs_bt.py` (itself the U12 recipe that built
615b8bbe): base jar → `merge_smali.py` adds only the classes in `stubs/members.tsv` → smali 2.5.2 `-j 1`, fixed zip
time.
- Base: **87cf65cc**.
- Built twice: byte-identical.
- Teed log: `evidence/build-stubs-nsd.log`.

**The one recipe deviation.** The donor compile puts `compile-only` before the SDK `android.jar` on the classpath. The
SDK jar carries package-private `android.annotation.NonNull/Nullable` that would otherwise shadow the compile-only ones.
This affects compile-time annotation lookup only.

**Merge report.** 0 members changed in deployed classes; 8 new classes, exactly the list. No synthetic class is dropped:
the jar's `android/net/nsd` set equals the list.

**Class gate** (`gates/class-diff-vs-87cf65cc.txt`, `deployed_class_diff --deployed 87cf65cc --allow-add <the 8>
--frozen`): 268 → 276 classes; **0 dropped, 0 reshaped, 0 added beyond the list, 0 frozen classes broken**, rc 0.

## 4. Behaviour on host ART with the boards' BCP (`test/`, `evidence/host-art-runs.txt`)

**Setup.**
- hw248 android-14.0.0_r1 host `dalvikvm64 -Xint`.
- The 8 board BCP jars plus the stubs under test, and the test-only Log/SystemClock shim from the bt-le run.
- `NsdTest` rebuilds immich's shape: `Base` = b7.a with `public boolean D`; `Disc` / `Reg` / `Res` = d7.c / c7.a / d7.a
  extending `Base` and implementing the three listeners; `Handler.read(Disc)` reads `Base.D` from a `Disc`-typed
  register = A2.b.
- Each case is loaded by name.

| case | new 94a94905 | old 87cf65cc (negative control) |
|---|---|---|
| 0 link `Handler` (the board event) | **PASS** | **FAIL `VerifyError: Verifier rejected class NsdTest$Handler … cannot access instance field boolean NsdTest$Base.D from object of type Unresolved Reference: NsdTest$Disc`**, the board's message shape |
| 1 Handler runs | PASS | FAIL (CNFE `NsdManager$DiscoveryListener`) |
| 2 three listener shapes load; calls dispatch; ResolveListener defaults are no-ops | PASS | FAIL |
| 3 NsdServiceInfo (verbatim) getters/setters immich uses | PASS | FAIL |
| 4 NsdManager public final, no public constructor, the 5 methods, AOSP 14 constants | PASS | FAIL |
| total | **FAILURES 0, rc 0** | FAILURES 5, rc 1 |

## 5. Who else is affected (U12 + U13 stage A, 332 runs)

`Verifier rejected class` appears for **fd-immich only**. No hilog names an NSD class, so the evidence is the verifier
line. First-fatal moves from this change: **1**.

## 6. Prediction for immich (first fatal)

| | |
|---|---|
| first fatal | **moves (high)**: `A2.b` links, the provider init passes, bind is no longer FAILED on the VerifyError |
| next wall | **the libcronet `ATrace_beginSection` relocation** (`UnsatisfiedLinkError … libcronet.143.0.7445.0.so`). In U13 window 1 it already appears 0.5 s after the bind failure on the same thread, and it was the process terminal (`J_invokeStaticMain_main_threw`). It does not depend on the bind result, so it is expected to stay the terminal: **high** |
| lit | **no (0)** while the ATrace wall is shelved (U15 #3). After that come the Flutter raster path (U14 fff9be31 EGL interposer) and LAN discovery. |
| bonsoir at run time | Only when Dart starts discovery: `getSystemService` returns null, as on a device without NSD. The plugin's `MethodChannel` error path reports it to Dart; not a startup fatal. |

**Deploy cost.** `adapter-mainline-stubs` is on the boot class path, so this needs the FZ-005 re-bake. It goes in the
same U15 bake as the framework Bitmap change (outer's plan).

## Rules this round sets

- **A Java VerifyError whose message names an app class as an "Unresolved Reference" is a missing BCP type one level
  down.** dexdump that class's superclass and interfaces, and add exactly the missing platform types. Do not add the
  manager's behaviour.
- **When the platform manager has no service on route A, keep `getSystemService` returning null.** That is AOSP's own
  answer for an absent binder. Ship only what linking needs.

## Files

- `aosp/` (fetched AOSP 14 r1 files).
- `stubs/`: `donor/`, `compile-only/`, `members.tsv`.
- `build_stubs_nsd.py`; `gates/`.
- `test/`: `NsdTest.java`, `build_test.py`, `run_nsd.sh`.
- `evidence/`: `immich-nsd-refs.txt`, `host-art-runs.txt`, `build-stubs-nsd.log`.
- `results.json`.
- Release: `$WORKSPACES/westlake-inputs/generations/u15-stubs-nsd-v1/` (jar + logs + `SHA256SUMS`).
