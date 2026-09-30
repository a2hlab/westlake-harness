# N1: one native cluster candidate on U0

The previous Flutter iterations confused a complete filesystem dependency list
with a reachable namespace owner. The host only installed app → bridge; OH musl
stops inheritance after one hop. JNA's last resource error was also misleading:
both original APKs contain libjnidispatch, and their earlier failure is
`__errno@LIBC` relocation. The candidate attempts to correct these boundaries,
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

## Cache correction before the complete batch

The initial runtime-only discriminator d40ae63f used an existing cached AudioSystemCapabilities object. Its three capability methods were present, but newAudioSessionId was absent despite the candidate source containing it. The authenticated cache restorer now invalidates all five changed translation units regardless of timestamp. The complete candidate runtime is 77639b80; the deployed d40 discriminator remains immutable and is not evidence for newAudioSessionId. FZ-003 source is unchanged.

## First device discriminator (61b, same boot and r17r)

Only `/system/android/lib64/liboh_android_runtime.so` changed: 53f00423 to d40ae63f (`device-61b/compare-runtime.txt`, variables: 1). HelloWorld and ZigZag t20 showed their own interfaces. NewPipe retained its live-page UI (network-error controls rendered); uhabits changed from exited/desktop to alive/white, which is not lighting. AntennaPod rendered its welcome/home UI. Fitness returned to the desktop after RenderThread SIGSEGV at 0x590, top frame OH Skia StrikeCache::generateStrike+156. The complete 11-file candidate was withheld and the discriminator rolled back. U0 exact declared SHAs, r17r SHA and boot identity were read back successfully; a clean U0 Fitness repeat is used to distinguish a pre-existing intermittent failure from a candidate regression.

All three U0 Fitness clean repeats rendered its own workout/setup screen at t20. Each comparison with the failing discriminator reports variables: 1. There was only one failing candidate trial; this is a reproducible U0 recovery and a control concern, not a claim of deterministic causality. At the end of round one, the full N1 acceptance gate remained closed; the authorized three-repeat decision and complete N1 run are recorded below.

## Round-one window closure (historical)

61b was restored to U0 and unlocked before the 45-minute limit. The final readback covers every declared live SHA, r17r overlay and unchanged boot; recovery HelloWorld/ZigZag t20 show their own interfaces. Exact per-run facts are in facts-all.txt, review paths in device-index.json, and final identity in device-61b/final-identity.json. No other board was written. Complete-N1 device verification was deliberately false; this state is preserved in device-verdicts-r1.json and lifecycle-r1.json rather than overwritten as a successful run.

Lifecycle: lint quality 1.0; frozen, cluster dispositions, host closure/negative, and rollback/handoff pass. The complete device/control scenario fails intentionally because the full candidate was withheld. This is not a successful N1 acceptance. Known-answer suite: 69 tests, 2 skipped. Raw process-table headers retain their captured trailing spaces; source-code whitespace checks pass.


## Round two: outer-authorized Fitness gate and complete N1

The single d40 Fitness crash was insufficient to label a deterministic regression.
The outer loop authorized three clean same-board repeats, with >=2/3 own workout
pages required before expanding to the complete candidate. All three repeats
rendered the own workout/setup page. Each comparison against the earlier failed
d40 run reports zero runtime variables. This satisfies the outer loop's
intermittent-Skia exception; it is not independent proof of the glyph-cache root
cause. See device-61b-r2/fitness-gate.json and fitness3-t20.jpeg.

The complete immutable aa57845c package was then deployed, retaining r17r and the
installer. Its deployment smoke passed SHA, child-root maps, single ART and
bridge identity. The full-package HW/ZZ screenshots and five protections
(Aegis, Auxio, Droid-ify, NetGuard, NewPipe) retain their own interfaces.
The thirteen targets are separate from those seven controls. White windows and
SPD's explicit cannot-start error page are not counted as working app screens.

Attribution has an instrumentation limit: compare_runs reports eight changed
paths, while package-changes.json declares eleven. Master's fingerprint glob
omits the three private westlake_flutter/*.so files. They were independently
read back through the child's root and match the package. See
`device-61b-r2/fingerprint-coverage.json`. No individual N1 component gets sole causal credit
from this eleven-file batch.

Read device-61b-r2/first-fatal-summary.json for exact log lines, visual-review.json
for screenshot interpretation, maps-summary.json for sampled process mappings,
and facts-r2.txt for unchanged master facts output. This round performs no
new native build and no U1 full sweep. Remaining API failures must stay in the
original eleven-row prediction denominator.


### N1 target outcomes (self-read, outer review pending)

| Targets | t20 | First observed blocking checkpoint |
| --- | --- | --- |
| LocalSend, FluffyChat, KitchenOwl | Launcher | Flutter private libandroid cannot resolve liboh_android_runtime.so |
| Immich, Libre, Saber | Launcher | libflutter relocation: __system_property_get not found |
| Firefox, Fennec | Launcher | libjnidispatch relocation: __errno@LIBC not found; com.sun.jna.Native initialization then fails |
| OpenCamera | Launcher | SoundPool reaches OH_AVPlayer_Create twice; next fatal Camera._getCameraInfo JNI missing |
| VLC | Launcher | libc++_shared relocation: android_set_abort_message absent; onboarding then fails theme attribute resolution at index 13 |
| SPD | Own cannot-start error page | GLImpl._nativeClassInit missing, an explicitly unimplemented row |
| uhabits, Noice | White app window | EGLSurface created; no main-thread fatal in captured log. uhabits has a caught/background AppWidgetManager NPE |

VLC's newAudioSessionId is registered; actual playback is unverified. Neither
JNA sample maps the new ABI DSO. None of the sampled Flutter processes maps a
completed libflutter load. These are time-sampled observations, not proof of the
entire loading history. All captured samples contain one ART path; Libre,
Saber and LocalSend exited between samples and have no maps evidence.

The seven control/protection screenshots retain their own interfaces, but no
new target has a normal working UI. N1 is an experimentally evaluated partial
candidate, not a unified signed generation. N03/Flutter predictions failed
live despite their filesystem-level static gates; the next namespace gate must
exercise the exact loader path and owner, not just match exported names.

61b was restored and unlocked at 2026-09-30T12:00:49.606801+08:00. The complete window was 2238.6 seconds (37m18.6s), within 45 minutes. All 30 declared U0/JAR SHA paths match, and boot ID is unchanged; see final-identity.json and rollback-state.json under device-61b-r2.

Current lifecycle: four pass and one pendingreview (device screenshots); zero failed. The known-answer suite ran 69 tests with two skips. Representative maps listed in device-61b-r2/maps-evidence-files.txt are committed; other raw samples/hilog remain at the recorded local paths with excerpt hashes.
