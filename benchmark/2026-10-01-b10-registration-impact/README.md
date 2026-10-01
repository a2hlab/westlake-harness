# U8 registration side effects and native consumers

## What the earlier model got wrong

Calling a complete `register_android_*` function through `dlsym` is **not** a method-table-only proxy: its in-function cache initialization still runs if registration succeeds. Conversely, its caller's initialization, a second DSO's private cache, and a deferred Java-entry initializer are separate mechanisms. Subtracting global names from two replacement implementations does not prove null caches.

The exact U8 first fatal also matters. `ath0-rpn` first fails in `GrDirectContext::dumpMemoryStatistics`, not a font-release JavaVM frame. `glmark2` aborts with `fid == null` in `GetLongField`, called from its own `native_getSceneInfo`; the stack alone contains no AssetManager converter frame. **The subsequent disassembly resolves that omission as a converter tail-call and identifies `AssetManager.mObject:J`; see `NATIVE-FIRST-FATAL.md`.** Actual cache-owner selection remains unknown. Other-attempt donor failures must not replace these selected U8 results.

## Identity and completeness

- `artifact_identity` returned **0**, three `DEPLOYED` lines before ELF inspection. Exact U8 providers: runtime `216b68fbb3a4`, HWUI `be59260f93b3`, libandroid `9ccf64f8d1f6`; complete hashes and target paths are in `REGISTRATIONS.json` / `expected-u8.json`.
- Runtime dispatch source SHA: `a001929dc40858bbbd1d8f883bf2a8d6c8bdb63c1e1827a4b0f7a2275278a6b2`. This is the U8 recipe snapshot, not the subsequent N10b candidate.
- **481/481** local reference files passed SHA verification. Reference tag: `android-14.0.0_r1`, `frameworks/base` commit `299fe6f5d6fc6f1af7c3411dcf4e5efdf7217368`. The outer supplied the read-only source copy and Git/tag attestation; this lane independently checked file hashes, not a complete local Git tree. `reference.json` records that distinction.
- **95 dispatch entries / 94 distinct functions**: 51 HWUI whole-function proxies, 40 strict direct entries, 3 GL entries and one separate Typeface whole-function call. **91** entries are `register_android_*`, **89** have exact AOSP14r1 functions, **2** are custom names, **4** are outside-prefix context. All 95 have provider symbols; this attests availability, not successful invocation or populated cache contents.
- Every matching original function retains its body, source SHA, coordinates, direct initialization lines and cache writes in `REGISTRATIONS.json`. Replacement body snapshots are donor-source evidence, not a cold reconstruction of all objects. Helper effects, late class initialization and unobserved providers remain explicit unknowns.

## Findings

| Mechanism | Evidence and conclusion |
| --- | --- |
| External GraphicsJNI VM initialization | AOSP14r1 `libs/hwui/apex/jni_runtime.cpp:173` sets **GraphicsJNI** VM before its registration loop. U8 `startReg` sets **AndroidRuntime** VM, a different owner; individual provider calls do not reproduce the outer entry. Static context gap; no proven U8 app unlock count. |
| AssetManager duplicate owners | AOSP `core/jni/android_util_AssetManager.cpp:1564`; U8 donor `android_util_AssetManager_aosp.cpp:1577` already initializes runtime `mObject`. Runtime cache `0x20f1c0` and libandroid cache `0x8b9e0` are distinct. Initializing one does not initialize the other. Actual caller/namespace selection and the glmark2 path still require proof. |
| HardwareBuffer | Original registration caches the class/field/constructor at `core/jni/android_hardware_HardwareBuffer.cpp:297`; it is outside this 95-entry inventory. Public `AHardwareBuffer_fromHardwareBuffer` is absent in these three providers, while a namespaced HWUI helper exists. Other providers/registration paths are unknown. |
| Replacement cache names | Nine modules differ lexically: Binder, SensorManager, SurfaceControl, SurfaceSession, DisplayEventReceiver, InputChannel, KeyEvent, InputEventReceiver, MessageQueue. `reviews.json` retains exact original/replacement bodies and explains changed backends, renamed/deferred lookups and remaining unknowns. These are **not nine proven fatal walls**. |
| Deferred initialization negative controls | DisplayEventReceiver fills `g_derClass` / `g_dispatchVsyncMethod` in `nativeInit:452–456`; InputEventReceiver calls `init_jni_refs` from its Java native entry after registration for the correct classloader. Registration-body-only comparisons would falsely flag both. |
| Custom audio names | `register_android_media_AudioSystemCapabilities` and singular `register_android_media_AudioProductStrategy` do not exist in AOSP14r1 according to the outer's full-tree search. Local definitions are `bms/src/adapter/framework/android-runtime/src/android_media_AudioSystemCapabilities.cpp:40` / `:53`, first available copy-in commit `a115654434001a1575c70daa46086a46d3150005`. Earlier origin is unestablished; filename not found in the searched Westlake / 00.Workspace / real-work trees. The plural original is `core/jni/android_media_AudioProductStrategies.cpp:218`, not the singular custom function. The custom implementation returns capability constants / an empty strategy list rather than using the original AudioPolicy cache consumers. |
| Skia initialization | Original `init_android_graphics` also calls `SkGraphics::Init` outside individual registration functions. Other OH Skia or lazy initialization paths have not been excluded; this is not proof of the `dumpMemoryStatistics` cause. |

