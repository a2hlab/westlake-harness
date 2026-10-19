# candidate-r4 — Toutiao video player crash (GLES/EGL symbol-preemption fix)

**Status: static proposal, no board.** r3 removed the load wall; on r3 the player then crashed deterministically. r4 fixes that crash with **one** derived file and keeps r3's three files unchanged (deploy is four files; executor = cx-seal CAS r6).

## The crash (proven)
Player thread `async_video_pla` SIGSEGV SEGV_ACCERR. libttmplayer's GLES3/EGL proc-address cache slots are `OBJECT GLOBAL DEFAULT` in `.bss` (105: gl*/egl*). The proc-loader `FUN_001ddcf0` resolves each via `eglGetProcAddress` and stores the pointer into the slot; the slot address comes from a `GLOB_DAT` GOT entry. OH musl (`e50b30f2` L1389) self-binds **only** `STB_LOCAL`, so a GLOBAL symbol is resolved by `find_sym_by_saved_so_list` to the provider's exported **FUNC** (libEGL/mali). `GOT[0x473e58]` (eglPresentationTimeANDROID) thus pointed at libEGL code (`0x7d1d95e1f8`), and `str x0,[x9]` wrote into a read-only code page. PC reconciled by load bias: `0x7eb529e714 − 0x7eb51c0000 = 0xde714` (frame `+0x21a6714` not used). Evidence: `../static/evidence/r4-crash/`.

## The fix (minimal, loader-supported)
Rewrite the 105 family `GLOB_DAT → R_AARCH64_RELATIVE` with `addend = st_value`. musl L1452 does `*slot = base + addend`, so each GOT slot self-binds to libttmplayer's own `.bss` cache (writable). `b427614d → 5fba8050`, 4662040 B, **627 bytes** differ — all inside those 105 relocs' `r_info`/`r_addend`. Symbol table, `.gnu.hash`/`.hash`, code, section permissions byte-identical. The 4 C++ vtables (`_ZTVN6vcloud8ttplayer…`, `.data.rel.ro`) are excluded. The 105 are the *potential* same-family cache collisions; this run observed exactly **1** faulting (eglPresentationTimeANDROID) — the fix covers the family so the other 104 can't fault the same way, but only 1 was observed. Provider EGL/GLES FUNC semantics untouched; no mprotect / no page-perm change.

## Rejected alternatives
`STV_HIDDEN` (musl ignores visibility at L1389) · `STB_LOCAL` (needs dynsym reorder + sh_info + hash rebuild — large) · `DF_SYMBOLIC`/`DEEPBIND` (musl doesn't honor) · surface-window wrapping (not the cause) · mprotect/RW code (masks the wrong binding — rejected by directive). See `../static/selected-change-r4.json`.

## Files
`derive_ttmplayer_selfrel.py` (`5e153009…`, reject gates) · `deploy-inputs/README.md` (four-file set) · `load-experiment-card.md` · `receipt-tests/reject-gates.txt` · `logs-sanitized/` + `raw-log-manifest.txt`. Large derived `.so` not committed (recipe is); outer mirrors to hw248. Independent cross-check: outer `video-r4-independent-relocations.json` (same `5fba8050`, 627 bytes).

## Not claimed
Playback/decode/surface. r4 removes one deterministic proc-loader crash; later stages unknown (`load-experiment-card.md` V4).
