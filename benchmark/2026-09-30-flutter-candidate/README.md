# Flutter candidate: pre-build closure gate rejected

The approved two-file proposal (ANL plus a private GLES2 facade) does not yet
satisfy the six engines' strong-import closure. The initial two-board logs
reported the first missing name, not all load requirements. At that initial gate no build was attempted. The later approved expansion and
two stopped build attempts are recorded below; nothing was deployed.

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
