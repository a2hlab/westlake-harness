# Native ABI and VelocityTracker port on 61b

The supplied #86 build recipe was not a complete working runtime recipe: it lacked headers, and `liblog_android_supplement.cpp` declares the common log API rather than implementing it. A version node alone also does not make a library or its dependencies visible inside an app namespace. This run separates build/link evidence, on-device load evidence, and screenshot review.

Auxio's music home screen was signed by the outer reviewer in round 1. All seven VelocityTracker JNI methods were registered from runtime `c835a93e`. That proves the registration fix. It does **not** prove that Anki or NetGuard's bionic ABI load succeeded. The imported VelocityTracker implementation deliberately returns neutral values (handle 1, velocity 0); fling velocity calculation remains unsupported.

**Final disposition: partially verified / blocked for the complete #87 ABI delivery.** The experimental namespace candidate maps both Anki `librsdroid.so` and NetGuard `libnetguard.so`, but regresses ZigZag (`libGLESv2.so` needed by libandroid cannot be resolved). All three ANL overlays are therefore rolled back. Only the R1 liblog/VelocityTracker pair is retained; the experimental ANL diff is archived as `anl-experiment.patch`, not applied to the runtime source. See `resident-final.json` and restored-control evidence.

## Sources and build

- #86 source package: upstream commit `08b59282`, cherry-picked locally as `569e0bca`; original Westlake snapshot `532633d` in `vm-copies/westlake-current`.
- `bionic_assert_compat.c`, `bionic_stdio_compat.c`, and `android_view_VelocityTracker.cpp` are copied without semantic changes. The latter is now in AndroidRuntime's startup registration table.
- `liblog.so` reuses the existing AOSP14 logging objects and real log implementation. `logger_write.cpp` is recompiled with Westlake's `native/include/ohos_port.h` (`program_invocation_short_name` maps to musl `__progname`). This is an incremental build; unchanged objects and their source/header snapshots are archived, not presented as a clean full build.
- The required `--version-script` remains. `liblog-bionic.map` keeps the LIBC version node and all previous liblog exports. Export comparison: liblog loses 0 names and adds 22; runtime loses 0 and adds the VelocityTracker registrar. The map retains unused entries from the larger #86 ABI list with `--undefined-version`; undefined *link symbols* still fail `-z defs --no-undefined`. This is partial ABI supply, not all 11 #86 source units.
- The ABI consumer requires `__errno@LIBC`, `__sF@LIBC`, and the real Android log API. It links against the candidate and fails against the original. That is a host link test, not proof of on-board symbol binding.
- OH SDK clang-15 SHA `b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913`; ld.lld SHA `8583bdc812436711a586fc4eae23cbf744606a31377fa3b28b04b639e1f403b4`. Builds use `dockbuild.sh`.

The deployment helper now accepts a native file already declared in the package even if it was not yet listed in `live_hashes`. It checks the original target against the old package **before** upload/mount, then adds the new target to live SHA and child-root checks. Undeclared files still fail; rollback verifies the previous package file hash. Seven deployment tests pass, including existing rollback-on-child-verification-failure coverage.

## Experiments

Only `61b0657200000000000000000324012c` is written. OS, APKs, v3a host/child/providers, bridge `84695d62`, and r8b JAR `d5000c4e` remain the baseline. Each native change uses a separately hashed package and `deploy_generation.sh --replace` with rollback.

| Round | Change | Observed boundary |
|---|---|---|
| R1 | liblog `8c81a937` + runtime `c835a93e` | Auxio music UI signed; Anki `liblog.so` header mapping fails; NetGuard reports missing `nativeSubscribeCommonEvent`. |
| R2 | ANL `35517975`: prepend validated runtime roots to dependency search/permitted paths; retain original direct-app path guard | Both Anki and NetGuard advance to `libc++.so` missing, needed by `/system/android/lib64/liblog.so`. |
| R3 | ANL `7e97f216`: add liblog's recursively audited NEEDED closure to named sharing | Still `libc++.so` missing. Named sharing through the bridge alone is insufficient in this configuration. |
| R4 | ANL `22d354dd`: add the fixed OH platform dependency directory `/system/lib64/chipset-sdk-sp` | Both app native libraries map and old ABI errors disappear; Anki reaches Startup/WorkManager NPE, NetGuard reaches common-event JNI failure. ZigZag regresses at GLESv2 dependency loading; rolled back. |

