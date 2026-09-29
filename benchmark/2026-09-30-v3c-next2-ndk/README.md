# v3c-next2: OH NDK dependency visibility

The rejected b66f1b60 ANL added runtime dependency lookup but omitted
`/system/lib64/ndk`. On both boards, Unity aborted because `libandroid.so`
needs `libhitrace_ndk.z.so`. Keeping r17m fixed and rolling back only the
native bundle restored ZigZag; see `../2026-09-30-v3c-next-rollout/`.

This change extends the existing B87 namespace setup with the fixed OH6.1
NDK directory in dependency search/permitted paths and eight explicit shared
SONAMEs. It preserves the original direct app path checks, v2 permitted-path
support, B92 thread behavior, version script, host/child/provider, and all
other package bytes. No board was accessed or written during this task.

## Evidence and implementation

Inputs were found locally, without downloading or querying devices:

- Exact next package `payload/android/lib64/libandroid.so` and
  `payload/zigzag/libtuanjie.so`.
- Retained OH6.1 `bms/src/.work/b68-generation/platform-pool/system/`.
- Existing native-loader policy uses `/system/android/lib64` and
  `/system/lib64/platformsdk`; B87 adds `chipset-sdk-sp`.
- Source baseline: commit `512b1724`,
  `bms/src/adapter/framework/app-native-loader/src/app_native_loader.c`.
  `anl-source.patch` is the complete additional change.

`audit_needed.py` walks the complete NEEDED lists of `libandroid.so` and
`libtuanjie.so`, plus the specifically requested OH hilog/ace NDK entry points.
`needed-closure.json` records **310 resolved ELF names**, hashes, source paths,
SONAMEs and every dependency edge. The resulting public NDK names are:

```
libhitrace_ndk.z.so libhilog_ndk.z.so libace_ndk.z.so libffrt.so
libpixelmap.so libpixelmap_ndk.z.so libsync_fence.z.so libudmf.so
```

These are added to the explicit bridge/app shared list alongside B87's existing
liblog dependencies. The fixed NDK root is validated on OH before namespace
creation. Direct `ANL_Dlopen` continues to validate the original app paths;
the change supplies native dependencies, not arbitrary app-provided directories.

The inventory has two unresolved **independent file names**, `libm.so` and
`libdl.so`, in the unchanged Unity/main input. They are retained explicitly as
static limitations, not silently counted as resolved. The preceding v3c board
runs loaded the same Unity files successfully. This offline gate checks NDK
policy coverage; it does not claim to emulate musl's runtime alias handling or
resolve every dynamic load. In particular, presence in a search list does not
prove that all nested OH namespaces will load successfully on-device.

## Build and gates

- OH6.1 clang: `b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913`.
- ANL two-pass byte identity:
  `1162a6fc34c283d9bbe3fdf6f2b85619d5744f68966b8850d218e7444c582144`.
- Strict link keeps `--version-script`, `--no-undefined`, `-z defs/now/relro`.
- NEEDED order, SONAME, imported and exported symbol sets match b66f1b60.
- The unchanged upstream host suite passes **142 checks, zero failures**,
  including foreign-path rejection, bootstrap failures and domain boundaries.
  It runs on Mac with `run_host_tests.sh`; the frozen Linux container lacks rg,
  and glibc mock warnings prevent its unmodified Werror runner from compiling.
  Those failed invocations are retained; no diagnostic was disabled and no
  production check was relaxed. OH-only directory existence remains board-pending.
- `check_ndk_coverage.py` derives required names from the ELF graph. Next2 passes;
  the exact rejected b66 artifact is the negative control and misses all eight
  names and the NDK root. This supplements the mock suite, which alone missed
  the original runtime dependency error.
- Repository known answers: 69 tests, two skips, pass.
- All three deployer dry-runs pass: 281 declared files, `device_io=false`.

## Package and handoff

Complete candidate:
`/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-next2-audio-anl`.
Manifest SHA:
`61cecc5a93b83f19a2f944b47ea53912b5e105d35c8c01b770f02c947321dcc2`.
Both ANL route/Android aliases are 1162a6fc; AudioSystem runtime remains f87dcdf9.
`package-changes.json` proves exactly two changed payload members relative to next.
The manifest updates both aliases; no executable identity gate is introduced.

Use the revised worktree deployer, exposing package r8b only after taking the
assigned lock and preserving the current external JAR receipt. Keep that JAR
constant for the comparison. The alias pair requires the existing transaction:

```sh
scripts/lab/deploy_generation.sh SERIAL /Users/zhaoyue/orca/workspaces/westlake-generation-v3c-next2-audio-anl --upgrade --lane LANE
# If controls regress, expose package r8b and undo precisely this transaction:
scripts/lab/deploy_generation.sh SERIAL /Users/zhaoyue/orca/workspaces/westlake-generation-v3c-next2-audio-anl --rollback --lane LANE
```

Next2 does not include EGL a578 or the new installer. A board with additional
native overlays must merge those explicitly before deploying a complete package.
Outer scheduling owns deployment. HW/ZigZag/Auxio/NetGuard and the original
Anki/VLC improvements still require device evidence. R2: **host verified,
device unverified**; next2 is an offline candidate, not a signed baseline.

Source, headers, exact patch, build recipe and toolchain provenance are archived
at the persistent path and SHA in `archive.json`; remote SHA was read back.
Frozen toolchain/sysroot inputs reuse the recorded B87 archive. No push occurred.
