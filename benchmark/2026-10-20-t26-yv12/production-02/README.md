# T26 + T27 joint offline production

The former R14 success formats exclude player YV12. This successor exposes a bounded YVU scratch buffer only after an admitted YV12 request and converts it to real OH12 / Android RGBA8888 before the original Unmap/Flush. Unknown history and other RGB requests retain the original path.

Production-02 compiled ten translation units with `_GNU_SOURCE=1` and `WL_T27_OBSERVER`. T25 baseline reproduced byte-for-byte. The 78 versioned exports, sole libc dependency, no TEXTREL and both exact consumer ABI checks passed. This is an offline candidate, not device or playback approval.

[receipt.json](receipt.json), [results.json](results.json), [source-index.json](source-index.json), [toolchain-and-dependencies.json](toolchain-and-dependencies.json), [raw-index.json](raw-index.json) bind actual files. Original argv/stdout/stderr/rc remain in `$T26/.private/production-02`; the first parser failure remains in `production-01`. A full source/header snapshot is in `production-02/full-source-snapshot`. Public receipt paths use aliases; their original bytes and SHA are indexed. No historical log is replaced by this new build.

`$T26` is this benchmark directory; `$REPO` its repository; `$MAIN` the main checkout; `$CC_VIDEO` the frozen observer checkout; `$VIDEO_PLAN` the original T23 producer checkout; `$WESTLAKE_INPUTS` the sibling input repository; `$ORB_WS` the existing Orb workspace; `$HOME` the runtime user's home. SDK paths remain the actual non-personal DevEco installation.

Import metadata is observed after the original provider mutex is released, while the RESERVED slot exclusively owns the new buffer. CPU and import getters require the retained handle and exact same libsurface base. The old one-argument non-underscored conversion is distinct from the SDK's two-argument underscored conversion. Missing or foreign getters remain UNKNOWN. Actual EGL create is forwarded once without consuming EGL error state.

The peer's unchanged original T23 fixture exercised all 14 actual derived R23 entry cases; [receipt and input hashes](r23-peer-receipt.json) are separately bound to the original receipt SHA. Host evidence does not prove on-device getter identity or successful import.