`log-needed.json` enumerates the nine-member transitive closure. R155/Westlake already use runtime library roots; the ANL changes are route-A integration code, **not** claimed to be a verbatim Westlake namespace implementation. The fixed OH directory is validated on device; host tests validate app-domain rejection and namespace arguments, while the OH-only directory branch needs board evidence. Host tests pass 140 checks, and each ANL candidate was built twice with identical bytes.

R1 Anki's t20 image is a LeakCanary diagnostic page, not the Anki card/deck UI. NetGuard returns to the OH desktop. The disappearance of a previous error behind a different failure is not counted as a successful ABI load. R1 HelloWorld and ZigZag screenshots show their own interfaces. Counts below and in the ACK are copied verbatim from `facts.txt`.

## Evidence and limits

`evidence/` holds record.json, process snapshots, selected exact hilog lines, and screenshots. `evidence-sources.json` gives the complete Mac-readable raw runs. Batches use the master `bms_batch.py`, with 16 MiB/private-off/time/screen preflight and t5/t20 snapshots; `foreground_unconfirmed` is retained rather than replaced with a visual verdict. Visual acceptance remains with the outer reviewer.

Known-answer tests: 69 executed, 2 skipped, no failures. Deployer tests: 7 passed. B8 lifecycle: all six selectors match zero tests and return **Skip**, not Pass; `lifecycle.json` and `lifecycle-error.txt` preserve this limitation. The contract was not edited.

## Reproduction inputs

`build-inputs.json` hashes the archived source, header, object, and candidate files. `external-inputs.json` maps external dependency headers to saved copies. `build-*.sh`, `runtime-recipe.sh`, `check-abi.sh`, and the original failed `try-supplied.sh` record the actual recipes. The archive also preserves the frozen sysroot/C++ headers and all deployed ANL candidates.

The SDK executable/runtime archive is the already persisted #79 kit: `oh61-bms-kit-b79-r3-final.tar.gz`, SHA `61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6`, under the versioned `/home/alvin/westlake-oh6.1-b79-bms-2220df48-installs-51e1b525/` directory on hw248. The #87 archive path and hash are recorded separately in `archive.json`. Both archives are required when the original local build tree is unavailable; recipes contain the original absolute input paths and require restoring those paths or mapping them to the preserved directories.

## Final first blocking exceptions (experimental R4, not the resident rollback baseline)

- Anki: `Unable to get provider androidx.startup.InitializationProvider: androidx.startup.StartupException: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.Class java.lang.Object.getClass()' on a null object reference`. The diagnostic follow-up maps `librsdroid.so`; this is progress past native loading, not an Anki normal-screen acceptance.
- NetGuard: `No implementation found for int adapter.activity.ActivityManagerAdapter.nativeSubscribeCommonEvent(int, java.lang.String[], int, java.lang.String)`. Early maps contain `libnetguard.so` and liblog; child-root liblog SHA is `8c81a937…`. No `__errno` relocation error is observed in this candidate run, but it cannot be promoted with the ZigZag regression.
- ZigZag regression: `JNI FatalError called: Unable to load library: /data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so [Error loading shared library libGLESv2.so: (needed by /system/android/lib64/libandroid.so)]`.

The first rollback invocation correctly refused while the diagnostic Anki process remained alive. `stop-test-apps.py` cold-stopped only this task's three test packages; rollback then removed ANL overlays in reverse order with the normal SHA/maps verification. No check was disabled.
