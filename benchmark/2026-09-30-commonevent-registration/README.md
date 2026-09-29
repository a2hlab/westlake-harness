# B91: bind the existing CommonEvent backend

The missing JNI family did not require rebuilding the OH IPC backend. The
retained 84695d62 bridge exports all six OHCommonEventClient functions needed
by the five JNI methods (singleton plus subscribe/unsubscribe/publish/finish/
sticky). `elf-compatibility.json` proves the new imports resolve in that exact
bridge. The five implementations and signatures were copied unchanged from
oc-t4 f6a60fc0 / Westlake `framework/activity/jni/activity_manager_adapter.cpp`.

The old combined registration table also contains ability methods. The B68
source already documents an optional `nativeConsumeConnectionFailure` absent
from older Java layers aborting registration before CommonEvent. This port
registers only the five CommonEvent methods from AndroidRuntime.startReg;
other ability registrations and the bridge remain unchanged. This is a host
finding, not yet a proven explanation of every device failure.

## Candidate

- `liboh_android_runtime.so`: **9e14bf2005290c6e9e689fa779a1019bfcded7436c3a36d7a4973f462f46cd0f**.
- Based on **c835a93e**, preserving VelocityTracker and real SQLite.
- 22 DT_NEEDED entries and order unchanged. No removed exports. Six new
  imports all supplied by retained 84695d62; C++ `std::__h` ABI matches.
- Two compilations of the changed units reproduce the complete library
  byte-for-byte. Strict linker flags include `-z defs`, `--no-undefined`,
  and `--no-allow-shlib-undefined`; Profile-B edge gate passes.
- No ART, ANL, provider, host, installer, Java or bridge change.

## Reproduce

Restore B87's persistent inputs listed in
`../2026-09-29-native-abi-port/archive.json`; that archive includes the source,
toolchain pointers and link inputs. Copy runtime-objects/runtime-out into
`bms/src/.work/b91-common-event/`, keeping the original B87 cache untouched.
Apply `runtime-registration.patch` to B87
`adapter/framework/android-runtime/src/AndroidRuntime.cpp`, writing the result
to B91 `AndroidRuntime.cpp`, and retain `AndroidRuntime.before.cpp`.
`build.sh` compiles using the same dockbuild configuration, restores the private
baseline source with an EXIT trap, and writes to B91-only output directories.
`runtime-recipe.sh` adds just the new CommonEvent registration unit. Its complete
source and unchanged reference files are tracked under
`bms/src/adapter/framework/native-compat/westlake-commonevent/`.

## 61b handoff (pending board availability)

Artifact directory:
`/Users/zhaoyue/orca/workspaces/westlake-b91-commonevent-9e14bf20`.
`package-61b-b90` is a one-file update from the current recorded
`westlake-generation-b90-61b-inet-d977bd15`. If the outer loop advances the
resident ANL/provider first, derive a **new package from that current package**
with prepare_generation_replacement.py and this pinned artifact; do not deploy
an older whole generation or bypass a mismatch.

After taking the board lock and checking active identity, expose the resident
package's JAR for deployer checks, then use `deploy_generation.sh SERIAL PACKAGE
--replace /system/android/lib64/liboh_android_runtime.so --lane cx-t0`.
Rollback is the same invocation plus `--rollback`; it restores that previous
runtime file. Reapply the chosen Java overlay after the SHA gate.

Require `[WL-COMMONEVENT] RegisterNatives 5 methods rc=0`; run vlc, fd-gallery,
fd-etar with master batch/preflight and t5/t20 capture. Preserve the original
UnsatisfiedLinkError counts and each next exception, plus facts verbatim.
Then HW/ZigZag and Auxio controls. Successful JNI binding does **not** prove CES
IPC or callback delivery; preserve callback-initialization/service errors too.

No board writes in this preparation. 61b remains held by the outer full sweep.
R2: host build/ABI checks verified, device effect unverified. B8 lifecycle six
Skip (selectors match zero tests), not pass.
