# M04 first-round current-tree ledger

## Boundary

- Boundary: source-to-producer reachability at the per-app Bionic ↔ typed
  bridge ↔ immutable OH/Musl boundary.
- Android behavior: an unchanged Bionic-built app DSO must reach a
  caller-scoped, typed provider; a source file merely existing in the tree is
  not an implementation.
- OpenHarmony mapping: a later current-generation producer must bind each
  classified crossing to a unique M04 provider without changing Musl, ART, the
  APK, or Unity DSO bytes.
- Fix layer: host-only module-owned oracle and ledger under
  `adapter/framework/native-compat/m04-first-round/`.
- Product code, shared producer, generation schema, M03/M07 source, device,
  APK, Unity, ART, Musl, and OH patches are unchanged.
- OH system-service patches are read-only by default. No exact-file approval
  exists for this lane, so no AOSP/OH patch path is writable in this round.

## Evidence target

- What this proves: executable source membership and denylist reachability in
  one current-project ARM64 shell producer, plus one causal positive/negative
  oracle pair.
- What this does not prove: compiler/object/ELF/payload/live-provider identity,
  ABI semantics, runtime readiness, attach, device behavior, or first frame.

This round proves only that executable shell statements in one ARM64 producer
can be separated from comments, classified, counted, and rejected when one
quarantined legacy source becomes reachable. The positive control has one
`bld bionic_compat` owner and five non-quarantined system-side inputs. Its
single-variable negative adds `unity_signal_box.c` and must fail closed.

This round also records the current input, crossing, provider/owner, and
legacy-shim reachability facts. It does not claim that the current producer is
eligible: the current-tree audit intentionally remains red.

## Environment

- Branch: `lane/m04-bionic-musl-impl-r1`.
- Base: `c919f07c347ceba092b6b5112cb9daa1eefaec15`.
- Integrator contract delta: the user supplied the correction from main
  `2a4f426`; this lane did not merge, rebase, or copy shared-schema bytes.
- Worktree: `/opt/21.Game/02.unity.cardwords/.work/m04`.
- Host: `Darwin AlexMac 25.4.0 arm64`.
- Device: not used; no hdc/adb path and no 5EAB5 access.
- Tool path: `/usr/bin/python3` and module-local
  `src/tools/verify_source_reachability.py`.
- Artifact path: no product artifact; the only committed outputs are source,
  fixtures, ledger, and evidence Markdown in this directory.
- App: no APK was launched; canonical CardWords bytes are missing locally.
- Test interpreter: `/usr/bin/python3`, Python 3.9.6, SHA-256
  `12bed4523661307059b879b9b54e77a73176e9d27d27a0e40363271d8f0668ba`.
- Producer input: `adapter/build/inner/cross_compile_arm64.sh`, SHA-256
  `2e3d090742c962fdb67a29cc60a149537c4b12489b2d920f2f00a0ba0cd857df`.
- Generation input: `adapter/build/build_l03_a12_arm64_generation.sh`, SHA-256
  `253ed9ae65f3943328ffabc3ae1e7f3d25e222f826872fa57df22db6516910e1`.
- Device, hdc, adb, 5EAB5, production-init, SELinux, APK launch, and network:
  not used.
- External product/build inputs: zero.

## Status

- Label: `real_impl` for the host source-membership oracle; `build_pass` for
  its causal fixture replay; current product candidate remains failed.
- Why: the parser and single-variable mutant are executable and repeatable,
  while all runtime/product/device prerequisites are explicitly absent.
- Oracle implementation and causal fixture tests: `real_impl`, host-only.
- Oracle execution: `build_pass` (syntax/source audit only).
- Existing `thread-template-publisher`: `real_impl`, host-only and product
  unwired; it is not promoted by this report.
- Current ARM64 product candidate: failed entry/reachability gates; neither
  `real_impl` nor `device_verified` is claimed.
- `device_verified=false`, `product_activation=false`.

## Design consistency gate

The `design-check` five-question gate was applied before landing:

1. ART/class_linker/vtable/entrypoint semantics changed: **no** (`PASS`).
2. BCP Java, AOSP classes, or ActivityThread semantics changed: **no**
   (`PASS`).
3. Change is confined to the adapter-owned native-compat audit layer:
   **yes** (`PASS`).