`known-evidence.json` binds the selected U8 reports to target PID/TID/time and hilog SHA. `ath0-rpn`: terminal `hilog.txt:46651`, first frame `:47181`, RenderThread PID/TID `27323/27348`. `glmark2`: abort `:45186`, signal `:45193`, full stack `:45326–45327`, PID/TID `5301/5324`. These are termination-linked observations, not a new screenshot verdict.

## Native impact, ranked by reference count

All **166** exact APKs and current SHA-pinned physical sidecars were scanned. Identical APK-member/sidecar pairs are deduplicated. Inventory: **888 members**, **492 valid AArch64**, **145 wrong-machine**, **248 wrong-class/endian**, **3 invalid-magic**. Unsupported members are not clean negatives. No missing sidecars were observed. Current sidecar inventory is separately pinned, not retroactively claimed identical to a historical freeze.

**34 apps** expose **115 exact API groups**. `API-IMPACT.csv` is sorted by affected app count; `CONSUMERS.json` includes each import/literal witness and member SHA. Strong imports, weak imports, exact loader literals and literal-only unknown use are separate. Packed/downloaded libraries and computed symbol names remain unknown.

| API | Apps with reference | U8 signed lit negative controls |
| --- | ---: | ---: |
| `ANativeWindow_fromSurface` | 30 | 13 |
| `AndroidBitmap_lockPixels` / `unlockPixels` | 26 each | 10 each |
| `AndroidBitmap_getInfo` | 20 | See machine table |
| `AAssetManager_fromJava` | 17 | 3: fd-minetest, fd-stk, wikipedia |
| `AHardwareBuffer_fromHardwareBuffer` | 7 | 0; still not seven proven failures |

Negative controls demonstrate why reference counts cannot become death or unlock counts. **Proven registration-side-effect deaths from this audit: 0; predicted unlock count: unknown.** The table prioritizes verification, not automatic repair or rollout.

## Reproduce offline

Use the repository environment and SDK tools, no devices. `WORKSPACES` denotes the sibling workspace root. The audit refuses source/provider drift and verifies every supplied AOSP file before comparison.

```sh
source "$WORKSPACES/westlake-inputs/env-mac.sh"
OUT="$(mktemp -d /tmp/registration-replay.XXXXXX)"
HERE=benchmark/2026-10-01-b10-registration-impact
python3 "$HERE/audit.py" --workspaces "$WORKSPACES" \
  --reference-root "$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src" \
  --reference-provenance "$HERE/reference.json" \
  --ported-source-root "$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b87-native/adapter/framework/android-runtime/src" \
  --expected "$HERE/expected-u8.json" --output "$OUT/audit.json"
python3 "$HERE/scan_consumers.py" --workspaces "$WORKSPACES" --output "$OUT/consumers.json"
python3 "$HERE/report.py" --audit "$OUT/audit.json" --consumers "$OUT/consumers.json" \
  --reference "$HERE/reference.json" \
  --signoff "$WORKSPACES/westlake-harness/benchmark/2026-10-01-u8-sweep/outer-signoff.json" \
  --output "$OUT/report"
python3 "$HERE/test_impact.py"
```

`validation.json` records actual validation exits. `landing-paths.txt` lists only this task's new files; `documentation.json` contains exact additive README/DIGEST lines for outer landing. No frozen prediction, runtime, selector exception or device was changed.
