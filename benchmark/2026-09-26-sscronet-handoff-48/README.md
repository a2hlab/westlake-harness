# #48 sscronet exact arm64 baseline handoff

ACK(done), R2=verified for artifact identity only. Read-only retrieval from board61, no app start, deployment or profile change. Intended for Claude-3 analysis/patching: r1 ChromiumNet0 libsscronet ELF0x28a21c.

- App namespace path: `/data/local/tmp/asx/lib/arm64-v8a/libsscronet.so`
- Actual board path: `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libsscronet.so`
- SHA256: `38f0dd424fabd2b92a08e0a6eb372bc464dd424b370aba23c88e39ba6374866f`
- Bytes: 4321504; ELF64 little-endian AArch64; inode137351 matches the recorded crash maps.
- Shared binary: `/Users/zhaoyue/orca/workspaces/westlake-harness-enginecheck48/benchmark/2026-09-26-sscronet-handoff-48/libsscronet.so` (same /Users path on Mac and a2hlab VM).

Board-before SHA = pulled SHA = board-after SHA. The binary itself is committed, not just its hash. `manifest.json`, `board-before.txt`, `board-after.txt` and crash-map excerpts preserve the evidence. The caller/root cause is not inferred from file identity.

All36 hollow+clamp+engine component hashes still match the final test state. No app/appspawn PIDs, both guardians stopped, map_count1048576, consent retained. `pull.py` uses the established HDC helper with deadlines≤20s and was run through `orb -m a2hlab bash -lc`. It reads board state and copies the binary off the board; no on-board writes.
