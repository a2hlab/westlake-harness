# 2026-09-26 operator r5 neuter (#48)
Neuter libmonitorcollector-lib.so's sigaction calls (embedded xhook SIGSEGV-handler install/restore)
that overrun musl's 152B old buffer (Bionic-vs-musl ABI, r5). 2 `bl sigaction`->`mov x0,#0`; same
method as npth 7639af00; namespace-robust (file-level). See CHANGE-NOTES for safety proof.
| Path | What |
|------|------|
| out/libmonitorcollector-lib.R5NEUTER48.so | patched (gitignored binary, on-disk) |
| scripts/patch_monitorcollector_sigaction.py | reproducible patcher from f3918bdc baseline |
| scripts/assert_r5neuter.sh | 2 sites mov x0,#0 + 0 bl-sigaction + ELF (ALL PASS) |
| CHANGE-NOTES.md | shas, byte change, root cause, safety proof |
