# M04 integration request — current-byte entry capsule

## Request boundary

This request closes only M04's first entry gate. It requests no product source,
shared producer, shared schema, OH system-service patch, device, merge, or
deployment change from this lane.

## Requested integrator-owned evidence

Provide a current-project-local immutable capsule containing:

1. the canonical unchanged APK and its four extracted ARM64 entries
   `libmain.so`, `libunity.so`, `libil2cpp.so`, and
   `lib_burst_generated.so`;
2. exact AOSP 14 / OpenHarmony 6.1.0.31 loader, Musl/sysroot, immutable base
   providers, and audit tools actually consumed by the later producer;
3. for every input, `origin path + origin SHA256 -> local path + local SHA256`,
   plus APK zip-entry identity, ELF identity, Build-ID, and one generation ID;
4. an M05 baseline verdict recomputed against those exact local bytes.

HP-9 is not frozen in 02 and must remain absent from the capsule unless the
integrator separately freezes the approved standard source into 02. Nothing
may be read, compiled, linked, or copied from 02d or another sibling project.

## Receipt contract note

The user supplied the main `2a4f426` contract correction without authorizing
this lane to merge/rebase. `NativeGenerationReceiptV1` is offline-generation
evidence only. Before attach, `ChildRuntimeReadyReceiptV1` must bind
`SpawnBirthReceiptV1 + pid + startSeq + generation + epoch`.

M04 requests that a future lane be created from an integrator baseline where
those already-versioned shared contracts are available. M04 does not request,
define, or modify their schema in this commit.

## Acceptance

The request is satisfied only when every capsule byte and receipt input is
inside the current project, hashes verify before and after use, realpaths stay
inside the capsule, M05 names the same bytes, and no sibling/ambient input is
present. Until then M04 remains audit-only and must not add a compatibility
shim.
