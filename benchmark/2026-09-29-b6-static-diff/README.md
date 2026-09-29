# B6 #53: exact R155/task50 static comparison

The assumption to reject is that the new generation differs only in link order. The six assigned ELF hashes match, but NEW also changes stdio binding, namespace/host-service admission and VM startup. **Restore behavioral contracts as coherent groups; do not revert addresses, generation hashes or verification checks indiscriminately.** This study executes no device commands and modifies none of the six inputs. The outer loop owns commit.

A second identity trap was found: `task52/static` compares different NEW artifacts and a different old provider. It cannot substantiate #53's exact pair. Its function names were reused as investigation leads, then checked against the assigned artifacts. **The old child itself embeds provider hash `80c9aee0`, not the assigned `/system/android` provider hash `977fb347`.** The reference may therefore describe the sealed provider rather than the assigned system copy. This is not proof that the reference chose an incorrect runtime baseline; it proves the file pairs differ. See `provider-baseline-caveat.json:1`. No claim is made about which provider was actually mapped on the board. See `reference-identity.json:1`; notably its old provider is `80c9aee0`, while this task requires `977fb347`. [First-edition metadata](V1.md) and [first 20 function judgments](TOP20.md) were delivered before the complete assessment.

## Findings for cx-t0

| Priority | Difference | Recommendation and evidence |
|---|---|---|
| 1 | Host moves `libhilog.so` from after `libsec_shared.z.so` to first in DT_NEEDED | Restore R155 order; isolated experiment already belongs to #52. `evidence/host/{r155,new}/dynamic.txt:4`. The other dependencies retain relative order. |
| 2 | Host adds `__sF@@LIBC` and six stdio function exports; R155 imports fflush/vfprintf | Restore broker/binding behavior as one unit for the R155 control. NEW remaps FILE pointers and adds a dlsym/pthread_once failure path ending in `_exit(127)`. TOP20 rows 1–6; `evidence/host/versioned-symbols-diff.json:1`. |
| 3 | Provider host-service fields +112/+120 change from **both zero required** to **both nonzero required** | **Resolve active-provider identity first.** `WLAR_HostServicesInstall` has a real inverted admission predicate for the assigned pair, but old child expects `80c9aee0`. Do not copy the zero-field predicate into the running sealed contract without confirming the old provider choice. [Predicate diff](evidence/runtime-provider/functions/f9e41293f04b3d10.diff), line 3. |
| 4 | Provider installer removes `WLNL_InstallSealedOpenV1`; child changes dlopen path admission to prepared dlopen_ns plus inheritance | Restore the chosen old namespace/installation path coherently **after resolving the provider-copy caveat**. Do not delete the new child export alone while keeping a host that requires it. [Installer diff](evidence/runtime-provider/functions/3e1af20b69614705.diff), line 3; TOP20 rows 6–10. |
| 5 | V1 direct child/provider entry becomes V2 identity, sealed manifest and A06→A02 prerequisite/commit sequence | This changes preconditions, error returns and lifetime. Restore the whole protocol for R155 parity, not selected offsets or one failed check. TOP20 rows 7, 10–12, 17; `ALL-FUNCTIONS.md`. |
| 6 | Provider startVm() becomes startVm(bool), conditionally omits -Xzygote and bootstraps javacore through Java; ChildMain removes post-fork hooks, adds mandatory Typeface no-op registration and defers adapter init | Restore VM mode, JNI/boot-library order and caller together. Typeface handling is in **ChildMain**, not preload; preload separately adds bridge verification before JNI registration. TOP20 rows 13–16, with exact disassembly lines. |
| 7 | Old constructor sets ICU/I18N/TZDATA/DEX2OAT environment and stack limit; new Constructors has reduced setup | Preserve required old environment/stack setup unless its replacement elsewhere in the generation is demonstrated. Absence from these three files is not proof of system-wide absence. TOP20 row 16 and both constructor records in ALL-FUNCTIONS. |
| 8 | NEW provider adds abort-bridge/base dependencies and a nonempty global Context constructor/destructor | Restore only with the corresponding VM/protocol rollback. Constructor initializes 1688 bytes and registers a destructor; it is not inert metadata. `evidence/runtime-provider/{r155,new}/dynamic.txt:4`; TOP20 row 19. |

“Restore” means **needed to reproduce the observed R155 contract**, not “proven necessary to fix the device failure.” No static-only analysis can decide that causal question. The proposed order keeps #52's link-order test isolated, then separates host stdio from the coordinated loader/provider protocol and VM behavior. No code or binary patches were made. The old provider-copy mismatch is a prerequisite to interpreting provider-specific rollback recommendations, not a blocker to the requested static comparison.

Keep harmless changes: relocated local globals/GOT/constant pools, diagnostic source-line numbers, ten P0-prefixed rejector renames with identical bodies, and non-allocated debug/symbol strings. Keep useful diagnostic-only edits unless testing their timing effects. Treat verified-open/16-or-20-byte build-ID handling and ancillary-message bounds arithmetic as compatibility/hardening changes requiring their own checks; do not call them proven equivalent or blindly revert them. R155 `bti c` disappears from `__emutls_unregister_key` in host/provider; preserve landing-pad hardening when rebuilding, but neither ELF advertises a GNU_PROPERTY BTI requirement and runtime causality is unverified.

## Complete comparison counts

The main rows below count **defined ELF function-symbol records**, including local functions and aliases. PLT/init/fini blocks lacking STT_FUNC are listed separately, so generated linker stubs do not inflate the main numbers. Same-name local duplicates receive deterministic address-order suffixes and remain separate records.

