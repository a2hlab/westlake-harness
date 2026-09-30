# Flutter r4: blocked by caller namespace permission

**Current result:** r4 built and deployed successfully; fixed-JAR HW/ZZ controls
remain on their own screens. All six Flutter apps fail before private-library loading: musl rejects the sealed
ANL caller creating westlake.flutter.*. All six t20 images show the launcher.
The original v3c package and exact r17p JAR were restored and verified. No fifth build.

The original gate below records why the initial two-file proposal was expanded.
Its old missing-symbol list is historical, not the current four-library closure.

## Measured result

All six extracted arm64 engines were matched by SHA256 to the engine entry in
the APK whose SHA matches app-input.json. FluffyChat, KitchenOwl and LocalSend
have **476** strong imports; Immich, Aves Libre and Saber have **477**.
The deliberately optimistic proposed-owner physical closure contains **300 ELF
files per app** (this is an audit superset, not a namespace allowlist). It assumes
libandroid resolves to current runtime, GLES2 to platform GLES3, dl/m to OH libc,
and includes the existing bionic/pthread supply. Even under those assumptions,
all six still lack:

| Kind | Missing requirement |
|---|---|
| DT_NEEDED | `libjnigraphics.so` |
| Window API | `ANativeWindow_lock`, `ANativeWindow_unlockAndPost` |
| Bitmap API | `AndroidBitmap_getInfo`, `AndroidBitmap_lockPixels`, `AndroidBitmap_unlockPixels` |
| bionic ABI | `__openat_2@LIBC`, `__gnu_strerror_r@LIBC`, `__cmsg_nxthdr@LIBC` |

Cross-checking **every ELF in the package**, including host and roots outside the
engine graph, also found no definitions for these eight. The first scan selected
the route copy of pthread bridge and listed `__register_atfork`; correcting the
index to the Android bridge that supplies it removed that false positive. Its
`__register_atfork@@LIBC` is retained as a positive control in the final audit.

There are also **292/293 versioned imports with only unversioned candidates**,
mostly ordinary libc functions. These are recorded separately: an exact version
set comparison is not an OH musl resolver implementation. They are **not** claimed
to be 292/293 additional failures. The eight absent names suffice to reject the
current gate; loader version compatibility remains an explicit future check.

## Existing implementations, ready for an expanded scope

Mac search found all missing API families under Westlake
`vm-copies/westlake-current/framework/webview-shim/`, repo commit
`532633da63b770d3d459c74683db6d7a1f82a022`:

* `webview_bionic_shim.c`: `__openat_2`, `__gnu_strerror_r`, `__cmsg_nxthdr`.
  Its comment around1233 explicitly says Flutter discovered the missing imports.
* `libjnigraphics_webview_shim.cpp`: real Bitmap Java pixel-buffer implementation,
  keeping private GraphicsJNI/Skia ABI out of the boundary.
* `libandroid_webview_shim.c`: the fuller native-window lock/post implementation.
  The older pair in webview_bionic_shim.c only returns ENODEV; do not mistake it
  for working CPU rendering or prefer it over the fuller implementation.

[Source paths and hashes](evidence/repair-sources.json) identify the inputs; no
source was changed. Adding a jnigraphics provider and compatibility exports
expands the approved **ANL + GLES2** delivery. An explicit scope question has
been submitted. Until it is answered, do not hide extra providers in the GLES
facade merely to pass this gate. The six prior pass predictions are conditional
and remain unverified; this gate found unsatisfied conditions.

## Reproduce and evidence

Run from the bms-deploy worktree:

```sh
python3 benchmark/2026-09-30-flutter-candidate/audit_engines.py \
  --inputs /Users/zhaoyue/a2hlab/app-inputs \
  --package /Users/zhaoyue/orca/workspaces/westlake-generation-v3c-candidate \
  --pool bms/src/.work/b68-generation/platform-pool \
  --out benchmark/2026-09-30-flutter-candidate/evidence
```

The scanner records strong imports, symbol versions, candidate providers,
DT_NEEDED edges, and input hashes. Physical reachability is an optimistic bound;
namespace ownership still needs the planned runtime experiment. It does not
modify the baseline source, package or devices.