4. libart/BCP bytes requiring a coherent boot rebuild changed: **no** (not
   applicable).
5. truly-cold device evidence exists: **no** (`Not Proven`, never promoted by
   this host-only gate).

There is no Java implementation or Java stub in this change. The external
HanBing/Yue mechanical helper was not run because this lane contract forbids
consuming scripts or product inputs from other projects; the equivalent scope
check is performed against current-worktree paths and Git diff only. The local
`app_native_so_compat` and `bionic_to_musl_compat` documents were used as
historical design inputs, while the newer M04 contract overrides their
plain-dlopen, global-preload, and fake-success proposals.

## Current-byte input ledger

| Required input | Current-project observation | Disposition |
|---|---|---|
| Canonical unchanged APK | No APK byte exists in the current worktree. The local historical handoff names expected SHA-256 `435f0ebbf99b5f5ae76aecb411da7684052a92ef0b6aee18d50afa6a98210626`, but there is no local byte to recompute. | `missing`; entry gate fails |
| `libmain.so` | Scratchpad-only byte, SHA-256 `9348cd29bcdec5b677c7124b111a2ebb285bfd6550282619c8fd178f2982eb5d`; not bound here to an APK zip entry/current generation. | fact oracle only |
| `libunity.so` | Scratchpad-only byte, SHA-256 `539fbc927731ad1ce93ab214133bc1fa5810e07f884d6b884a91b7b51d60bc82`; not bound here to an APK zip entry/current generation. | fact oracle only |
| `libil2cpp.so` | Scratchpad-only byte, SHA-256 `c298c9cb864ba7117d873e3f14d98f20db765c87554ee1a570c810ede1cf9f4d`; not bound here to an APK zip entry/current generation. | fact oracle only |
| `lib_burst_generated.so` | Absent from the current worktree. | `missing`; four-root closure fails |
| Exact OH/Musl loader | One scratchpad byte exists at `adapter/scratchpad/claude_presearch/P05_L03_A16/inputs/ld-musl-aarch64.so.1`, SHA-256 `316f70f2195b72aaf64e9f71e97d1d16cc25070f852f185994175893aeeeaa98`; no local AOSP14/OH6.1.0.31 origin-path freeze receipt binds it to this candidate. | fact oracle only; not consumable generation input |
| HP-9 source | HP-9 source has not been frozen into 02. No 02d sibling path was read or consumed. | `missing`; sibling consumption forbidden |
| Immutable Musl/base providers | No current immutable-base manifest with complete direct/transitive provider identity. | `missing` |
| Current M04 candidate manifest | No source → object → ELF → payload current-byte manifest. | `missing` |
| M05 baseline verdict | `adapter/verification/bionic-musl/` and the named independent-verifier directories are absent at this base. | `missing` |
| Offline generation receipt | Per integrator correction, `NativeGenerationReceiptV1` proves only an offline artifact generation. No local definition is invented or changed by M04. | absent at this base; integrator-owned |
| Child runtime-ready receipt | Before attach, `ChildRuntimeReadyReceiptV1` must bind `SpawnBirthReceiptV1 + pid + startSeq + generation + epoch`. Offline generation identity cannot substitute for this receipt. | absent at this base; integrator-owned |

The three scratchpad DSO hashes and the relevant source hashes still match the
sealed current-project blind-review inputs. That makes them reproducible fact
oracles only; it does not upgrade them to the required canonical four-root
ledger.

## Actual crossing / provider / ownership ledger

Because the canonical APK/four-root ledger is incomplete, “actual” below means
the currently frozen three-DSO fact oracle plus executable producer membership;
unknowns stay explicit.

