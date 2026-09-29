# Native ZIP name and ABI validation

The production boundary receives the raw central-directory filename, creator and
external attributes plus entry bytes/digests from the archive owner. Tests write
real temporary ZIPs and use real minizip from zlib 1.3.1 to read metadata, decompress and
check CRC before calling the validator. ELF fixtures are the real GNU outputs
bound in `../fixtures/elf/SOURCE.md`; `InspectElf` checks actual class/machine and
identity, while the runtime ABI list is explicit fixture/provider input.

[PKWARE APPNOTE 6.3.10](https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT),
SHA256 `0b993022a7d320a0bf704e6980bea36fafd17a6066ab994db0a0c16278a50cd6`, §§4.4.2, 4.4.15, 4.4.17, defines creator-dependent attributes and
relative names with forward separators. BC-05 requires rejecting ambiguous/dot
paths and duplicates. Accepted native paths are already canonical
`lib/<abi>/<filename>.so`; no URI decoding, case folding or path cleanup changes
one filename into another. Components are bounded at255 bytes and total names
at4096 bytes. Native symlinks/directories/FIFOs and DOS directory-marked entries
are rejected; ordinary ZIP files without a declared Unix type are supported.

The two SPC-48 tests cover valid32/64 libraries, nonnative files/directories,
absolute/traversal/repeated separators/drive/backslash/NUL/oversized names,
duplicates, nonregular entries, unknown/unavailable runtime ABI and actual ELF
mismatch/corruption. Original ELF error types are preserved for the inventory
consumer. The complete same-sealed-FD ZIP inventory is T-06; original CTS/ACTS
remain separate external gates.
