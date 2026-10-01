spec: project
name: "Reproducible build chain for liboh_adapter_bridge.so 84695d62"
---
## Intent
The deployed adapter bridge (liboh_adapter_bridge.so, sha256 84695d62…, 2.27 MB, .symtab kept, built with OHOS clang 15.0.4 llvm 99548401bd80 / LLD 15.0.4 from OH SDK 6.1.0) has no reproducible source/patch/toolchain/link chain (benchmark/2026-10-01-bridge-846-provenance). Close that gap: pin the exact source, patches, toolchain and build script, rebuild it, prove what the rebuild equals function by function, and freeze the chain so later fixes (the two-copy bridge wall, #80) can be built and single-variable tested.
## Constraints
- No board writes and no change to any deployed artifact; builds run offline on hw248 or a2hlab in new directories.
- Source lookup order: Mac local trees (real-work, Westlake, 00.Workspace) -> a2hlab -> hw248; never reconstruct from memory.
- Never fabricate a receipt: anything not recovered is written `unknown`.
- Repository is public: no credentials; large binaries stay on hw248 under /home/alvin with path + sha256 in the repo; scripts use WORKSPACES/LAB_HOME, not user paths (check_user_paths.py).
- Equivalence is claimed only with per-function evidence; remaining differences go into an exception table (object, reason, evidence) approved by the outer loop.
- No push.