| Capability | Current consumer/crossing fact | Current provider/reachability | Owner and classification | Result |
|---|---|---|---|---|
| Namespace/provider scope | Local sealed review records `libmain/libunity/libil2cpp` depending on Android SONAMEs and `BIND_NOW` for the two large DSOs; no edge to the legacy Unity boxes. | M07 loader is read-only; no same-generation M04 provider manifest or live provider identity. | M07 owns loader; M04 owns ABI broker; crossing remains `unclassified`. | `Not Proven` |
| TLS / stack guard | Local three-DSO oracle and legacy comments identify fixed TP-relative guard access; fourth root and complete bypass scan are absent. | `thread-template-publisher` is host-only and absent from product recipes. `bionic_tls_abi.c` is also unwired and denylisted. | M04, must be `translated` only after exact Musl layout + six-entry admission proof. | `Not Proven` |
| pthread / mutex / cond / rwlock / once / sem | Local three-DSO oracle records dynamically interposable pthread/sem calls, but inline/direct access closure is unknown. | `unity_pthread_box.c` is not in the ARM64 producer. No typed side owns one-lock-domain semantics. | M04; currently `unclassified`, not direct-compatible by symbol existence. | `Not Proven` |
| Signal layout and delivery | Local oracle records signal relocations and the known Bionic 8-byte versus Musl 128-byte layout hazard. | `unity_signal_box.c` is not in the producer. `art_runtime_stubs.cpp` globally installs handlers and is reachable, but is not a typed signal provider. | M04 translation + ART/Musl signal owner; current route is `unsupported`. | `Failed` for product eligibility |
| errno / libc object layout / stdio | Three-DSO oracle covers some imports, not the complete fourth-root closure. | `unity_libc_stubs.c` is unwired; active six-source `libbionic_compat` is system-side AOSP-on-Musl support, not a guest libc ABI provider. | M04; individual POD/direct cases need classification, FILE/layout cases need typed translation or explicit unsupported. | `Not Proven` |
| Allocator / FD ownership | No current exact allocation/free/fdsan call closure or lifetime ledger. | `malloc_compat.cpp` and `fdsan_stubs.cpp` are producer-reachable labeled stubs/no-ops for system-side AOSP support. They do not prove guest heap/FD ownership. | M04; crossing remains `unclassified`. | `Not Proven` |
| C++ runtime / RTTI / exception / unwind | No four-root C++ provider and no cross-boundary object inventory. | No per-app isolated C++ runtime provider in M04-owned product sources. | M04 with M07 namespace; raw objects/exceptions are `unsupported` across the bridge. | `Not Proven` |
| Main/pthread/JNI/callback/pool/post-fork/signal entry admission | No current generation/epoch receipt covers the six entry families. | Host publisher proves only a portable template mechanism; no product wiring. | M04 admission must feed integrator-owned `ChildRuntimeReadyReceiptV1`, bound to `SpawnBirthReceiptV1 + pid + startSeq + generation + epoch`. | `Not Proven` |

Exit classification counters for the actual product remain:
`missing>0`, `duplicate=unknown`, `unclassified>0`. Therefore no
offline `NativeGenerationReceiptV1` may be issued. Even a future valid offline
receipt cannot authorize attach without the separate bound
`ChildRuntimeReadyReceiptV1`.

## Producer and payload ownership ledger

| Artifact/source group | Executable current-tree fact | Ownership / consequence |
|---|---|---|
| `libbionic_compat.so` | ARM64 producer compiles five non-quarantined inventory sources plus denylisted `misc_compat.cpp`. | M04-owned sources, system-side AOSP-on-Musl compatibility only. Source membership is proven; behavior and guest ABI are not. `misc_compat.cpp` is separately failed below. |
| `libart_runtime_stubs.so` | ARM64 producer compiles `art_runtime_stubs.cpp`; L03.A12 generation copies the DSO to payload, and `libprofile/libunwindstack` link it. | Broad runtime stub is product-reachable and violates the M04 quarantine gate. This is the first source-reachability failure after the already-failed input gate. |
| `libbionic_compat.so` payload | No explicit `copy_regular` of this DSO appears in the current L03.A12 payload list. | Complete provider closure is not proven; changing the shared producer/payload belongs to the integrator. |
| `thread-template-publisher` | Referenced only by its module-local host tests/report. | M04-owned `real_impl`, host-only, not product-reachable. |
| Legacy Unity pthread/signal/libc/TLS sources | Present in the tree but absent from executable ARM64 producer statements. | Correctly unreachable for now; source existence is not implementation. |
| `.bak*` sources | Tracked historical files exist, but no executable producer statement references them. | Denied from every product artifact; historical fact only. |

## Legacy shim reachability denylist

