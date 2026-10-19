# Independent decoder-selection address check

Ghidra VA0x28d0fc is not the ELF PC. Independent LLVM disassembly places the function at ELF/file0x18d0fc with imagebase0x100000. The bytes through0x18e534 exclusive are identical in the r4 REA input5fba8050 and the r8/r9 actual reused player0b4d95c5 (range SHA31901285).

The complete raw REA result (d74c11ab,56,824bytes) was read independently. Its function reads a track property through a virtual call, then branches on internal codecId0xae/0x41000/0xc5 to request a named decoder; missing selection falls back to avcodec_find_decoder. This does not prove registration, the live stream codecId, decoded frames, or audible playback.

Raw REA and independent LLVM output are preserved in the SHA-verified private archive. No runtime writes or new build were performed for this check.
