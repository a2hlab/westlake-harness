# WMC baseline build receipts — outer baseline 01

The first successful link was **not a source rebuild**: it reused the original object set and reproduced bridge SHA `b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4`. The later Linux compile rebuilt the WMC translation unit, and a subsequent Mac link substituted that newly compiled object. These are separate evidence levels.

| Run | Actual result | Meaning |
| --- | --- | --- |
| mac-original-link-01 | rc0, bridge b0e5602a…, 2,023,136 bytes | Original-object relink; receipt reports 111 input pins checked. |
| linux-original-compile-01 | rc1, no output SHA | `<memory>` missing at WMC header line 23; stderr lines 2–6 retained by reference. |
| linux-original-compile-02 | rc0, object f91b354f…, 323,192 bytes | WMC source rebuilt exactly after adding 792 fixed SDK C++ system headers. |
| mac-recompiled-link-01 | rc0, bridge b0e5602a…, 2,023,136 bytes | Rebuilt WMC object replaces its original counterpart; other objects remain reused. |

The exact WMC object SHA is `f91b354ffa408fed7ff3002e1ed24a786b65621fd9b985c37db9b0fab461b8ed`. This lane independently rehashed all three successful output files and the original WMC object, and checked all 792 header hashes at both their source and destination (1,584 matches, zero mismatches). Source identity and full hashes are in `results.json`.

## Reproduction delta

The initial staging, as reported by the outer lane, contained the `-MMD` dependency closure but omitted system headers. The original argv and missing-`memory` diagnostic support the failure; this review did not observe the historical directory before the copy. The correction materialized the complete fixed SDK `native/llvm/include/libcxx-ohos/include/c++/v1` inventory at the original `toolchains/clang-15/include/libcxx-ohos/include/c++/v1` search location. The 792-entry raw inventory, source/destination paths and SHA are indexed. No compiler flag was changed between compile-01 and compile-02: only dependency-output and object-output names differ (argv indices 380 and 384). Compile-02 retains one `LOG_TAG` redefinition warning.

The subsequent link changes only the WMC object argument (index 53) and output path (index 123). Thus the observed closure is **one WMC source translation unit → exact original object → exact baseline bridge using the remaining original objects**, not a full bridge source rebuild.

`commands.sanitized.json` contains the complete recorded argv arrays, terminal receipts, transport/environment records and short diagnostics, with explicit `$STAGE`, `$RAW`, `$HOME` and `$VM_HOME` aliases. These are archival records, not executed commands in this task. `raw-index.json` pins the original argv/stdout/stderr/receipt files beneath `$HOME/.local/share/westlake/wmc-baseline-build-20261024/`; originals are unchanged, including compile-01 failure. The existing staging/SDK artifacts are still required for a future replay; this small receipt increment does not embed binaries or the full SDK.

This lane performed local reads and hashes only: no compilation, VM/remote command, device action or t1 modification. Byte equivalence is not runtime recovery, a deployment approval, or evidence of restored feed rendering. No Git reference writes or push were attempted.
