# B6 / task 47: retain R155 ART and isolate its abort-message C++ boundary

The reconstructed ART from task 45 was incompatible with the signed B5 Java/image
cohort. R155 already exports `art::GetFaultMessageForAbortLogging()`; its missing
C wrapper does not require rebuilding ART. This task compiles the unmodified
real-work abort bridge into a separate DSO, links the real-work runtime provider
against it, and regenerates the sealed child manifest and host pins.

## Inputs and host checks

The user explicitly authorized rebuilding `libwestlake_android_runtime_provider.so`
because that library contains `appspawnx_runtime.cpp`, the C-wrapper consumer.
Of the 28 captured R155 providers, 26 retain their exact bytes. Only sigchain and
runtime-provider change; the abort bridge is added. Original ART remains
`59e1bb45…`; boot images and Java JARs are not changed. The previous no-image
experiment is removed by restoring the two original real-work source files.

[ABI evidence](abi-evidence.json) records the `std::__h` ABI-v1 string layout
and the exact board libc++ SHA `9466fb0d…`. The wrapper calls the C++ API inside
that same cohort and exports a buffer/length C API to its consumer. Strict
linking succeeds with `-z defs`, `--no-undefined`, and
`--no-allow-shlib-undefined`. This is ABI/link evidence, not proof that an actual
ART abort has exercised the wrapper.

[Preserved inputs](preserved-provider-inputs.json),
[generation checks](generation-verification.json), [NEEDED closure](closure.json),
[negative controls](closure-negatives.json), and [sigchain coverage](sigchain-symbols.json)
record the host gates. Two builds of runtime-provider, child, and host are
byte-identical. The full NEEDED walk covers 319 libraries and 2,831 edges.
Original board libandroidfw/libicuuc omit Build-ID; they are SHA-pinned external
inputs, not newly built or deployed artifacts. An initial audit incorrectly
classified them as new artifacts and failed; classification was corrected before
deployment without weakening the deployed-generation identity rules.

## Deployment

Only locked board 5ea is used. Native bridge/runtime roots are read from the
signed B5 board and their actual SHA/Build-ID are pinned; those roots remain
unchanged. Each failed trial returns to the complete B5 baseline and rechecks
HelloWorld and ZigZag screenshots before another trial.

Trial 1 exited with code 203 (`190 + WLSCPL_ERROR_EXTERNAL_ROOT`) before ART.
The host mapped Android TGR `c401e710…`, while the manifest bound the separate
R155 TGR `674d3ef3…` at `/system/lib64`. Both bytes and inode differ.
The loader intentionally requires inherited providers to match the verified
inode. Trial 2 binds both TGR paths to the same R155 original, retaining its
bytes and preserving identity enforcement. Trial 1 was fully rolled back;
HelloWorld PID 13098 and ZigZag PID 14092 each displayed their own UI.

Target outcome is recorded below when observation completes.

## Trial 2 outcome

The TGR alias correction passes the loader gate. Child 17111 maps and hashes
confirm host `5a18279e…`, child `df17eede…`, original ART `59e1bb45…`, and new
sigchain `6d5d5538…`. Hilog records `WLCGATE:HSPM:PASS_IDENTITY`, successful A06
and A02 causes, and `CHILD_A02`. The earlier primitive-return LinkageErrors are
absent in this trial. This establishes startup progress with original ART;
it does not prove Wikipedia or repaired implicit-null behavior.

HelloWorld exits with code 1. Its final screenshot is the desktop. The decisive
error is `libbionic_compat.so` unavailable in `westlake.anl.app.17111.1`, followed
by `Unable to create namespace for the classloader ... default-owner namespace
configuration failed: 2`. The real-work host's `StockCreateConfiguredNamespaces`
returns ENOENT when reopening that SONAME inside the app namespace fails,
after creating the bridge namespace and inheritance edge. Whether namespace
residency, inheritance, or allowed search paths cause the lookup failure remains
unverified. No namespace isolation or identity check was relaxed.

Wikipedia/NPE and candidate ZigZag were not run after the HelloWorld control
failed. Status is **blocked**, with zero new lights and null-check mode
**unverified**. This is not advancement beyond Wikipedia's getTheme. Both failed
trials were rolled back as complete generations. Final B5 control screenshots
and process/fault receipts are retained under `rollback-final/`.


Final rollback restored B5 parent 19220. HelloWorld PID 20224 and ZigZag PID
21245 have own-UI screenshots and no new fault files. Board lock was released.
The current lifecycle is **4 pass / 4 fail**: caller, missing-artifact rejection,
loader identity and symbol coverage pass; Wikipedia UI, candidate controls,
post-getTheme advancement and repaired NPE evidence fail. The generic known-answer
suite ran 69 tests, with two skips and no failures. The symbol selector now checks
coverage against the selected ART SHA rather than incorrectly requiring a new ART
build, consistent with the explicit task-47 instruction; the spec is unchanged.
