# N10b: route-owned JNI libraries and real Emboss over U8

## Evidence first

The failed N10 preloaded JNI owners in `default`. Its HelloWorld crash was
`JVM_NativeLoad+100`, with two ART and OpenJDK JVM instances observed. That
candidate was removed; the original failure evidence remains under
`../2026-10-01-n10-native/board5cd/`.

N10b is an **offline candidate**, not a signed runtime. There have been no board
commands or new screenshots in this task. U8 remains the three-board state.
cc-wiki donor `d95af3a94` was incorporated at the outer loop’s request.
`c8008fce` is preserved as the superseded Emboss-only intermediate; the combined runtime is `7dbfac24`.

| Check | Observed result |
|---|---|
| Child original recipe reproduction | `d240f8d2` exact |
| Child candidate / independent repeat | `884ef2a8` exact |
| Runtime original AndroidRuntime source compile + original object relink | `216b68fb` exact |
| Runtime Emboss + registration initialization / independent repeat | `7dbfac24` exact |
| Existing runtime object changes | only `AndroidRuntime.o` and `android_graphics_Typeface.o`; asset-fd, VelocityTracker and all other original objects unchanged |
| New objects | 6 isolated Emboss/support objects + 1 asset-owner initialization object |
| Frozen package checks | 0 violations |
| Java / stubs / 27 images | original U8 bytes |
| Native N1 / N2 | 51 / 103 rejected; no borrowed approvals |
| Semantic delta from U8 | N1 +23; N2 +0 |
| Actual owners, surface lookup and UI | unknown until approved board window |

## Namespace donor and implementation

Read the actual OH6.1 musl implementation before choosing a loading domain:
`third_party/musl/ldso/linux/dynlink.c`, commit
`02dd8d82887b040b85a4294e9a5039f016fd607a`, file SHA
`e50b30f22a1d2248509c438e33c5e1b143462c4f001cf05a4230f1376c152e9f`.
Its preserved copy is `evidence/oh61-dynlink-linux.c`.

`CREATE_INHERIT_CURRENT` adds an inheritance edge. It is not a snapshot of all
resident objects. Inherited file lookup is one hop; resident lookup also tests
name and inode. `dlopen_ns` selects the named domain.

`src/sealed_child_provider_loader.c` opens the route-a runtime provider first.
Only after that open succeeds does it check resident ART and preload bridge and
runtime through the same `westlake.sealed.child` domain. Owner handles remain
resident. It never preloads those owners in `default`. A missing resident ART
or missing owner rejects startup rather than continuing with a mixed closure.
`test_owner_order.py` executes this actual function against a bounded mock ABI;
it proves call order and refusal, **not** device DSO uniqueness.

## Emboss donor, exact deployed dependency and ABI

cc-t3 supplied the AOSP14 r1 constructor at
`westlake-harness-t3/benchmark/2026-10-01-n10b-emboss-native/src/MaskFilter_createEmboss.cpp`.
`emboss-sources.json` binds its hash, all copied implementations and the exact
U8 AndroidRuntime source. The AOSP helper implementation was copied from
`frameworks/base/libs/hwui/jni/Graphics.cpp`; this avoids adding a direct HWUI
NEEDED edge just to use its float-array helper.

The initial claim that modern Skia removed the backing filter was inapplicable:
OH6.1's **m133 still has the real implementation**, at
`third_party/skia/m133/src/effects/SkEmbossMaskFilter.{h,cpp}` and
`SkEmbossMask.{h,cpp}`, commit `ef08c4838855d9424ad70a47d5d5f4201055fab6`.
The local copied file SHA equals the readonly hw248 source. `MakeEmboss` is
behind `SK_SUPPORT_LEGACY_EMBOSSMASKFILTER`.

