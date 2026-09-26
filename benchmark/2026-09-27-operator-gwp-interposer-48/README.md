# 2026-09-27 operator GWP interposer (#48 path A)
Malloc-layer diagnostics to PIN the non-hook mallocng heap corruptor (musl a_crash at ld-musl
0xd6e20 on SHARED group/meta, victim thread random ≠ writer). Offline-built for aarch64 OH musl +
self-tested (glibc). Board runs by claude-2; claude-3 analyzes the captured evidence.

Evolution (each superseded the last after a board verdict):
- **v1 canary-guard-ALL** — rear+front redzones + periodic scan. Board: **0 CORRUPTION**.
- **v2/v3 page-guard** (LEFT-adjacent; v3 removed the ≤4096B size cap, guards ALL sizes). Board:
  **0 FAULT** across 12 rounds / 8 samples of 0xd6e20 (victims: bd_tracker/main/ChromiumNet0/
  RenderThread/platform-io). → proved: not a user-allocation adjacency bug; the write hits shared
  musl meta. All three user-alloc guards structurally miss it.
- **v4 OBSERVER** (current) — STOPS guarding; malloc family = thin pass-through (musl layout
  untouched). At the a_crash SIGSEGV it dumps in-process: PC→lib+off, all GP regs, and a
  frame-pointer backtrace of the detecting thread (LRs resolved via dl_iterate_phdr) = the
  free()/realloc caller chain DFX can't get (EACCES).

| Path | What |
|------|------|
| src/westlake_gwp.c | v1 RIGHT-guard interposer (guard page + quarantine + sampling + cap) |
| src/westlake_canary.c | v1 canary-guard-ALL (redzones + periodic scan + chain-load shim) |
| src/westlake_gwp_shim.c | v2/v3 LEFT-adjacent page-guard + in-SEGV dl_iterate_phdr + chain-load |
| src/westlake_gwp_obs.c | **v4 OBSERVER**: no guarding; regs + fp-backtrace dump at a_crash |
| out/libwestlake_gwp_obs.aarch64-ohos.so | v4 observer build (gitignored, on-disk; provenance name) |
| out/libwestlake_gwp_shim.aarch64-ohos.so | v4 observer bytes under deploy name (same-name overlay over v3) |
| scripts/build_gwp.sh | BiSheng clang aarch64-linux-ohos build |
| scripts/selftest.c | normal/overflow/uaf harness (LD_PRELOAD) |
| CHANGE-NOTES.md | v1 page-guard: what it does, self-test, board plan, caveats |
| CANARY-NOTES.md | v1 canary variant notes |
| GWPSHIM-NOTES.md | v2/v3 LEFT-adjacent page-guard notes |
| OBS-NOTES.md | **v4 observer**: pivot rationale, sha, 3 confirmations, board deploy, analysis plan |
| RECIPE-board-diagnostic.md | board runner recipe (push/inject/gate/repro/hand-back) |