| Denied source | Reachability now | Why denied from product | Removal/review condition |
|---|---|---|---|
| `art_runtime_stubs.cpp` | **reachable**: compiled and payload-copied | broad no-op runtime surface, constructor signal ownership, abort/raise/global same-name behavior, suppressed assertions | replace each actually needed capability with its unique real owner; final ELF denylist and provider closure show zero reachable broad stub |
| `unity_signal_box.c` | unreachable | title allowlist, raw signal syscalls, handler suppression, pretend-success return | caller-scoped typed signal codec + reviewed ART/Musl delivery owner; no global same-name provider |
| `unity_pthread_box.c` | unreachable | global pthread interposition, `RTLD_NEXT`, mapped-address-as-owner heuristic, no-CAS first-use, in-object pointer overwrite, raw 8B mask forwarded to Musl, no thread admission trampoline | one-lock-domain proof per primitive, typed ownership/lifetime state machine, all entry admissions |
| `unity_libc_stubs.c` | unreachable | Unity-specific allow-surface, FORTIFY checks dropped, overlapping copied `FILE` objects, constructor mutation | complete crossing census; ABI-identical direct cases proven individually, layout cases translated without raw FILE objects |
| `bionic_tls_abi.c` / `bionic_tls_abi.h` | unreachable | constructor/inline direct-TP write, fixed entropy fallback, Musl global guard rewrite, unsafe ready/publication order | final-main TLS ownership, OS entropy only, authenticated generation/epoch publication, exact Musl non-overlap proof |
| `misc_compat.cpp` | **reachable** in `libbionic_compat.so` | fixed entropy fallback and direct rewrite of Musl global `__stack_chk_guard` | replace with final-main authenticated guard publication; OS entropy failure must fail closed |
| `art_quick_entrypoints_arm64.S` | unreachable | broad minimal/no-op ART entrypoints and null-return fallbacks | real AOSP14 entrypoints from frozen source/build only; zero provider collision |
| `palette_system_stub.c` | unreachable | unconditional success/default outputs for behaviorful APIs | real unique palette owner or explicit unsupported failure per call closure |
| every `*.bak*` under `bionic_compat/src` | unreachable | mixed/ambiguous source provenance | never product-consumed; delete only in a separately approved cleanup boundary |

The gate deliberately rejects a whole denied file becoming producer-reachable.
It does not claim that files absent from this table are semantically approved.

## Proven

- The module, branch, base, worktree, Owned-Paths, entry/exit contracts, and
  local architecture specifications were read before implementation.
- The current ARM64 producer has one `bld bionic_compat` command and references
  the five non-quarantined inventory sources once each.
- `unity_signal_box.c`, `unity_pthread_box.c`, `unity_libc_stubs.c`, and
  `bionic_tls_abi.c` are not executable members of that producer.
- `art_runtime_stubs.cpp` is executable producer input and its DSO is copied to
  the generation payload.
- The module-local positive source-membership control passes, and the
  single-variable old-signal-shim mutant is killed.
- No external project source, header, object, DSO, toolchain, sysroot, or
  product artifact was compiled, linked, copied, or loaded.

## Not Proven

- Canonical APK/four-root identity, the fourth Unity DSO, exact AOSP14/OH
  6.1.0.31 inputs, exact Musl/base providers, and current M05 verdict are absent.
- HP-9 remains unfrozen in 02; no claim or source was imported from 02d.
- This source parser does not prove shell execution, compiler argv, object
  membership, strict link, ELF identity, SONAME, Build-ID, symbol versions,
  provider uniqueness, namespace isolation, payload completeness, or live maps.
- No signal, pthread, TLS, allocator, FD, errno/libc layout, or C++ runtime
  semantic claim is promoted.
- No ARM64 weak-memory, fork, signal delivery, sanitizer, device, truly-cold,
  Unity init, render, first-frame, input, or soak evidence exists in this round.
- Neither the offline-only `NativeGenerationReceiptV1` nor the bound attach
  prerequisite `ChildRuntimeReadyReceiptV1` is proven or defined here.
- The existing active system-side stubs/no-ops are inventoried but not approved
  as guest translations or release behavior.

## Failed

- Module entry gate: current worktree lacks a canonical APK/four-root ledger,
  exact frozen loader/provider closure, M04 candidate manifest, and M05 baseline.
- Current producer reachability gate: `art_runtime_stubs.cpp` is denylisted yet
  producer-reachable; the generation also payload-copies its DSO.