| Artifact | R155 / NEW functions | Changed | Added | Removed | Normalized equal | Total differing functions |
|---|---:|---:|---:|---:|---:|---:|
| host | 209 / 219 | 42 | 11 | 1 | 166 | 54 |
| child | 58 / 107 | 25 | 64 | 15 | 18 | 104 |
| runtime-provider | 85 / 99 | 13 | 35 | 21 | 51 | 69 |

All **352 old + 425 new function-symbol records** and **70,550 decoded AArch64 instructions** are covered; executable section bytes equal decoded bytes for each file, with zero uncovered instructions. This does not discover additional source functions optimized away or inlined. Ten zero-size symbol records use explicit next-symbol/section-end ranges. Instruction equality is not a proof of data, dependency or runtime equivalence. Evidence: `results.json:1` and `evidence/<component>/<version>/coverage.json:1`.

[ALL-FUNCTIONS.md](ALL-FUNCTIONS.md) lists every changed/added/removed function and linker block with disposition. [function-assessments.json](function-assessments.json) has per-row original disassembly line numbers, explanation, address-resolved diff and register-number-erased diff. Full unchanged records remain in `evidence/<component>/functions.json`. `TOP20.md` is the shorter review entry point.

## ELF metadata, symbols and strings

| Artifact | R155 SHA prefix | NEW SHA prefix | Imports + / - | Exports + / - | Allocated printable-run + / - |
|---|---|---|---:|---:|---:|
| host | 1f6cf53b | 02c611c8 | 3 / 2 | 7 / 0 | 23 / 3 |
| child | 0976dee8 | 587e7a85 | 7 / 3 | 1 / 0 | 96 / 51 |
| runtime-provider | 977fb347 | 8d109259 | 5 / 5 | 1 / 0 | 71 / 97 |

Full SHA-256, paths, sizes, DT_NEEDED **order**, SONAME/RUNPATH/FLAGS/FLAGS_1 and version-qualified symbol changes are retained. SONAME, RUNPATH absence and both flags fields are unchanged in all three pairs. No exported name is removed. Provider adds `libwestlake_art_abort_bridge.so` before `libart.so` and `libbase.so` after it. Child DT_NEEDED is unchanged. See each `metadata-diff.json:1`, `versioned-symbols-diff.json:1`, and raw LLVM `dynamic.txt:1`, `symbols.txt:1`, `versions.txt:1`.

Host PT_TLS remains 48 initialized zero bytes, memsz 48, alignment 16, flags R. Child/provider have no PT_TLS. Host resolved init targets remain `__do_init`, `_init`; fini remains `__on_dlclose_late`, `__do_fini`. Child has neither array. Provider retains `__do_init` and adds `_GLOBAL__sub_I_westlake_android_runtime_provider.cpp`; fini targets retain order. Arrays are resolved through RELA, not compared as zero-valued on-disk slots. See each `inventory.json:1` and metadata semantic projections.

| Artifact | RELATIVE (1027) | GLOB_DAT (1025) | ABS64 (257) | JUMP_SLOT (1026) |
|---|---:|---:|---:|---:|
| host | 47 → 48 | 10 → 12 | 1 → 1 | 191 → 190 |
| child | 28 → 46 | 0 → 0 | 0 → 0 | 32 → 36 |
| provider | 4 → 8 | 10 → 10 | 1 → 1 | 69 → 69 |

Counts are independently cross-checked against LLVM relocation dumps; identical counts do not imply identical symbols. Full per-section counts and targets are retained in the raw dumps. Section offsets/sizes/flags/content hashes, allocated strings versus non-allocated debug strings, and symbol-table attributes are independently inventoried, including 1,574 printable-run set deltas. Printable runs have minimum length four and include incidental constant bytes: the report does not pretend every printable run is a path or configuration key. Each difference has a disposition and reason in its `*-diff.json`.

## Normalization, evidence and validation

`compare.py` parses ELF64 LE headers/tables itself and records OH LLVM readelf/objdump/nm output. Direct branch targets resolve to symbol plus intra-function offset. ADR/straight-line ADRP references resolve to named functions, objects, strings or relocation targets where possible. Unresolved data offsets remain visible. Ordinary immediates, memory offsets, widths, branches and calls are retained; a separate `.register.diff` erases register **numbers** as requested. That lossy view is never sufficient to label a behavior harmless. Global data contents and dynamic bindings are separate evidence, even when code normalizes equally.

The conservative pass intentionally reports more changes than the reference's aggressive load/store-offset erasure. Manually assessed layout-only residuals, byte-checked constant pools and log-line-only edits are explicitly labeled. This study does not claim formal semantic equivalence, full interprocedural pointer analysis, or effects of dependencies outside the assigned three pairs. Raw disassembly and full inventories remain reviewable.

Reproduce all evidence and assessments, in this order:

```sh
python3 benchmark/2026-09-29-b6-static-diff/compare.py --functions
python3 benchmark/2026-09-29-b6-static-diff/top20.py
python3 benchmark/2026-09-29-b6-static-diff/assess.py
python3 benchmark/2026-09-29-b6-static-diff/verify.py
```

The six assigned files must exist at the paths recorded in `results.json`. Tools are the OH LLVM binaries under `/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/`. Input prefix checks fail closed; validation checks full SHA-256 values against the recorded inventory. No external package is required.

Validation: five offline tests pass (full hashes, LLVM relocation counts, function/executable-byte coverage, complete per-delta trace, wrong-generation and normalization negative controls). Agent-spec lint scores 100% with one decision-coverage warning; lifecycle has **2/2 pass** (`lifecycle.json:1`). Repository known-answer suite: **69 tests, 2 expected skips, no failures**. These checks do not validate restoration causality. R2: artifact inventory **verified**; function-behavior classification **partially** (bounded static assessments); device behavior and root cause **unverified**. No screenshots or execution-success claims.
