# N3b: explicit WebView publication in one runtime replacement

A non-null webviewupdate Binder was mistaken for WebView availability. The real
U3 framework first rejects `isWebViewSupported()==false`; merely adding native
symbols or claiming a feature would not supply a Chromium provider. N3b supplies
the validated native publication half and a precise Java/provider contract.
**No device has run this candidate.** Effects/screenshots/facts are unknown.

Package: `/Users/zhaoyue/orca/workspaces/westlake-generation-n3b-53bb18d1`

- Base manifest: `8a7880fa207a4e13e6d0cb86140d0345dcd1f377a0eebcab8d633a323e9b9a24` (immutable N3 8a7880fa).
- Candidate manifest: `53bb18d1743a69bee9be98b4704afc5e684f57c002687fc2771678c2edd575d3`.
- Runtime: `7c9c6240c7bbaa529460d7acb8e12629e3c9f9151b390a071f1d10a0bd727042` (7c9c6240).
- Exactly one declared path changes: `/system/android/lib64/liboh_android_runtime.so`.
- JAR/APK/ART/boot/bridge/host/child/ANL/provider/installer remain original bytes.
- `rollout_ready=false`; Java integration, actual provider inputs and board review
  are still required. This package by itself does not unlock Tutanota.

## Source and lifecycle

Six complete functions copied byte-identically from Westlake
`532633da63b770d3d459c74683db6d7a1f82a022`,
`framework/activity/jni/activity_task_manager_adapter.cpp`: jstr, exception log,
feature cache setter, shared prime/publish implementation and two public entries.
`source-origins.json` gives exact original lines and function hashes. The full
pinned file is archived in N3's offline-followup source snapshot.

The donor requires real provider availability, identity-preserving ServiceManager
cache/public readbacks, and a current Application before returning publication success. An
early prime holds feature false; late prime preserves a successfully published
capability. Provider instance and framework verification stay untouched.

N3b adds only includes and two serialized JNI wrappers, named for
`adapter.core.WestlakeWebViewInstall`, `nativePrime()Z` and
`nativePublishAfterBind()Z`. Explicit Java checkpoints replace the old bridge's
log-trigger/watch thread because that bridge implementation is absent from our
pinned runtime. No background thread, logger hook, app-specific provider rewrite,
new preload or automatic JNI registration is introduced. Existing apps do not
call these entries until the paired Java helper is supplied.

`JAVA-HANDOFF.md` tells cc-t3 exactly where to load/call the helper, how to retain
real PM/provider metadata and which payload/namespace/data-directory inputs are
still missing. Test doubles in test_host.py are never production Java input.

## Minimal reproducible build

The restored dockbuild environment succeeded on the first source/link round.
`build.py` authenticates/copies the 61 N3 runtime objects into a separate directory,
relocates the recorded N3 recipe, and first relinks unchanged inputs. Output is
bit-identical to N3 `2cf33c15`. It then compiles **one** additional TU and relinks in
the same order. Every original object still matches its SHA. The inherited EGL/GL
inputs and library flags are preserved by the original recipe; no unrelated recompilation.
The frozen clang/sysroot hashes are in toolchain-identities.json. N3 original
source/build provenance remains in `../2026-09-30-n3-native/`.

```sh
"$WORKSPACES/westlake-inputs/tools/dockbuild.sh" run -n n3b-webview -- "cd $PWD && python3 benchmark/2026-09-30-n3b-webview/build.py"
python3 benchmark/2026-09-30-n3b-webview/prepare.py
```

Do not overwrite an exported hash-named package. prepare.py rejects an existing
staging/output path. It uses the repository single-file replacement preparer;
the export contains the original deployment/rollback tools and complete base.

## Validation and limits

Host JNI tests execute compiled donor C++ on a real JVM with typed Android API
doubles under -Xcheck:jni: missing class/provider, provider exception/null instance,
missing/throwing Application, wrong/throwing public cache, failing cache insertion,
happy path, late prime and concurrent calls (12 cases). All pass without JNI warnings.
No claim is made that host mocks prove OH ART class-loader or Chromium behavior.

ELF audit: no removed exports, four new explicit entry symbols plus one weak inline JNI helper, identical NEEDED
order/SONAME, no RPATH/RUNPATH/TEXTREL. Package validator sees one changed path;
corrupt-runtime negative is rejected. Four recursive_mutex imports resolve in the archived OH6.1 chipset-sdk-sp/libc++.so selected by DT_NEEDED (new-import-supply.json). The differently named libc++_shared.so lacks them and is rejected as a substitute. The canonical library is an external system input, not package payload; current board identity was not reread while offline. Frozen sources/provider pass. Dry-run
records device_io=false. The contract has two automated scenarios and one human
handoff review; deployment remains blocked on its integration checklist.

## Scheduled deployment only

These commands are reviewable instructions, not actions performed this round.
Before any future board operation, obtain its scheduled lock and confirm the
active package is the signed N3 base; a U3/N2 board is **not** a direct replacement
base. Preserve/reapply the approved JAR receipt through the existing deployment
procedure; this round does not authorize temporarily dropping J3.

```sh
PKG="/Users/zhaoyue/orca/workspaces/westlake-generation-n3b-53bb18d1"
python3 scripts/lab/deploy_generation.py "$SERIAL" "$PKG" --replace /system/android/lib64/liboh_android_runtime.so --dry-run
# Only after prerequisites, board scheduling and paired Java/provider review:
python3 scripts/lab/deploy_generation.py "$SERIAL" "$PKG" --replace /system/android/lib64/liboh_android_runtime.so --lane cx-t0
python3 scripts/lab/deploy_generation.py "$SERIAL" "$PKG" --replace /system/android/lib64/liboh_android_runtime.so --rollback --lane cx-t0
```

Verify single ART/maps/SHA and HW/ZZ before Tutanota. With no provider the feature
must stay unavailable; with the real provider require public Binder identity,
post-bind feature publication, real native provider initialization and a t20
screenshot. Any control regression rolls back. Counts remain **unknown** here.

## Retained donor failure behavior

The whole-function copy is not an atomic cache/feature transaction. In the
`lookup-wrong` negative, an available provider and ready Application let the
feature field become true, while the failed public-cache identity makes the
function return **false**. The raw log therefore contains both `feature=published`
and `startup service cache failed`. This upstream behavior is preserved, not
silently fixed. Java integration must check the native boolean and both readbacks;
the feature log alone is not acceptance. Never continue provider startup after a
false return. Device failure semantics remain a review point before rollout.
