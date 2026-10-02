# android.bluetooth.le.ScanCallback for fd-plus: our boot class path has 4 of AOSP 14's 22 public android.bluetooth.le classes; one verbatim AOSP class in the stubs moves fd-plus's bind failure

#90, JAR/BCP, offline. Nothing was deployed to a board. Builds ran on the Mac; the behaviour test ran on hw248's host
ART.

## The wall

fd-plus (OsmAnd) fails `ensureBindApplication` in U10.1T8 (`2026-10-03-u101t8-unbound-longwait`, master 5d45806cf5) and
again in U12 (window 4, 5ea):

```
00:51:14.791 [B43-BIND] ensureBindApplication FAILED: java.lang.reflect.InvocationTargetException
             Caused by: java.lang.NoClassDefFoundError: Failed resolution of: Landroid/bluetooth/le/ScanCallback;
               at net.osmand.plus.plugins.externalsensors.ExternalSensorsPlugin.<init>(ExternalSensorsPlugin.java:107)
               at net.osmand.plus.plugins.PluginsHelper.initPlugins(PluginsHelper.java:123)
             Caused by: java.lang.ClassNotFoundException: android.bluetooth.le.ScanCallback
```

`first_fatal.py` picks the later `IllegalStateException: Surface was not locked` (18.059) as the termination. That comes
after the bind had already failed; the earliest wall is the class above.

## 1. What the BCP lacks (`bt_inventory.py` → `bt-inventory.json`)

- **Reference:** the public AOSP 14 API, taken from the android-34 SDK `android.jar` (the jar every build here compiles
  against). The android-14.0.0_r1 source on hw248 (`packages/modules/Bluetooth`, cbb30d72) confirms the class bodies.
- **What we deploy:** the deployed jars, matched by sha256:
  - framework `3e106350`;
  - adapter-mainline-stubs `2f365a75` (U10.1T8) and `615b8bbe` (U12/U13);
  - oh-adapter-framework `2257b835`.

| package | AOSP 14 public | in our BCP | missing |
|---|---|---|---|
| `android.bluetooth.le` | 22 | 4: `ScanFilter`, `ScanFilter$Builder`, `ScanRecord`, `ScanResult` (all empty stubs in adapter-mainline-stubs) | **18**: `ScanCallback`, `BluetoothLeScanner`, `ScanSettings(+Builder)`, `AdvertiseCallback`, `AdvertiseData(+Builder)`, `AdvertiseSettings(+Builder)`, `AdvertisingSet`, `AdvertisingSetCallback`, `AdvertisingSetParameters(+Builder)`, `BluetoothLeAdvertiser`, `PeriodicAdvertisingParameters(+Builder)`, `TransportBlock`, `TransportDiscoveryData` |
| `android.bluetooth` | 41 | 5: `BluetoothCodecConfig(+Builder)`, `BluetoothDevice`, `BluetoothLeAudioCodecConfig(+Builder)` (stubs) | **36**, including `BluetoothAdapter`, `BluetoothManager`, `BluetoothGatt*`, `BluetoothProfile`, `BluetoothSocket` |

**Why so much is missing.** Since Android 13, Bluetooth is a mainline module (`framework-bluetooth.jar` in
com.android.btservices), not part of framework.jar, and our BCP carries no framework-bluetooth. The stubs hold only
the classes earlier rounds needed.

## 2. Who can hit it (`bt_scan.py` → `bt-scan.csv`; static = upper bound)

| | keys (of 166) |
|---|---|
| reference any missing android.bluetooth class | 87 |
| reference `ScanCallback` | 3: fd-plus, toutiao, fd-fitness |
| define a subclass/implementor of a missing class (fails as soon as that app class loads) | 9: fd-plus, toutiao, fd-fitness (`ScanCallback`); fd-im-vector-app, subwaysurfers, x (`BluetoothProfile$ServiceListener`); fd-minetest, fd-stk (`BluetoothGattCallback`); opencamera (`BluetoothGattCallback`, `BluetoothAdapter$LeScanCallback`) |
| **actually fail on an android.bluetooth class in a hilog** (U10.1T8 signing + U12 windows 1–4, `NoClassDefFoundError` / `ClassNotFoundException` / `Failed resolution`) | **1: fd-plus** (both generations) |

