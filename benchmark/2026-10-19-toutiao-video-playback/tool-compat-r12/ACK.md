# ACK r12-tool-ready

Offline-ready dedicated 5cd probe, not tool compatibility PASS.
Actual OH cross-build rc0; probe SHA 8ab9acaff7c92098f764aa602272e51aeab5b4935af9ef42875c578b874e6c3c, marker ELF0x1af0.
11 Python cases / 4 Rust selectors PASS; t7 lint100; user-path gate0.
No device call, no R11 change, no push. Original stderr and build/command logs
are persistent under .private and bound by private-evidence-index.json; not in git landing.

Entry: `observe.py --admission FILE --out NEWDIR --execute`.
Default refuses. `--validate-only` is local only. Outer creates the real launch
receipt from actual device printf, starts the two owned processes and owns the
exclusive forwarding/cleanup. Runtime checks exact cmdline/socket inode/identity.
Final human acceptance still requires actual handshake/two hits/detach/progress
and outer forward removal; no Toutiao applicability is claimed.
