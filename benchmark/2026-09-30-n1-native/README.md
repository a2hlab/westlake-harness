# N1: one native cluster candidate on U0

The previous Flutter iterations confused a complete filesystem dependency list
with a reachable namespace owner. The host only installed app → bridge; OH musl
stops inheritance after one hop. JNA's last resource error was also misleading:
both original APKs contain libjnidispatch, and their earlier failure is
`__errno@LIBC` relocation. The candidate corrects these specific boundaries,
retains frozen asset FD behavior, and combines the previously tested graphics
and audio registrations. It is **not a signed runtime** until device review.

The frozen round-one plan retains all **11 N1 rows**. See dispositions.json:
N07 GLImpl/GLES1 and N09 Bitmap color space are not implemented; N08 requires a
Java WebView provider boundary; N03 is partial. These remain delivery gaps in
the original prediction denominator, not successful fixes.

## Copied implementation and provenance

- Exact historical repository: `/Users/zhaoyue/orca/workspaces/vm-copies/westlake-current`.
  Commit `02cbace7fbe8e72acb356817bb93a9c6bad3baa9` is present here. The separately
  named `/Users/zhaoyue/orca/westlake` checkout and VM Westlake HEAD 22b94532 do
  not contain that object. Historical source blobs are in source-evidence with
  original paths/commits/SHA in historical-source.json.
- Graphics: retain the accepted 32df explicit SC identity mapping and complete
  BLAST JNI block copied from Westlake `22b945321929987c86b35cd99f9f2d2f4283e82e`.
  The 02cbace SC uses a relayout thread-local written by its window bridge, with
  an older global fallback. R155's bridge does not call that setter. Copying that
  fallback would restore the observed wrong-session bug; 32df's explicit name/
  parent mapping preserves per-window identity without rebuilding bridge 846.
  No forced EGL destruction is added. The 02cbace window/SC sources are saved
  for this comparison; same-window rendering still needs actual screenshots.
- Flutter: existing private libandroid/bitmap/bionic functions are copied from
  Westlake `532633da63b770d3d459c74683db6d7a1f82a022`, whose LocalSend engine-loading
  evidence is recorded by harness commit a3640061. Its WebView redirect precedes
  the plain-name fallback (02c173bf), and GLES2 uses the OH GLES3 implementation.
  These are complete facade source files, not fabricated missing-symbol stubs.
- Namespace mechanism: VM `/home/zhaoyue/a2hlab/ws/art-build/stubs/link_stubs_arm64.cc`,
  SHA `3f7e87a93a1707ad6039c7a676916d045276b4a2aa758f84eed1ce8d7acc98ab`, uses
  exact-name selection, direct parent inheritance and an ABI preload ahead of
  Android native libraries. This file is outside the Westlake git checkout;
  it is identified by SHA, not falsely assigned to the adjacent repository commit.
  The existing host callback adaptation is necessary because sealed ANL cannot
  call dlns APIs directly. User approval limits new host edges to the six Flutter
  packages' private namespace. Non-Flutter host behavior and d977 INET remain.
- JNA/bionic: existing __errno implementation plus atfork/FD checks copied from
  Westlake 532633da. A separate versioned ABI DSO is preloaded only for the 11
  listed native-cluster packages. Its DF_1_GLOBAL exposes the preload to subsequent
  app loads while retaining the existing callback's RTLD_LOCAL invocation.
  This is an explicit candidate behavior, not proven live symbol visibility.
- SoundPool: entire 02cbace `framework/core/jni/oh_soundpool_jni.c`, using OH
  AVPlayer on its dedicated worker thread. All required OH exports are present.
  NativeLoader adds only the declared canonical libsoundpool path; its public
  exports and three NEEDED entries match U0. No ART/provider or JAR rebuild.
- Audio capabilities: existing AudioSystemCapabilities source, including the
  Westlake AudioProductStrategy empty-list fallback and newAudioSessionId=0
  allocation sentinel. This does not claim real audio playback.

## Frozen and build inputs

FZ-003 is compiled directly from its original source file (blob e47ede07),
without editing it. FZ-002 provider remains 0509fe23 on both aliases; installer
FZ-001 is untouched. All builds run check_frozen; publication runs it on the
package and source root. Runtime starts from the verified 59 B91 objects and
recompiles only graphics, registration, audio capabilities and the frozen asset
TU. The B87/B68 persistent source and toolchain archives referenced by prior
reports supply unchanged inputs. source-sha256.json pins this candidate's sources.
Build scripts use dockbuild and preserve complete commands. Local binary output
is bms/src/.work/n1-native; package preparation is reproducible via prepare.py.

## Offline checks and limits

- Runtime, host, ANL/private ABI, SoundPool and NativeLoader strict links passed.
- Actual host callback recorder validates two direct owner edges, six-package
  path selection, unchanged non-Flutter paths, and failed owner lookup. Original
  host is the negative control and is rejected.
- Baseline NativeLoader suite: 74 checks, zero failures. Baseline ANL suite with
  its strict-mode configuration: 136 checks, zero failures. The tracked newer
  next-series suite expects broad OH dependency expansion and fails three such
  expectations, intentionally absent from N1. Historical strict-gate tests also
  fail under the already-approved log-and-allow default; the strict-mode result
  is reported separately, not as a test of that default behavior.
- Six engine filesystem closures: no missing strong symbol or NEEDED name.
  292/293 Android version tags resolve against unversioned musl exports under
  the previously inspected OH loader rules; exact GNU version equality is not
  claimed. Namespace reachability, ABI preload order and no duplicate runtime/
  DFX require device maps and logs.
- Package dry-run/frozen checks passed without device writes. New files are
  declared and rollback uses the deployed preflight's absent/present records.

## Controlled experiment

Use the assigned board after held confirms the lock. Capture U0 package/JAR
receipt and keep r17r and installer unchanged. First test runtime alone against
same-boot clean NewPipe/uhabits baseline (compare_runs must report one path),
with HW/ZigZag and AntennaPod/Fitness controls. Then evaluate the complete N1
native batch; report every changed path, never call the multi-library batch a
single-cause result. Control regression stops expansion and rolls back.

Capture t5/t20 with master batch preflight and clean installation. Check actual
libflutter/JNA mappings, one ART/runtime/DFX, inherited libsurface owner, and
SoundPool registration/backend logs. Report exact facts and first fatal, hand
screenshots to outer. Short-window completion rolls back to U0 and releases the
board; only outer acceptance can promote this candidate into U1 sharded sweep.