### Why fd-plus fails at bind, and what it touches next (dexdump of the frozen APK)

1. `ExternalSensorsPlugin.<init>` @0x77 (line 107) creates `ExternalSensorsDeviceHelper`, which extends
   `DevicesHelper`.
2. `DevicesHelper.<init>` @0x0a does `new DevicesHelper$1()`. **`DevicesHelper$1 extends ScanCallback`** → class load
   → the failure.
3. Then `DevicesHelper.init` runs. On a fresh install there are no stored devices, and `updateDevices` iterates an
   empty list, so it touches no Bluetooth API.
4. The BLE entry points (`BluetoothManager.getAdapter`, `BluetoothAdapter.getDefaultAdapter` / `getBluetoothLeScanner`)
   are reached only via:
   - `DevicesHelper.initBLE` ← `setActivity` ← `ExternalSensorsPlugin` / `VehicleMetricsPlugin.mapActivityCreate` / `init`;
   - the device dialogs.

   `PluginsHelper.onMapActivityCreate` only iterates `getEnabledPlugins()`, and `OsmandPlugin.isEnableByDefault()`
   returns false; neither plugin overrides it. **So a default startup never reaches the classes that are still
   missing.**

## 3. Minimal fix: one class in adapter-mainline-stubs (BCP, needs the FZ-005 re-bake)

**Why the BCP and not the runtime jar.** App classes resolve `android.*` through the app PathClassLoader's parent, the
boot class loader. The runtime jar is a separate PathClassLoader that the app cannot see, so a stub there would not be
found.

**What.**
- `android.bluetooth.le.ScanCallback`, plus its nested `@ScanFailed` annotation type.
- **Copied verbatim** from AOSP android-14.0.0_r1 `packages/modules/Bluetooth` cbb30d72,
  `framework/java/android/bluetooth/le/ScanCallback.java` (sha256 `eae1a43c…`; `stubs/donor/` is byte-identical,
  `aosp/` keeps the fetched copy).
- It is the real class:
  - `public abstract`;
  - `SCAN_FAILED_ALREADY_STARTED…SCANNING_TOO_FREQUENTLY` = 1…6, package-private `NO_ERROR = 0`;
  - empty `onScanResult`, `onBatchScanResults`, `onScanFailed`.
- Its only dependency, `ScanResult`, is already in the stubs. `android.annotation.IntDef` is compile-only, SOURCE
  retention.

**Build.**
- `build_stubs_bt.py` is the recipe of `2026-10-02-u12-jar-r2-bake/build_stubs_min.py`, the one that built U12 stubs
  615b8bbe: base jar → `merge_smali.py` adds only the listed new classes → smali 2.5.2 `-j 1`, fixed zip time.
- base `615b8bbe` → **`adapter-mainline-stubs-u14-bt.jar` = `87cf65ccff4eda56183f98de2eb8e7740db6b7725e429c6799a570ae0b39e73a`**.
- Merge report: 0 members changed, 2 new classes. Built twice: byte-identical.
- Persisted with its teed build log at `$WORKSPACES/westlake-inputs/generations/u14-stubs-bt-v1/`.

**Gates** (`gates/`):
- `deployed_class_diff --deployed 615b8bbe --frozen`: 0 dropped, 0 reshaped, 0 added after allowing exactly the 2 new
  classes, 0 frozen classes broken.
- Against U10.1T8's `2f365a75`: the same, with `Predicate` (U12's) also allowed.

**Deploy cost.** adapter-mainline-stubs is on the boot class path, so this needs an FZ-005 boot-image re-bake (as U12
stubs did). It belongs in the U14 JAR/stubs batch.

### Behaviour on Android semantics (`test/`, `evidence/`)

**Setup.**
- hw248 android-14.0.0_r1 host `dalvikvm64 -Xint`.
- The boards' 9 BCP jars, with only the stubs jar swapped, plus the test-only Log/SystemClock shim from
  `2026-10-03-u14-jar-v1`.
- `BtLeTest` defines an app class `extends ScanCallback`, the `DevicesHelper$1` shape.

