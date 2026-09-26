# 2026-09-26 operator hollow hook-engines (#48)

Convergent fix for the clamp r3/r4 residual mallocng heap corruption: neutralize the
inline-hook engines (libbytehook + libshadowhook) so NO lib can install any inline hook /
trampoline. Binary-patched from codex-2's exact board baselines.

## Layout
| Path | What |
|------|------|
| out/libbytehook.CLAMP48HOLLOW.so | patched (gitignored binary, on-disk) sha256 fbb761a0… |
| out/libshadowhook.CLAMP48HOLLOW.so | patched (gitignored binary, on-disk) sha256 34378f5c… |
| scripts/patch_engine.py | the patcher (offsets + mov x0,#N;ret), reproducible from baselines |
| scripts/assert_hollow_engines.sh | verifies 9 entries return fake + structural (9/9 PASS) |
| CHANGE-NOTES.md | shas, byte-level change, safety proof, OBSERVE/FUNCTIONAL table, crux experiment |

## Change
Overwrite each engine's exported hook-install entry (bytehook_hook_single/partial/all,
shadowhook_hook_func_addr/sym_addr/sym_name/sym_name_callback) first 8 bytes with
`mov x0,#1; ret` (fake non-null handle, install nothing); each unhook with `mov x0,#0; ret`.
32/40 bytes changed; exports/SONAME/NEEDED unchanged (no ULE); init untouched.

## Why / decision
r3 (jato free-hook) and r4 (hotfix ClassLinker hook via shadowhook MACHINERY) are different
hooks but BOTH go through the engines. r4's corruptor is the machinery itself (non-malloc hook
still corrupts) -> conditional pass-through can't help -> full engine no-op. Bypasses the
namespace isolation that killed the LD_PRELOAD master-switch (patched .so file IS what loads).
NOT deployed (board is codex-2's). Crux experiment gates functional safety.