- Current producer reachability gate: `misc_compat.cpp` is denylisted yet
  producer-reachable because it retains fixed entropy fallback and a Musl
  global guard rewrite.
- Provider/payload ledger: no explicit current-generation payload membership
  for `libbionic_compat.so` was found.
- The negative fixture that adds `unity_signal_box.c` fails with
  `M04_REACHABILITY_FAIL reasons=deny_reachable`; this failure is intentional
  and preserved.

## Next evidence

One deterministic next gate only:

- Command: execute the literal local SHA-256 verification command supplied by
  the integrator's future current-byte capsule receipt, then execute the M05
  baseline command named by that same receipt; neither command/input exists at
  this base, so M04 must not substitute an ambient path.
- Expected output: canonical APK + four DSO + exact loader/base-provider hashes
  all match one generation, and M05 names those same bytes without admission.
- If it fails: stop at the first hash/realpath/generation mismatch and do not
  build, link, wire, or deploy a compatibility shim.

1. Integrator lands a local, immutable current-byte input capsule containing
   the canonical APK plus four extracted DSO entries, exact OH/Musl loader and
   immutable base-provider manifest, with origin/local SHA-256 and generation
   identity; M05 emits its baseline against those bytes.
2. Re-run this source gate, then extend evidence (not this commit) to
   source → object → final ELF/payload membership.

Expected next result: all entry inputs verify locally, M05 baseline identifies
the same bytes, and the first executable failure is deterministically the
denylisted broad runtime-stub membership. If the byte capsule does not verify,
stop there; do not build a shim or consume an ambient/legacy input.

Receipt sequencing after that later repair remains: integrator signs the
offline generation with `NativeGenerationReceiptV1`; runtime admission then
produces the separate `ChildRuntimeReadyReceiptV1` bound to
`SpawnBirthReceiptV1 + pid + startSeq + generation + epoch` before attach.
This module neither defines nor edits either shared schema.

## Shim/stub/bypass inventory

- Item: no new runtime shim/stub/bypass; one test-only old-signal-shim source
  token mutant, plus the pre-existing reachable/unreachable inventory below.
- Owner: M04 owns this oracle and its fixture; existing runtime stubs retain
  their historical owners pending integrator assignment.
- Why it exists: kill source-membership false positives before any semantic or
  device experiment.
- Removal condition: retain the oracle until final producer/object/ELF
  membership and denylist coverage supersede it with equal fail-closed checks.
- Test coverage: one exact positive fixture, one single-variable negative
  fixture, and one preserved current-producer failure.
- App-specific or common: the oracle is common; the negative file token is a
  quarantined historical Unity-specific source and is never product-reachable.
- Newly added runtime shim/stub/bypass: none.
- Test-only mutant: `tests/fixtures/negative_old_shim/build.sh` adds one source
  token only. Owner: this oracle. Reason: prove fail-closed reachability.
  Removal condition: retain while the denylist policy exists. Coverage: one
  exact positive and one single-variable negative. Product reachable: no.
- Existing reachable stubs: `art_runtime_stubs.cpp`, `fdsan_stubs.cpp`, and
  behavior-weakening/no-op surfaces in the six-source system compat library.
  Owner: existing M04/system-runtime compatibility history. Reason: historical
  cross-link closure. Removal condition: unique real owners and current-byte
  tests for every live call. This report adds no endorsement.
- Existing unreachable legacy shims: listed in the denylist table. They remain
  source facts only and are not silently deleted in this boundary.

## Memory/skill/CI/review updates

- Memory: no memory file changed. The durable local report records that
  source presence, producer membership, payload membership, and live provider
  identity are four different evidence levels.
- Skill: WestLake boundary-first, evidence labels, fail-closed stub treatment,
  and required handoff sections were applied; no skill file changed.
- CI: module-local replay is `tests/run_host_tests.sh`; shared CI is unchanged
  and remains integrator-owned.
- Integration requests: only
  `var/evidence/INTEGRATION_REQUEST.md` is used; no root/shared request file is
  created.
- Review checklist: keep comments excluded from reachability counts; require one producer
  owner; reject denylisted, backup, duplicate, missing, and unclassified source
  membership; never promote this source gate to ELF/device proof.
