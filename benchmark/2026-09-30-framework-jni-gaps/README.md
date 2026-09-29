# Framework native gap inventory (45-minute offline edition)

The earlier gap model missed ART/libcore's own native tables and could confuse a registration attempt with successful binding. This edition enumerates **5,406 unique class/name/descriptor identities** from every DEX-bearing v3a framework JAR. It verifies **2,669 compiled implementation identities**, including **562 newly attributed ART/libcore entries**. The remaining **2,737 rows are an unresolved worklist, not 2,737 proven absent implementations**: 12 observed-unbound signatures, 114 registration-attempt-only signatures, 3 static adapter misses and 2,608 unknowns. See [results.json](results.json).

[jni-gap.csv](jni-gap.csv) is the gapfill handoff; [jni-all.csv](jni-all.csv) retains the entire declaration inventory. Full descriptors keep overloads distinct. Each row records startup/all-code app counts, exact declaration location, observed failures, Westlake source/definition lines and evidence references. [gapfill-batches.csv](gapfill-batches.csv) groups candidates by class. Confirmed r17a fatal bindings come first, then other observed-unbound methods, then unknowns ordered by conditional affected-app count. Do not blanket-stub the unknown rows.

The first six rows cover the seven app failures identified by the outer loop:

| Method | r17a fatal keys | Westlake copy candidate |
|---|---|---|
| Process.getElapsedCpuTime()J | fd-im-vector-app, fd-meet | vm-copies/westlake-current/framework/android-runtime/src/oh_process_cpu_time.cpp:11, registration :20 |
| FileObserver$ObserverThread.init()I | fd-com-amaze-filemanager | vm-copies/westlake-current/framework/android-runtime/src/class_library_services.cpp:72, registration :415 |
| ActivityManagerAdapter.nativeStopServiceAbility(String,String)I | fd-catima | vm-copies/westlake-current/framework/activity/jni/activity_manager_adapter.cpp:130; exact additional candidates in CSV |
| Camera.getNumberOfCameras()I | opencamera | No exact implementation found in the two scanned Westlake snapshots. Local AOSP16 android_hardware_Camera.cpp:1122 registers a different name/signature, _getNumberOfCameras(Parcel,int)I; do not copy its ABI as ()I. |
| VelocityTracker.nativeInitialize(I)J | fd-auxio | vm-copies/westlake-current/framework/android-runtime/src/android_view_VelocityTracker.cpp:36, registration :55; neutral handle stub, not real velocity computation |
| EGLImpl._nativeClassInit()V | fd-shatteredpixeldungeon | No exact implementation attributed in the scanned Westlake snapshots; remains unknown. |

The complete source evidence is in `evidence/westlake-sources.json.gz` and `evidence/methods.json.gz`; CSV paths are absolute and include line numbers. `body_found` is a source-copy candidate, not proof that that source was deployed. Missing matches mean not found in the searched snapshots, not nonexistent everywhere. Source search stayed at the first level of the required order (local Mac trees and vm-copies); no source text was inferred from memory. Existing version/provenance records and per-file hashes are retained. Installer/sidecar work is outside this delivery.

**Registration distinction:** vm-copies/westlake-current/framework/android-runtime/src/AndroidRuntime.cpp:439–448 prints OH_RegHook before calling the original RegisterNatives. Across completed r16/r17a runs there are 2,603 unique target-process registration attempts. The scanner requires the target PID from the app's resolved ApplicationInfo line, retains run/serial/boot/path/line and does not count a pre-call log as successful registration. In particular, nativeStopServiceAbility/nativeSubscribeCommonEvent have compiled registration evidence and still produced explicit ULEs: those are binding gaps, not proof that another function body is needed. The observed-unbound set also contains tolerated Typeface/serial-number helpers; they are separated from fatal-app counts and parked for exception review.

## Reachability and limits

All **66 keys** are accounted for in [app-coverage.csv](app-coverage.csv). **65 original APKs** passed identity checks and were scanned. SubwaySurfers is unknown: the manifest pins 5904cda2…, while its current app-input pins ffd32287…. No identity substitution was made. The base APK's Application, launcher Activity, same-process providers and androidx.startup callbacks root a bounded APK call graph. Framework Java calls extend the graph by at most six edges. **190 gap signatures** have conditional startup paths; **196** have either such paths or an attributed r17a fatal app. All-code references are a separate column, never substituted for startup reachability.

These are potential call paths, not execution-order or branch-feasibility proofs. Framework duplicate definitions are unioned; active BCP selection, ambiguous callbacks, reflection, async work and split DEX remain unresolved. `unknown_no_bounded_path` does not mean first-screen unreachable. This limitation is why all newly generated exception proposals remain draft. Per-app compressed evidence retains roots and caller traces; `graph.py` reproduces the framework closure. The large intermediate framework graph is local-only and reproducible, not part of the small handoff.

## Strict gate and exceptions

```sh
python3 benchmark/2026-09-30-framework-jni-gaps/gate.py \
  --strict benchmark/2026-09-30-framework-jni-gaps/jni-strict.json \
  --exceptions benchmark/2026-09-30-framework-jni-gaps/jni-exceptions.json
```

Expected exit is **1**: 2,737 unresolved entries, zero accepted new exceptions. `jni-strict.json` is the strict list; `jni-exceptions.json` has **2,547 review proposals**, with an object, reason, evidence, exact inventory digest and prior approval references where applicable. First-screen no-path proposals explicitly retain unknown reachability. Only `approval=approved`, an approver, reason, evidence and the matching inventory digest/method/status can subtract an entry. Prior #72 approvals remain unchanged in their original file; their 20-app direct-call scope is not silently expanded to this 66-key startup/transitive scan. This gate is an offline handoff checker; it is not wired into the deployer by this task.

## Reproduce and validate

From repository root, run these scripts in order:

```sh
python3 benchmark/2026-09-30-framework-jni-gaps/inventory.py
python3 benchmark/2026-09-30-framework-jni-gaps/observations.py
python3 benchmark/2026-09-30-framework-jni-gaps/graph.py
python3 benchmark/2026-09-30-framework-jni-gaps/reach.py
python3 benchmark/2026-09-30-framework-jni-gaps/westlake.py
python3 benchmark/2026-09-30-framework-jni-gaps/runtime_tables.py
python3 benchmark/2026-09-30-framework-jni-gaps/publish.py
python3 benchmark/2026-09-30-framework-jni-gaps/test_gaps.py
```

Requires the pinned local package/APK/source/log paths and Android build-tools dexdump/aapt2. No boards, network or runtime repair are used. Tests cover overload identities, attempt-vs-binding evidence, strict/draft/stale exceptions, bounded graph propagation, the complete native set, 66-key coverage, Process/FileObserver known answers and ART-native coverage. R2: compiled/source evidence and target-process ULEs verified; startup impact conditional; runtime behavior and screen results unclaimed. Git metadata is read-only in this lane; outer loop commits.
