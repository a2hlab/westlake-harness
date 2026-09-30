# N4 deployment failure and JNI registration-order correction

The scheduled J6 + N4 33/33 sweep did **not start**. Both boards rejected the
original N4 package at the deployer's HelloWorld gate, before J6 was installed.
The deployer automatically restored N2; the original owned J3 overlays were
replayed, and both shell and appspawn-root SHA views matched U3
`0b81cdbe0ed9`. The 61b lock was released at 00:28:36 for the other lane.

## Evidence before interpretation

Original N4 manifest: `1617080a`; runtime: `71f79c84`. 5ea child PID 14100
and 61b child PID 4732 both logged:

```text
No implementation found for void com.google.android.gles_jni.GLImpl._nativeClassInit()
GLImpl.<clinit> -> EGLContextImpl.<init> -> EGLImpl.<init> -> EGLContext.<clinit>
AndroidRuntime::startReg returned -1
registerNativeMethods failed, ret=-1
com.example.helloworld ... exit with code:123
```

`evidence/{5ea,61b}-n4-failure.json` preserves source line numbers and the full
hilog digest. These were normal provider-entry failures, not a new observed
native crash. Fault-directory listings and raw hilog remain in each board's
`diagnostics/`; historical unrelated faults are not attributed to this attempt.

The original N4 startup caller registered EGL and eagerly cached its fields
**before** registering GLImpl. JNI field/method ID lookup can initialize Java
classes; the real dependency chain above reached GLImpl's native initializer
before that method was registered. The isolated cache mock did not model this
cross-class initialization dependency and therefore missed the regression.

## Minimal correction

`n4-registration-order/registration-order.patch` moves the existing full
GLImpl registration block ahead of EGL registration/cache initialization. It
adds no native implementations and does not clear or bypass EGL cache errors.
The source is copied from this repository's N4 implementation (commit
`44b8e0b0a`, with documentation follow-up `9d52f1360`). GLImpl itself remains
the existing Westlake/AOSP port and registration helper from N2.

Only `AndroidRuntime.o` changes among the runtime objects. The immutable package
`westlake-generation-n4-order-216b68fb` has manifest `7bc02de7` and runtime
`216b68fbb3a40b5ac7a90b726f6d8184fa7cdba848ccde56c809abd400a660df`.
Relative to original N4, exactly one payload file changes. Host, ANL, ABI,
ART/provider, JAR and installers remain unchanged by this correction.

`n4-registration-order/build.py` reuses the frozen N4 recipe and objects in an
isolated build directory. It can run in the authorized a2hlab VM with the same
frozen compiler. `build-inputs.json` pins source and original object hashes;
`package.json` pins the output and package manifest. The baseline source-view
provenance is inherited from `../2026-09-30-n4-native/frozen-source-origins.json`.
The actual patch does not touch frozen source files.

## Validation and scope

- Frozen package/source check and deployment dry-run passed.
- Existing real-cache harness passed success, idempotence, ten failed lookups,
  pending-exception and atomic-publication cases.
- Known-answer suite: 82 run, 3 skipped, zero failures.
- The corrected deployment passed the HelloWorld child/maps/SHA gate on 5ea
  with the **same package-base r8b JAR** used by the failed original deployment.
  Its image shows the Hello World UI; see `evidence/order-deploy/final.jpeg`.
- Original J3 was restored before the subsequent master-batch probes. J6 was
  never installed. The planned 66-app results and prediction backtest remain
  **unverified**, not zero lights and not a completed sweep.
- Target probe facts and t20 images are archived separately. Final visual
  acceptance belongs to the outer reviewer. This report does not treat a live
  process or `active_verified` as a rendered app.

The user revised the window after the deployment failure: diagnose first,
release 61b if the logs suffice, keep only a bounded 5ea probe, and return to U3
before 01:02:28. That revised instruction supersedes the original keep-N4/J6
sweep instruction.

The inherited N4 lifecycle remains 3 pass + 1 pending-review on its offline
selectors. It still tests the original N4 package; this result does **not**
overrule the dual-board failure or certify the corrected package. The new
`test_order.py` replays the observed initialization dependency with the real
caller/cache and a mock JNI environment: original fails, reordered succeeds.
Device probes provide the independent check.


## Bounded results and revised exit

The four J3 targets all had t20 screenshots of the OH desktop. Their next
observed walls were fd-app: SystemVibratorManager monitor-enter NPE;
FluffyChat: private libandroid NEEDED liboh_android_runtime unresolved despite
host publication; Burger King: libmmkv NEEDED libz unresolved; Firefox:
libmozglue relocation for __gnu_strerror_r unresolved. Exact source lines and
hilog hashes are in `walls.json`; verbatim counts are in `facts-all.txt`.
These are not four newly lit apps. HW/ZZ were signed by the outer reviewer.

At **00:45:16**, the outer reviewer replaced the return-U3 plan with a new
**U5 three-board 22/22/22 sweep** using this corrected package plus J6.
5ea therefore hands the active N4-order package directly to that new task;
61b had already been returned to U3 and released. See the separate
`../2026-10-01-u5-sweep/` report. Do not confuse that later sweep with this
aborted original N4/J6 attempt or these six J3 probes.

The successful HelloWorld maps contain two offset-zero liboh_android_runtime
mappings; recent U3 maps also contain two. This report does not claim the
single-runtime-instance criterion passed or attribute that baseline property
to the new host. The deployer's single-ART gate is a different check.
