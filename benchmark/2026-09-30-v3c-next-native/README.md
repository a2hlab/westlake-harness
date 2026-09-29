# v3c next: AudioSystem registration and Anki dependency namespace

The v3c runtime contains the AudioSystem capability source in the repository,
but its retained B91 build never compiled or registered that unit. Anki's app
namespace also omitted liblog's transitive OH dependency roots. These are two
separate native changes; no app success is claimed from the offline build.

## Source and build

- Copy `bms/src/adapter/framework/android-runtime/src/android_media_AudioSystemCapabilities.cpp`
  unchanged (import commit `a11565443`). Add its AudioSystem and AudioProductStrategy
  registrations to the exact B91 AndroidRuntime snapshot. Stereo capability,
  4000–192000 Hz limits and empty policy-strategy fallback are the existing
  Westlake implementation, not proof of working audio playback.
- Preserve B91 `9e14bf20` CommonEvent, B87 VelocityTracker and B67 real SQLite.
  The complete compilation entry and registration snapshot are included here.
  Restore base inputs using `../2026-09-29-native-abi-port/archive.json`, then
  replay B91's documented registration setup. Copy B91 runtime-out and
  runtime-objects to `bms/src/.work/v3c-next-native/` before `build-runtime.sh`.
- Apply the existing `../2026-09-29-native-abi-port/anl-experiment.patch` to the
  current B92 ANL source, preserving its v2 path checks and default READY behavior.
  The B87 R4 experiment passed Anki/NetGuard native mapping but regressed ZigZag
  at missing GLESv2. v3c now declares that GLESv2 shim; this removes the known
  missing-file prerequisite but does **not** prove ZigZag regression-free.
- ANL uses validated bridge roots plus OH's fixed chipset-sdk-sp runtime root
  for dependency lookup, and shares liblog's dependency SONAMEs. Direct app
  loading retains its original app path validation. The version script is kept.

Both libraries build with the retained OH6.1 clang `b107ce03`. Each was built
twice with byte-identical results. Strict runtime linking and Profile-B gate
pass. ANL passes **142 checks, zero failures**, including path negative controls.
The NEEDED order and imported symbol sets are unchanged; neither drops exports.
See `elf-compatibility.json` and `anl-host-tests.txt`.

## Artifacts and rollback

- Runtime: `f87dcdf96615defa463cbb92223fc098dd585bea9e040c9570aedb902609472e`.
- ANL: `b66f1b605b5c7e94b7cf692f926d45ebaa59e50daf4b25c6da5b05b4adfdd9ca`.
- Runtime-only package: `/Users/zhaoyue/orca/workspaces/westlake-v3c-audio-f87dcdf9`.
  Its parent is the accepted v3c candidate package `668e4f7c`.
- Combined **offline candidate**:
  `/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-next-audio-anl`.
  Exactly three payload bytesets differ: runtime and both ANL route/Android aliases.
  `package-changes.json` records the prior hashes. No installer or Java changes.

Use the current worktree deployer or frozen `westlake-v3c-deployer-5fa85f77`,
not the obsolete copy embedded in the source package. After checking the active
package and taking the assigned board lock, temporarily expose the package JAR
for its gates, preserving/restoring the chosen external JAR afterward.

For the runtime-only experiment:

```sh
scripts/lab/deploy_generation.sh SERIAL /Users/zhaoyue/orca/workspaces/westlake-v3c-audio-f87dcdf9 --replace /system/android/lib64/liboh_android_runtime.so --lane LANE
# Exact rollback of this runtime layer:
scripts/lab/deploy_generation.sh SERIAL /Users/zhaoyue/orca/workspaces/westlake-v3c-audio-f87dcdf9 --replace /system/android/lib64/liboh_android_runtime.so --rollback --lane LANE
```

The combined candidate requires the existing `--upgrade` transaction because
ANL is a route/Android alias pair; a one-file replacement must not leave those
copies inconsistent. Dry-run passed with 281 declared files and no device I/O.
Rollback uses the same package with `--rollback`, retaining the preceding ledger
and all lower mounts. Do not apply against a board whose extra native changes
would be lost: derive a new candidate from its current package instead.

## Pending device criteria

Run master batch with preflight, `--focus-check --shots 5,20`, using the current
JAR explicitly. VLC must pass `AudioSystem.native_getMaxChannelCount`; Anki must
map liblog and its dependency chain and pass the previous header error. Record
next exceptions verbatim. HW, ZigZag, Auxio and NetGuard are regression controls.
Anki's launcher can select LeakCanary: an image of LeakCanary is not Anki success.
Screenshots/facts and device rollback are pending; R2 is **partially**.