* `evidence/summary.json`: per-engine gate summary.
* `evidence/engines.json`: per-engine import/version records and closure members.
* `evidence/elf-inputs.json`: 305 distinct ELF input identities and NEEDED edges across six graphs.
* `evidence/apk-member-check.json`: original APK and engine-member SHA checks.
* `evidence/all-payload-symbol-crosscheck.json`: whole-payload symbol cross-check.
* `evidence/base-dry-run.json`: existing v3c baseline dry-run passed for 61b,
  **device_io=false**. This is not a candidate dry-run: no candidate exists yet.

No board lock, device I/O, screenshots or process samples. cc-t3 retains priority
for r17s if ready; this rejected preflight consumes no device slot. The expanded source and build outcome are recorded below.

## Approved expansion; two attempts exhausted

Outer approved the private compatibility set after the initial gate rejection.
The implementation inputs are now archived under `src/`, including the original
Westlake Android and jnigraphics files, exact extracted strerror/cmsg functions,
JNI/bitmap headers, and an ANL snapshot with the scoped namespace adaptation.
`evidence/build-source-identities.json` records every source hash and the frozen
clang/sysroot and runtime input hashes. ANL keeps the old path for all domains
except the six approved package path components after a libflutter request.
The planned three private files use unique filenames but Android SONAMEs; the
existing runtime remains a dependency owned by the existing namespace.

| Attempt | Actual outcome |
|---|---|
| 1 | dockbuild stopped before clang: `extra_mounts[@]: unbound variable` when no extra mount was set. |
| 2 | With the worktree explicitly mounted, ANL compiled/linked, Android and bionic objects compiled; private Android provider link failed because the sibling v3c package was not mounted in the container. |

Exact final error:

```text
clang-15: error: no such file or directory: '/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/../westlake-generation-v3c-candidate/payload/android/lib64/liboh_android_runtime.so'
```

The file exists on Mac (SHA9e14bf20); this is a container input visibility error,
not a proven source ABI or unresolved-symbol failure. There was one harmless
`_GNU_SOURCE` redefinition warning before the link command. We counted the
launcher failure as an attempt and stopped at **two** as instructed. No third
compile, package dry-run, lock or device action occurred. The partial ANL is
not safe to deploy without its private providers and has not been packaged.

`retry-build.sh` now supplies both worktree and sibling-package mounts, and
`build.sh` checks the runtime input before invoking clang. This correction is
**prepared, not run**; another build window is required. A completed build must
still pass the import/version closure and package gates before the ≤30-minute
61b control-first sequence. In particular, actual namespace owner lookup,
private SONAME reuse, and OH version matching are not yet runtime-verified.

## Authorized attempt 3: build passed; namespace gate rejected

The corrected mount command completed all four strict links:

| File | SHA prefix | Actual SONAME |
|---|---|---|
| libapp_native_loader.so | 5c63ac49 | libapp_native_loader.so |
| libwestlake_flutter_android.so | 5babd5a4 | libandroid.so |
| libwestlake_flutter_gles2.so | 4b653941 | libGLESv2.so |
| libwestlake_flutter_jnigraphics.so | 3016cf48 | libjnigraphics.so |

`evidence-r3/summary.json`: all six engines now have **zero missing strong
symbol names and zero unresolved NEEDED names** in the optimistic physical
closure. No other runtime/provider was rebuilt. The existing 292/293 non-exact
version matches are explained by the inspected OH6.1 relocation path:
`vinfo.v` starts empty, imported versions set `use_vna_hash`, and an unversioned
provider passes `check_verinfo` while v is empty. A versioned provider instead
checks the requested hash. This source analysis does not prove namespace access.
See `evidence-r3/oh61-loader-rules.txt`; source is the existing local
`bms/src/.work/next4-oh61-dynlink.c` from the earlier OH6.1 investigation.

**The candidate is not deployable.** The independent namespace gate found two
implementation mistakes before any device run:

1. The native-window/native-buffer link inputs declare **libsurface.z.so**.
   The direct owner edge lists their input filenames, omitting this real NEEDED
   name. This would block the Android compatibility provider.
2. OH's `search_dso_by_name` checks `p->shortname`, and load_library derives that
   from the opened filename rather than DT_SONAME. Preloading a private unique
   filename does not make it discoverable under libandroid/GLES2/jnigraphics.
   A private directory with the canonical basenames, searched only by the six
   Flutter domains, is required; open those libraries by basename in that domain.

`check_domain.py` returns nonzero and records exactly the missing owner and
three name mismatches. This supersedes the earlier assumption that preloading
arbitrary filenames with canonical SONAMEs was sufficient.

An **offline-only** package was assembled at
`/Users/zhaoyue/orca/workspaces/westlake-flutter-r3-offline-5c63ac49`.
Its manifest declares all three new files and both ANL aliases; the ordinary
package dry-run passes (`device_io=false`). It carries `rollout_ready=false`
and `DO-NOT-DEPLOY.txt`. Hash/package consistency does not validate loader
semantics. No claim of successful candidate deployment is made.

Proposed correction: retain the three built private libraries byte-for-byte,
place them under a declared `payload/android/lib64/westlake_flutter/` directory
with their canonical basenames, change only the Flutter-domain ANL search/preload
and actual libsurface owner name, and recompile ANL once. Existing flat `--add`
rejects nested destinations; an existing whole-package `--upgrade` can switch
that declared directory and both ANL aliases atomically with other bytes intact.
A further ANL compile would exceed the explicit three-attempt window, so this
correction is pending authorization, not performed. cc-t3 still owns 61b;
there have been no device commands or lock acquisitions.

## Approved r4: canonical private directory

Outer approved one additional ANL-only build. ANL is now 09a9f016; the three r3 compatibility libraries retain their original SHA. The package westlake-generation-flutter-r4 changes only the two ANL aliases and adds three canonical names under android/lib64/westlake_flutter. Six package names are the only trigger. The real libsurface.z.so owner edge is present. evidence-r4/domain-gate.json passes; the old r3 source/package fails the same check. The package and upgrade dry-run pass. Existing known-answer tests: 69 run, 2 skipped, OK.

On 61b we captured the actual JAR as r17p a0ed5c4f, not an assumed r17s. Control inputs originally pointed at the app-only directory; both records failed before launch, with zero screenshot slots. A separate corrected baseline run uses westlake-b90-controls-inputs. Controls use launch-only to preserve ZigZag's five existing native bind mounts; Flutter apps use clean reinstall.


## Device caller gate: the offline check was incomplete

Immich hilog line 47200: caller ns: westlake.sealed.child have no permission,
target is westlake.flutter.21485.3; LocalSend line 28360 reports the same denial.
The following Java error is UnsatisfiedLinkError: Flutter namespace configuration
failed. This is before owner inheritance or facade preloading. The old ANL
uses runtime_gate.namespace_host_ops.create_configured_namespaces/open_namespace
to execute through the default owner. r4 incorrectly called dlns APIs directly
from the sealed provider. The local OH6.1 source checks the caller DSO namespace
against its permitted set; westlake.sealed.child is not one of them.

evidence-r4/caller-gate.json and musl-caller-policy.txt record the missing gate.
Do not use the earlier name/identity-only domain-gate PASS as deployment approval.
A future implementation must preserve the existing default-owner callback flow
for creating/configuring/opening namespaces; no runtime policy relaxation has
been made. The fourth build budget is exhausted.

Use this worktree's scripts/lab/deploy_generation.sh for the tested transaction.
The immutable candidate package still embeds the older deployer; it does not
support absent nested private libraries. The entry-point fix permits only
manifest-declared native additions and still requires resident live-hash members.
Nineteen deployer tests and 69 known-answer tests (2 skipped) pass.

## Final board state and verbatim facts

61b was held from 09:13 to 09:35, then released. No boot or installer change.
The original package 668e4f7c and JAR a0ed5c4f are restored; the rollback gate
verifies SHA, one ART instance and all three added paths absent. Final HW t20
is its own UI. Screenshots were self-reviewed; outer review remains the signoff.

