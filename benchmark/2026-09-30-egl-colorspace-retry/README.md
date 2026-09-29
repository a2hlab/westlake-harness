# B11 EGL colorspace retry: OH6.1 source rebuild candidate

**Offline candidate, not a Wikipedia success.** The VM `out.75d82d5`
`libhwui=a11c9154` is a different AOSP15 build with imported EGL entry points;
its link log is empty. It cannot supply the resident R155 `be59260f` rebuild.
The retained R139 build was incomplete. We instead rebuilt all **154 objects**
from the available AOSP14 source recipe, using OH6.1 inputs. No OH7 object was
reused and no existing ELF was patched.

## Artifact and limits

- Baseline: `be59260f93b3debe1ad64cc8e7b6b0575e5be04794b46f8eb876436d1ebc9b74`.
- Candidate: `a578b94933cfac4a8fa79116abf145435248df7bce315b9c8eedf41eccb793c6`,
  2,769,072 bytes, `eglCreateWindowSurface` remains a defined strong symbol.
- Single-file package: `/Users/zhaoyue/orca/workspaces/westlake-b11-egl-a578b949`.
  Parent is the active 5ea v3c package `668e4f7c`, checked against the deployment
  state for boot `51812b02-ec64-4d36-821c-ffd94531fb45`.
- Only `/system/android/lib64/libhwui.so` changes. JAR, host, ART, bridge,
  installer and provider are unchanged by this package.
- **This is a source rebuild, not a byte-equivalent R155 library with just one
  function changed.** ImageDecoder/BitmapFactory stream paths, rendering probes
  and the existing EGL owner/destroy wrapper also differ from R155.
  `static-diff.json` records 4,419 normalized-equal records, 1,177 modified,
  14 added and 23 removed; normalization includes conservative address noise,
  so these numbers are not counts of semantic fixes.
- Thirteen removed exported helpers have **no UND consumer in 91 package
  libraries**. This does not prove that no external or string-based consumer
  exists, nor establish rendering equivalence. Controls and rollback are required.

## EGL change

Start from oc-t4 `e9ee5599` in
`bms/src/adapter/aosp_patches/libs/hwui/hwui_oh_abi_patch.cpp`, section 4.
After a failed `eglCreateWindowSurface`, remove color metadata attribute/value
pairs and retry once. Preserve the existing OH window unwrapping. Log the first
and second `eglGetError` values under `OH_EglHijack`.

Two compile declarations were missing in that revision: EGL_NONE and the C
`eglGetError` declaration. Attribute keys were corrected using the frozen OH
`EGL/eglext.h`: 0x309D, SMPTE2086 0x3341–0x334A, CTA861_3 0x3360/0x3361.
Colorspace *values* (PQ/HLG/LINEAR) are not keys and are not separately filtered.
No arbitrary old live surface is destroyed to force a new one. The reported
same-window duplicate-create sequence remains a hypothesis until actual error
codes and ownership are observed on the board.

`test_retry.py` compiles and executes the production retry block with five
mock EGL cases: first success, successful filtered retry, failed retry, null
attributes, and an empty filtered list. It verifies unrelated attributes survive.
All pass. Modified object SHA is `c8dc9196f6c084330e25cd4298de3ee64ac2ad849831bad6b3688f95a87b9382`.

## Rebuild provenance

The available source recipe and dependencies came from the historical build
`hw248:/opt/build-runs/cts-getpackageinfo-oh7-20260915/t001b-hwui-oh7/`:
`base-full` is the patched **AOSP14** HWUI source, `aosp-deps` supplies minikin,
harfbuzz and freetype headers, and `public-headers` supplies Android public
headers. The archive name identifies its former deployment target; its old
objects and OH7 link inputs were excluded from this rebuild.

Additional source: `hw248:/opt/build-trees/aosp14/`. The local OH6.1 header view
is `bms/src/.work/b68-generation/oh`; the toolchain is frozen OH6.1 clang
`b107ce03`, with the existing libc++ compatibility wrapper. All source roots
are included or referenced by hash in the preservation manifest.

`rebuild-recipe.sh` is the historical full recipe with local input relocation,
explicit libc++ headers, Android GLES headers, and the device-exact link input
folder. Compile source groups reported **39 + 50 + 1 + 62 successes, zero
failures**, plus two adapter objects. The unrelated repository RenderNodeDrawable
probe references missing `OpInspectCanvas.h`; it was not used. The reference
source's original RenderNodeDrawable was compiled instead.

Strict linking initially exposed two input-selection problems, both corrected:
SDK EGL stubs lack extension exports; current liblog's bionic stdio exports
would add a new liblog NEEDED edge. Link against the exact OH EGL/GLES libraries,
and omit the unnecessary explicit `-llog`, preserving the baseline contract.
All **15 NEEDED entries and order match R155**. The two new imports resolve in
exact-board Skia (`FrontBufferedStream::Make`) and musl (`fmodf`). Board SHA
readbacks for EGL/GLES/Skia/libc++/musl are recorded; these were read-only calls.
The historical whitelist warns about fmodf; its provider is explicitly checked,
not assumed. The changed TU was recompiled and relinked twice, byte-identically.

## Handoff

Use the current worktree deployer (or `westlake-v3c-deployer-5fa85f77`), not the
old embedded handoff copy. The current owner of 5ea must keep its lock and use
its lane name. Expose package r8b only for the deployer checks, then restore the
chosen r17j/r17k overlay and record its SHA as a separate variable.

```sh
scripts/lab/deploy_generation.sh 5ea34a4500000000000000001123012c /Users/zhaoyue/orca/workspaces/westlake-b11-egl-a578b949 --replace /system/android/lib64/libhwui.so --lane OWNER
# On any regression:
scripts/lab/deploy_generation.sh 5ea34a4500000000000000001123012c /Users/zhaoyue/orca/workspaces/westlake-b11-egl-a578b949 --replace /system/android/lib64/libhwui.so --rollback --lane OWNER
```

Dry-run passed, 281 declared files, no device writes. First HW/ZigZag controls,
then Wikipedia with master batch 16M preflight, t5/t20 shots and focus checks.
Capture both EGL errors, window/surface pointers and process maps. If retry
fails, keep the exact errors; do not infer BAD_ALLOC solely from pointer reuse.
An image of the welcome page must be read by the outer reviewer. If controls
or JNI/image decoding regress, roll this file back to `be59260f` immediately.
Facts/screenshots/device rollback are pending. R2: **partially**.

B11 lifecycle: all four scenarios **Skip** because each selector matched zero
tests. This is not acceptance evidence. Board screenshots, reference-log review
and regression rollback remain with the Wikipedia lane/outer reviewer.

## Preserved replay inputs

`source-preservation.json` pins the 191 MiB source/object/link-input archive
in `/home/alvin/westlake-oh6.1-b11-egl-a578b949/`, verified after upload. Reuse
the frozen toolchain recorded in the B87 archive. Restore at the recorded
worktree root and keep the B68 OH platform view (or recreate its platform library
paths from the archived `link-inputs`). Then run:

```sh
DOCKBUILD_MOUNTS=/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-candidate \
  /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/dockbuild.sh run -n b11-replay -- \
  bash benchmark/2026-09-30-egl-colorspace-retry/build-probe.sh --clean --phase=1,2a,3,4 --strict-audit
```

The deliverable is `oh61-rebuild-adapter/out/hwui-build/libhwui.strict.so`;
the historical script's final `out/aosp_lib64/libhwui.so` banner is a stale
reference and is **not** the candidate output.
