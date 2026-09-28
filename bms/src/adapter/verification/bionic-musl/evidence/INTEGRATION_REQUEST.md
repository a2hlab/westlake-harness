# Integration Request M05-R1-001

Location is intentionally inside the M05-owned evidence directory. This request
records missing cross-module inputs. It does not define a shared ABI or
authorize M05 to edit M03/M04/M07, shared schemas, build recipes, generation
manifests or OH system-service patches.

Integrator contract anchor supplied during this lane: `main@2a4f426`. This lane
is not merged or rebased and remains based on `c919f07`.

## Integrator actions requested

1. Land the canonical
   `BIONIC-MUSL-UNITY-INDEPENDENT-VERIFIER-BOOTSTRAP.md` in this project and
   identify its authoritative path/hash, including the S1-S7 definitions.
2. Land or restore the lane-contract source
   `adapter/research/atoms/L03/A12/runtime-generation-redteam/**`, including the
   names and evidence rules for all existing 22 gates.
3. Provide an integrator-approved `NativeGenerationReceiptV1` for the M04
   candidate. M05 will treat it strictly as an offline-generation receipt.
4. Before any runtime attach, provide a separate
   `ChildRuntimeReadyReceiptV1` bound to `SpawnBirthReceiptV1`, pid, startSeq,
   generation and epoch. M05 will consume only integrator-approved receipt
   versions and will not edit their shared schemas.

## Minimum offline-generation facts

These are verifier data requirements, not a proposed shared field layout:

- Candidate ID, source revision and one nonempty generation token common to all
  offline artifacts and evidence.
- Frozen local-input manifest with, for every input, origin path/SHA256 and
  local path/SHA256. Permitted upstream origins are only AOSP 14 and
  OpenHarmony 6.1.0.31/wukong100.
- Exact unchanged APK identity and its four Unity entries: zip entry, SHA256,
  byte size, ELF machine/class, SONAME where present and Build-ID where present.
- Exact loader, Musl runtime, typed bridge and every recursive provider identity:
  local path, SHA256, byte size, ELF machine/class, SONAME, Build-ID,
  `DT_NEEDED`, strong UND and symbol-version observations.
- Strict-link and recursive-provider closure results, with every strong UND
  resolved to exactly one provider and every provider bound to the same
  generation.
- Namespace/search policy and proof that no `RTLD_GLOBAL`, ambient LD path,
  RUNPATH/RPATH, plain-dlopen fallback, loose DSO or wrong-generation provider
  can satisfy the candidate.
- Sealed-FD observation for every opened candidate/provider: dev, inode, size,
  content hash, open/map lifetime and equality to the mapped identity.
- Current actual crossing/provider/ownership ledger; each crossing classified
  `direct`, `translated` or `unsupported`, with zero missing/duplicate/
  unclassified entries.
- Reachability denylist and complete shim/stub/bypass inventory, including owner,
  reason, removal gate, tests and app-specific/common scope.
- Deterministic producer receipt: exact commands/tools, input hashes, output
  hashes, strict link, ELF/SONAME/Build-ID checks and two-build equality.

`NativeGenerationReceiptV1` closes only these offline-generation facts. It must
not be cited as evidence that a forked child exists, is the expected process or
is safe to attach.

## Minimum runtime-ready binding facts

- `ChildRuntimeReadyReceiptV1` identity and exact local receipt hash.
- The bound `SpawnBirthReceiptV1` identity and exact local receipt hash.
- Exact pid and startSeq identifying the same process birth.
- Generation equal to the accepted offline-generation token.
- Runtime epoch used by the guard/TLS/fork admission path.
- A fail-closed mismatch result for each single-variable mutation of spawn
  receipt, pid, startSeq, generation and epoch.

## Frozen-input and patch stop-lines

- HP-9 source is not frozen into 02. M05 must not consume the 02d sibling or any
  copy derived from it. If HP-9 becomes required, the integrator must first land
  a project-local freeze receipt under the standard provenance policy.
- OH system-service patches are read-only by default. Any future need must be an
  exact-file request approved and assigned by the integrator; M05 requests no
  such patch in this round.

## Acceptance and next evidence

After the required inputs land on main, the integrator should create a fresh M05
lane from the absorbed commit. The deterministic next gate is to normalize one
offline receipt, import and rerun all 22 gates against the same generation, then
verify the child-ready/spawn-birth binding before runtime attach. No device run
is requested before the offline current-byte gate succeeds.