The deployed OH Skia is `caa86d58`, not VM `out.75d82d5`'s `f5bd14f8` or the
server's newer `a477c1a9`. It does **not export** `MakeEmboss`. The exact local
link input is preserved in the B11 archive; `evidence/u8-artifact-identity.txt`
binds U8 runtime/HWUI to deployed artifacts. The VM symbol probe in
`evidence/emboss-system-symbols.txt` is explicitly a different artifact.

Copy the real m133 emboss filter and its required hidden support functions.
`emboss-base.cpp` extracts five core methods and the two OH GPU default methods
verbatim, rather than copying unrelated private drawing code or replacing OH
Skia. The filter performs actual blur/lighting and returns a real mask filter;
this is not a null/error constructor stub. An explicit JNI override runs after
the existing HWUI registration and compat table, and rejects registration
failure.

**ABI gate found an intermediate defect before deployment:** `SKIA_OHOS` adds
two virtual methods to SkMaskFilterBase. The first prototype's vtable was
136 bytes; the corrected OH view is 152 bytes. The `50d56b4a` prototype package
is superseded and never authorized. The delivery build enables the OH macro
and copies its default implementations. A new direct NEEDED edge resolves to
the exact `caa86d58` Skia; the system library itself is unchanged. Initialization
and domain behavior still need the board control gate.

## Native registration side effects (cc-wiki handoff)

`src/android_graphics_Typeface.cpp` copies the exact original recipe source and
adds `GetJavaVM` + the exported `_ZN11GraphicsJNI9setJavaVMEP7_JavaVM` setter
**before** delegated HWUI Typeface registration. This mirrors AOSP14
`libs/hwui/apex/jni_runtime.cpp` initialization order, from cc-wiki
`d95af3a94` / `n10b-fix/setjavavm-typeface-fix.md`. Missing VM or setter now
rejects this registration; it never delegates with an uninitialized VM.
HWUI itself remains `be59260f`; its optional defensive source changes are not
part of this runtime-only batch.

Static inspection corrected a narrower premise: the original U8 runtime's
`register_android_content_AssetManager` **already fills** `mObject` in its own
cache. U8 `libandroid.so` exports a second `gAssetManagerOffsets` and an
`AAssetManager_fromJava` consumer. `src/asset-offsets-init.cpp` repeats the
AOSP14 class/field lookup in a separate file, keeps the runtime cache valid,
and explicitly resolves/writes the NDK owner's cache after HWUI registration.
The NDK handle remains resident. Missing field, library or cache rejects startup.
This avoids rerunning RegisterNatives and preserves the entire frozen FZ-003
source/object. Actual symbol resolution and the glmark2 outcome still require
board verification; distinct DSO symbol definitions do not themselves prove
which cache was uninitialized in the failing process.

`test_registration_init.py` compiles the **actual two changed sources** and
executes six success/failure paths against an instrumented JNI/DSO ABI. It proves
setter-before-registration, both field-cache writes, and refusal on absent
prerequisites. It cannot prove on-device DSO identity, render output or GC behavior.

## Packages, gates and rollback binding

`u8-package.json` records both a child-only control candidate and the batch.
Both copy the approved U8 J9/T7e composition, with the T7e provenance receipt
unchanged. Rollback reference fingerprints are recomputed from actual U8
members, not U8's historical U7 reference files. `u7_executor.prepare` checks
all 312 expected identities. The child-only control changes one target; the
batch changes child and `/system/android/lib64/liboh_android_runtime.so`.

`batch-u8-native-gate.json` has no input errors. `batch-u8-gate-comparison.json`
retains every U8 finding. Comparison ignores line and sequence ordinals only;
the authoritative checker/issue IDs and exact exception bindings are unchanged.
The 23 newly scanned uncertainties include the child ART NOLOAD check, JNI
member calls, typed function-pointer callbacks, and AssetManager DEX initialization
closure. The scanner also reports type words `int` and `void` as unresolved calls.
The exact proposal records each object, reason and mock/strict-link evidence; no
checker logic was changed. N2 is unchanged: 103 findings already present in U8.
`batch-u8-exception-proposal.json` proposes all 154 exact manifest/input-bound
exceptions. **None are approved.** Production preflight correctly refuses;
rollout is disabled. No old N10 or other package authorization is inherited.

