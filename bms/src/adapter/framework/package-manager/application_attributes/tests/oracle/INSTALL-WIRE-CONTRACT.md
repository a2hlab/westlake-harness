# Install wire contract (SPC-50)

The published `jni/game_install_plan_v1.h/.cpp` remain byte-for-byte unchanged.
The real C probe fixes its 1208-byte layout and each field's offset in the
restored `GameInstallPlanWire` prefix. The missing prepass-wire header has no
historical tracked blob in this repository; the restored type follows the
current call sites and unchanged `test/test_game_install_plan_wire.cpp`, with a
1296-byte separately negotiated layout. This is not a claim about an unidentified
external binary. Version and exact size must both match before payload reads.

The old wire delegates its prefix to the existing V1 structural validator,
retaining that game's arm64/launcher requirements. The original test deliberately
uses structural FD values 41/42; passing it does not authenticate those FDs.
`TrySetVersion` refuses a nonzero major instead of truncating it into V1.

V2 has a separate ABI value 2 and 21032-byte C layout. Standard C11/C++ explicit
8-byte alignment is used for the plan and FD spans, including i386. Capability
bits 1/2/4 mean full version/general APK/sealed inputs and are negotiated as the
exact supported mask. Every string, count and reserved byte is bounded; inactive
artifact slots must be initialized, including FD=-1. Version sources preserve
DEFAULT versus EXPLICIT and declaration presence; DEFAULT with present=true is
allowed for a parsed default-valued attribute, matching the existing parser.

An artifact stores role/id and separate immutable APK/prepass FD spans. Role
values map to the existing BASE/SPLIT_CONFIG/SPLIT_FEATURE domain. The existing
`ComputeArtifactSetDigest` computes the set identity. Each prepass is decoded by
the real codec against that artifact's APK digest and the common trusted context;
ELF facts are not relabeled with another APK's digest. The limits are 64 members,
2 GiB aggregate APK bytes and 64 MiB per metadata/prepass payload.

The metadata FD holds canonical JSON (`parsed.dump()` must equal the bytes):

- `schemaVersion: 2`, `kind: "apk-install-metadata"`, `artifactSetDigest`;
- `manifest`: the real `ManifestParseReceiptJson` object, preserving complete
  facts and the versionV2 decimal strings/provenance. It must bind request,
  package, base APK/set identity and the plan's full version fields;
- `signing`: `verified`, matching set digest, nonempty `verifierVersion`, scheme
  list (2/3) and unique lowercase certificate digests. Additional owner facts
  such as lineage can travel in this versioned, fully hashed object.

This wire validator checks content/binding, not cryptographic authenticity,
caller permission, full installation policy or host readiness. Trust in the
context and signing producer must be established by the actual prepare/host
entry. No success from this function means installation completed.

Validation borrows and duplicates FDs, checks real Linux seals/fstat/digest and
reads mappings without moving caller offsets. Release is for an owned,
same-process initialized V2 plan, closes each descriptor number once without
allocation, resets all slots, and can be repeated. Unknown ABI/size is never
reinterpreted as an owned V2 object.

Tests use actual AXML APKs, the production parser and prepass codec, Linux memfd
seals and C exports. The V1 parser fixture runs in its existing primary-user-only
parse profile; V2 context stays user 27 and wrong-user tests stay active. The
manifest bytes themselves are user-independent. The generic production prepare
entry and removal/bypass of the old parser's profile restriction remain the
later bound assembly work, not a claimed result of this leaf test. Signing is
an external verified-owner fixture; no cryptographic/installation pass is claimed.
The all-uint32-bits case tests transport, not the APK installation allowed domain.

The complete unchanged original wire executable runs with assertions enabled.
The native C11 probe genuinely compiles/links/calls; Clang additionally performs
freestanding C layout compilation for i386/x86_64/armv7/aarch64, without substitute
SDK headers. These cross-target probes are not target linkage or OH execution.
The four-target probe requires the documented Clang test toolchain. Full OH
build, general host entry, CTS and ACTS remain later frozen gates.
