# 2026-09-27 operator GWP interposer (#48 path A)
GWP-ASan-lite page-guard malloc interposer to PIN the non-hook mallocng heap corruptor by faulting
AT the corrupting write (crash PC == writer). Offline-built for aarch64 OH musl + self-tested
(glibc). NOT on board yet — coordinate with codex-2. See CHANGE-NOTES for self-test + board plan.
| Path | What |
|------|------|
| src/westlake_gwp.c | header-minimal interposer (guard page + quarantine + sampling + cap) |
| out/libwestlake_gwp.aarch64-ohos.so | board build (gitignored binary, on-disk) |
| scripts/build_gwp.sh | BiSheng clang aarch64-linux-ohos build |
| scripts/selftest.c | normal/overflow/uaf harness (LD_PRELOAD) |
| CHANGE-NOTES.md | what it does, self-test results, board diagnostic plan, caveats |