A failed image check due to omitted `LAB_HOME` is kept in
`batch-u8-production-dry-run-invalid-env.json`: oatdump never ran and G2 rejected
empty disassembly. The rerun uses real remote oatdump. Its result and refusal
reason are recorded separately in `batch-u8-production-dry-run.json`.

## Source preservation and reproducibility limits

`source-archive.json` and `source-archive-index.json` identify the intermediate
6.7 MB archive, copied to `hw248:/home/alvin/` and SHA-verified after copy. It
contains changed sources, 3,175 member identities, exact m133 headers, baseline
runtime/child objects, original recipes and build receipts. The B11 dependency
archive supplies existing OH/AOSP headers/link inputs. Toolchain binary hashes
are in `runtime-build-receipt.json`. This is a source-controlled incremental
rebuild with preserved original objects, **not a full-source cold rebuild** of
all historical U8 components. The final combined runtime archive is recorded in `source-archive-final.json` (7.2 MB / 3,245 indexed members, SHA `3720d581`, remote readback equal);
the earlier archive is retained, rather than overwritten.

Commands (Mac workspace visible in a2hlab, same frozen toolchain):

```sh
# New output directories are required; never reuse interrupted outputs.
N10B_BUILD_OUT=<fresh-dir> python3 build-child.py
N10B_RUNTIME_OUT=<fresh-dir> python3 build-runtime.py
python3 prepare-u8.py
python3 gates-u8.py
# Set LAB_HOME, MAC_HOME and the existing VM ssh/scp tools explicitly.
python3 production-dry-run-u8.py
python3 verify.py
python3 verify-u8.py
agent-spec lifecycle specs/n10-native/t2-child-owner.spec.md --code tools/spec-checks --layers test
agent-spec lifecycle specs/n10-native/t3-emboss-batch.spec.md --code tools/spec-checks --layers test
```

No runtime UI result can be inferred from those offline checks. R2 is partial:
compilation, input identity and gate refusal are verified; DSO uniqueness,
absence of unknown sessionId, constructor execution and rendered t20 remain
unverified.

## Prospective approved-window plan

`predictions.csv` lists the six bridge-wall targets requested by the outer loop:
Wikipedia, fd-app, SPD, flowitgame, dddmodel2 and webrtc-check; Acrylic is the
confirmed Emboss constructor consumer. The same table now includes ath0-rpn and glmark2.
Board work requires a new explicit window and exact exception approval.
First gate is one mapped ART/JVM/bridge/runtime per child, then HW/ZigZag and
five U8-signed controls. Unknown sessionId or control regression means immediate
U8 rollback. For attribution use the preserved child-only candidate before the
combined runtime if the outer loop assigns separate single-variable windows.
Screenshots and alive counts are unknown in this offline report.

## Delivery status

`results.json` records final runtime `7dbfac24`, child `884ef2a8`, native
manifest `342198db` and bundle `8611fc85`. Actual production G1/G2 pass. Frozen
checks have zero violations. Agent-spec Rust-backed lifecycle passes child
3/3 and batch 4/4 with zero skips; initial root-code invocations that skipped
are preserved as failed setup receipts, not counted as verification.
Native preflight still refuses all 154 unapproved findings (51 N1 + 103 N2).
The package deliberately stays `rollout_ready=false`. The exact proposal is
`batch-u8-exception-proposal.json`; the outer loop must approve this binding
and assign a window before any activation.

Intermediate U7/Emboss-only proposals, including `package.json`, `native-gate.json`
and `u8-package-c8008fce.json`, remain historical evidence and confer no
deployment authority. Use only current `u8-package.json` and the U8-prefixed
final reports. No board locks are held.