| | new stubs `87cf65cc` | old stubs `615b8bbe` (negative control) |
|---|---|---|
| 1 app subclass loads and instantiates | **PASS** | **FAIL `NoClassDefFoundError: Failed resolution of: Landroid/bluetooth/le/ScanCallback;`**: the boards' exact line |
| 2 override runs, base callbacks are no-ops | PASS | – |
| 3 `ScanCallback` is `public abstract` | PASS | – |
| 4 `SCAN_FAILED_*` = AOSP 14's 1…6 | PASS | – |
| total | FAILURES 0, rc 0 | FAILURES 1, rc 1 |

`BluetoothAdapter` stays absent in both: this fix does not change it.

### What is deliberately not added, and the AOSP semantics if it ever is

Each of these has a predicted first-fatal move of 0 (no key fails on it in any hilog; fd-plus's default path does not
reach it), so per AGENTS it is not built now:
- `BluetoothAdapter`, `BluetoothManager`, `BluetoothLeScanner`, `ScanSettings`;
- `BluetoothGattCallback`, `BluetoothProfile$ServiceListener`, `BluetoothAdapter$LeScanCallback`.

**AOSP 14 r1 behaviour without Bluetooth** (source on hw248, `BluetoothAdapter.java:1032-1060, 1190`):
- `getDefaultAdapter()` → `createAdapter()` returns **null** when `BluetoothFrameworkInitializer.getBluetoothServiceManager()`
  or the `IBluetoothManager` service is null.
- `getBluetoothLeScanner()` returns **null** when `!getLeAccess()`.

Our stub `BluetoothFrameworkInitializer.registerServiceWrappers()` registers nothing, so
`getSystemService(BLUETOOTH_SERVICE)` is already `null`, the "device without Bluetooth" answer. A future
`BluetoothAdapter` stub must keep that: `getDefaultAdapter()` → null. It must not hand out an adapter that pretends to
scan.

## 4. Prediction by first fatal (`predictions.csv`)

| key | today | with stubs 87cf65cc |
|---|---|---|
| **fd-plus** | bind fails on `ScanCallback` | **first fatal moves (high)**: `DevicesHelper$1` loads, bind gets past `initPlugins`; next wall unknown. The default path touches no other missing BT class. |
| toutiao | first fatal is native (relocation walls) | 0 at t20 (its `ScanCallback` subclass is in bdlocation, after the native walls) |
| fd-fitness | as today | 0 (only when the BLE device dialog opens) |
| 6 keys subclassing other missing BT classes | as today | 0 (not this class; none observed failing) |
| 78 keys that only reference missing BT classes | as today | 0 |

## What was wrong before

- "No jar defines ScanCallback" was true, but the gap is the whole Bluetooth mainline module: 18 of 22 `le` classes and
  36 of 41 `android.bluetooth` classes are missing.
- Fixing by the static count (87 keys) would build a large fake Bluetooth stack for zero observed failures. The fix is
  sized by the one key whose hilog actually fails, plus a dexdump of what that key executes next.
- `first_fatal.py` names fd-plus's later Surface exception. For bind failures, the earliest wall is the
  `ensureBindApplication FAILED` cause.

## Rules this round sets

- **For a mainline-module class gap, compare the whole package against the SDK's public list**, not just the class in
  the log. Then size the fix by hilog failures and the dexdump of the executed path.
- **A BCP stub for a missing platform class is copied verbatim from the matching AOSP tag** (here 14.0.0_r1, located
  local → a2hlab → hw248). Test it on host ART with the boards' BCP, with the old stubs as the negative control.

## Files

- `bt_inventory.py` → `bt-inventory.json`; `bt_scan.py` → `bt-scan.csv`.
- `aosp/ScanCallback.java.aosp14r1`.
- `stubs/`: donor (verbatim), compile-only IntDef, `members.tsv`.
- `build_stubs_bt.py`; `gates/`.
- `test/`: `BtLeTest.java`, `build_test.py`, `run_btle.sh`.
- `evidence/`: host-ART logs new/old, `hw248-inputs.txt`.
- `predictions.csv`, `results.json`.