flutter-r4-baseline-fixed-61b

```text
RUNTIME fingerprint=71ccc587850e files=117 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
helloworld           shots 2/2  alive t5=yes t20=yes  child_hilog=5858  foreground_unconfirmed
zigzag               shots 2/2  alive t5=yes t20=yes  child_hilog=12871  foreground_unconfirmed
TOTAL keys=2 screenshots_captured=4/4 alive_t5=2 alive_t20=2
```

- benchmark/2026-09-30-flutter-candidate/device-61b/runs/flutter-r4-baseline-fixed-61b/61b0657200000000000000000324012c/helloworld/t20.jpeg
- benchmark/2026-09-30-flutter-candidate/device-61b/runs/flutter-r4-baseline-fixed-61b/61b0657200000000000000000324012c/zigzag/t20.jpeg
flutter-r4-controls-61b

```text
RUNTIME fingerprint=5f2cfcb18c9e files=117 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
helloworld           shots 2/2  alive t5=yes t20=yes  child_hilog=5864  foreground_unconfirmed
zigzag               shots 2/2  alive t5=yes t20=yes  child_hilog=13554  foreground_unconfirmed
TOTAL keys=2 screenshots_captured=4/4 alive_t5=2 alive_t20=2
```

- benchmark/2026-09-30-flutter-candidate/device-61b/runs/flutter-r4-controls-61b/61b0657200000000000000000324012c/helloworld/t20.jpeg
- benchmark/2026-09-30-flutter-candidate/device-61b/runs/flutter-r4-controls-61b/61b0657200000000000000000324012c/zigzag/t20.jpeg
flutter-r4-first2-61b

```text
RUNTIME fingerprint=5f2cfcb18c9e files=117 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
fd-immich            shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
localsend            shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
TOTAL keys=2 screenshots_captured=4/4 alive_t5=0 alive_t20=0
```

- benchmark/2026-09-30-flutter-candidate/device-61b/runs/flutter-r4-first2-61b/61b0657200000000000000000324012c/fd-immich/t20.jpeg
- benchmark/2026-09-30-flutter-candidate/device-61b/runs/flutter-r4-first2-61b/61b0657200000000000000000324012c/localsend/t20.jpeg
flutter-r4-rest4-61b

```text
RUNTIME fingerprint=5f2cfcb18c9e files=117 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
fd-fluffychat        shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-kitchenowl        shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-libre             shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-saber             shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
TOTAL keys=4 screenshots_captured=8/8 alive_t5=0 alive_t20=0
```

- benchmark/2026-09-30-flutter-candidate/device-61b/runs/flutter-r4-rest4-61b/61b0657200000000000000000324012c/fd-fluffychat/t20.jpeg
- benchmark/2026-09-30-flutter-candidate/device-61b/runs/flutter-r4-rest4-61b/61b0657200000000000000000324012c/fd-kitchenowl/t20.jpeg
- benchmark/2026-09-30-flutter-candidate/device-61b/runs/flutter-r4-rest4-61b/61b0657200000000000000000324012c/fd-libre/t20.jpeg
- benchmark/2026-09-30-flutter-candidate/device-61b/runs/flutter-r4-rest4-61b/61b0657200000000000000000324012c/fd-saber/t20.jpeg
flutter-r4-rollback-61b

```text
RUNTIME fingerprint=71ccc587850e files=117 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
helloworld           shots 2/2  alive t5=yes t20=yes  child_hilog=5863  foreground_unconfirmed
TOTAL keys=1 screenshots_captured=2/2 alive_t5=1 alive_t20=1
```

- benchmark/2026-09-30-flutter-candidate/device-61b/runs/flutter-r4-rollback-61b/61b0657200000000000000000324012c/helloworld/t20.jpeg

The initial incorrectly rooted input attempt was a setup failure before launch, recorded separately in flutter-r4-baseline-61b (0 screenshot slots). Caller-gate failure supersedes the original name-only static pass. No lifecycle spec was assigned to this continuation (board #90 spec=null).
