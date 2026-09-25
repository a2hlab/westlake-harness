# #48 metasec A2 / A1 board trials

Board:61b0657200000000000000000324012c only. Harness branch
`test/metasec-load-48`, based on the five-fix operator handoff76dcb7d.
No push, no system-partition writes, no SELinux or mount-policy changes.
All VM commands use `orb -m a2hlab bash -lc '<command>'`.

Each round stops the guardian, records/kills the prior app and parent and all
remaining Toutiao processes, renames app-data/data/webview-t-data into a distinct
profile-backups directory, and starts a new parent and child. Prior profiles,
including the working operator profile, are preserved. Consent and article
selection use real `uinput -T -d ... -u ...`; replacement children never count
as survival of the sampled PID/birth. Times are board uptime with CLK_TCK=100.

A2 uses claude-3's1b95d07 preseed script in the parent's actual mount namespace
with nsenter, before host_spawn. The same hook is in the guardian immediately
before recovery spawn. This matters because host `/data/data` is not the app's
namespace. The script's UID variable was renamed and OH restorecon is called
once per path (the original multi-path call printed `invalid args`). The
symlink target remains `/data/local/tmp/asx/lib/arm64-v8a/libmetasec_ml.so`.
Before every round the executable metasec source is hashed; a changed file is
preserved and restored from the original backup before the next trial.

Observed app namespace mounts `/data`, `/data/data` and asx have no noexec flag.
The app_lib file/link label is data_app_el2_file, the asx file label appdat.
Read-only dmesg sampling has not yet established a corresponding metasec AVC;
we do not promote the SELinux inference to a confirmed denial mechanism.

The supplied assertion script is retained verbatim, but its literal
`failed to map library.*errno=13` pattern misses A2's actual message:
`Error loading shared library .../app_lib/libmetasec_ml.so: Permission denied`.
The summary therefore separately counts both EACCES forms, the actual
platform-back-handler exception, X.DEv/main-return, parent terminal status,
and observed lifetime. Zero matches in the supplied errno13 check alone is
not a pass. A background-thread exception is not equated to whole-app exit.

## A1 build isolation

The operator libart009a08fb comes from art-build9acbaec and does not yet
contain the strict FindPackagedCopy helper. In a separate VM worktree
`~/a2hlab/ws/art-build-operator48`, branch `test/metasec48-operator`, its
necessary1a190e8 loader-retry dependency and requestedf162c5e were cherry-picked
as baca9a3 and94f8195. This adds the helper and its call site; it does not import
sensor/property or unrelated #23 runtime changes.

`build_a1.py` validates all454 object hashes and first relinks the unmodified
inputs. Result is byte-identical to deployed009a08fb. It compiles only
link_stubs_arm64.cc, weakens that object, and replaces that one link input;
all453 others and runtime-boundary/ICU/zlib stay unchanged. No full native-runtime
chain or downstream stage rebuild. The new libart is
`ae2cb1829ffa9eca08e1a0fe816edfc33bbe0e1ca3e2f43aaa99e522924a8937`.
Added undefined symbols:0. The five supplied host library-copy tests pass.
A1 rounds disable the A2 hook and start with clean ordinary app_lib data;
otherwise the two treatments would be confounded.

## Live control

Guardian pointers remain `/data/local/tmp/operator45/{child.pid,parent.pid,guard.pid,child.stderr.path}`.
It checks every3s, archives prior logs/faults before recovery, cleans other
Toutiao processes, and reapplies max_map_count1048576. A2 is enabled only by
`/data/local/tmp/operator45/preseed48.enabled`; A1 removes that marker.
To stop the guardian while leaving the app running:

```sh
touch /data/local/tmp/operator45/stop
kill $(cat /data/local/tmp/operator45/guard.pid)
```

Original guardian/metasec/libart backups are under
`/data/local/tmp/operator45-crashes/metasec48-original`.
Per-round data backups are under the existing runtime's
`profile-backups/metasec48-before-<round>`.
