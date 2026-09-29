# Prepass canonical format, schema 1

This internal codec restores BC-02. The existing materializer test's
`wire::PrepassBundleRecord`, `PrepassBundleCodec::Decode`, identity fields and
`NO_NATIVE_ELF` contract remain available. Full materializer/context/FD execution
is wired by its own subsequent tasks; this test does not claim it ran already.

The encoding is independent of C++ object layout and host endian order. Integers
are unsigned little-endian at the specified width. Strings are a uint32 byte
length followed by bytes, without a terminator; embedded NUL is rejected.

| Part | Encoding |
|---|---|
| Header | Eight bytes `4f 48 50 52 45 50 00 01`; uint32 schema=1; uint32 reserved=0 |
| Identity | requestId string, packageName string, nonnegative userId uint32, packageGeneration string; apk/contract/policy/tool/topology/runtimeGenerationSeal digest strings |
| Inventory | disposition uint32 (0 no native, 1 analyzed native present, 2 no matching ABI), nativeEntryCount uint32, ELF fact count uint32 |
| ELF identity | analyzerVersion/apkSha256/entryName/abi/elfSha256 strings; class uint8, machine uint16, soname string (may be empty) |
| LOAD facts | count uint32; each offset/virtualAddress/fileSize/memorySize/alignment uint64, flags uint32 |
| Dynamic facts | counted needed-library strings; counted exported-symbol strings; counted required symbols, each name string plus weak uint8 (0/1) |

ELF records are sorted by (abi, entryName) and duplicates are rejected. Within an
ELF, DT_NEEDED, PT_LOAD and symbol order are preserved. Decode requires exact
re-encoding equality, no trailing bytes, valid counts and known schema/enums.
The codec validates scalar/range/identity structure; actual ELF analysis still
belongs to `InspectElf`, never to a serialized claim alone.

Maximum payload is 64 MiB, native records 4096, LOAD segments per ELF 4096,
symbol/dependency list items 1,048,576, identity strings 4096 bytes, other strings
65,535 bytes. Count allocations are also bounded by remaining payload bytes.
Digests are exactly 64 lowercase hex characters. These are codec resource limits,
not new Android SDK/ABI compatibility rules.

`payloadSha256` covers every canonical byte. `record.binding` comes from the
trusted request context and must equal the payload's identity. For an FD consumer,
`DecodePayload` takes both the expected payload digest and trusted binding from
that owner's envelope; deriving them from the same untrusted payload would defeat
the check. A checksum is not a signature. The signature/APK-set owner, context
validator and host C ABI retain their own obligations.

The tests use a real sealed APK and production inventory/ELF analysis for the
multi-ELF record. A separate DTO width probe changes a uint64 value only to test
codec preservation, and does not claim those altered facts were re-analyzed.
Every encoded payload byte is individually corrupted; identities are additionally
changed with recomputed checksums against an unchanged trusted binding. Original
CTS/ACTS and actual install/loader observations remain external gates.
