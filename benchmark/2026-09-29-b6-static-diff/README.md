# B6 #53: exact R155/task50 static comparison

The assumption to reject is that the new generation differs only in link order. The six assigned ELF hashes match, but NEW also changes stdio binding, namespace/host-service admission and VM startup. **Restore behavioral contracts as coherent groups; do not revert addresses, generation hashes or verification checks indiscriminately.** This study executes no device commands and modifies none of the six inputs. The outer loop owns commit.

The task52 reference used different NEW artifacts; function names were only investigation leads. **Task 56 corrects the old provider from the superseded system copy 977fb347 to sealed 80c9aee0**, now matching the old child manifest and the reference old provider. All three reference NEW hashes still differ. `reference-identity.json:1` and `provider-baseline-caveat.json:1` record the reconciliation. Historical V1 files are not provider rollback guidance.

## Findings for cx-t0

**Use [RESTORE-PLAN.md](RESTORE-PLAN.md) for the single coordinated source restoration.** Four groups cover service-table publication, namespace/V1 identity and A06/A02 sequence, VM/JNI/environment/dependencies, and host stdio/link order. Each gives R155 disassembly lines, current source targets and offline exit checks. Source is mutable preparation state; pinned binaries remain authoritative (`source-targets.json:1`).

The corrected provider has the same 93 normalized instructions in WLAR_HostServicesInstall: **+112/+120 are mandatory nonzero in both versions**. WLNL_InstallSealedOpenV1 moves from the R155 installer to candidate Constructors; restore its installer-time ordering before READY, not a second call. R155 already uses non-zygote startVm(bool), the Typeface warmup no-op and deferred adapter initialization; recommendations to undo these are withdrawn. Actual VM changes include javacore bootstrap/abort option, JNI phase order, environment/stack setup and dependencies. See [PROVIDER-REVISION.md](PROVIDER-REVISION.md).

Host/child findings and evidence bytes are unchanged (`host-child-preserved.json:1`). Restore whole contracts; keep harmless relocation/diagnostic/rejector renames and justified verified-open/bounds hardening. Static restoration recommendations are not proven crash fixes. No device commands, source patches or binary patches were executed.

## Complete comparison counts

The main rows below count **defined ELF function-symbol records**, including local functions and aliases. PLT/init/fini blocks lacking STT_FUNC are listed separately, so generated linker stubs do not inflate the main numbers. Same-name local duplicates receive deterministic address-order suffixes and remain separate records.

| Artifact | R155 / NEW functions | Changed | Added | Removed | Normalized equal | Total differing functions |
|---|---:|---:|---:|---:|---:|---:|
| host | 209 / 219 | 42 | 11 | 1 | 166 | 54 |
| child | 58 / 107 | 25 | 64 | 15 | 18 | 104 |
| runtime-provider | 86 / 99 | 14 | 32 | 19 | 53 | 65 |

All **353 old + 425 new function-symbol records** and **70,320 decoded AArch64 instructions** are covered; executable section bytes equal decoded bytes for each file, with zero uncovered instructions. This does not discover additional source functions optimized away or inlined. Ten zero-size symbol records use explicit next-symbol/section-end ranges. Instruction equality is not a proof of data, dependency or runtime equivalence. Evidence: `results.json:1` and `evidence/<component>/<version>/coverage.json:1`.

[ALL-FUNCTIONS.md](ALL-FUNCTIONS.md) lists every changed/added/removed function and linker block with disposition. [function-assessments.json](function-assessments.json) has per-row original disassembly line numbers, explanation, address-resolved diff and register-number-erased diff. Full unchanged records remain in `evidence/<component>/functions.json`. `TOP20.md` is the shorter review entry point.

## ELF metadata, symbols and strings

| Artifact | R155 SHA prefix | NEW SHA prefix | Imports + / - | Exports + / - | Allocated printable-run + / - |
|---|---|---|---:|---:|---:|
| host | 1f6cf53b | 02c611c8 | 3 / 2 | 7 / 0 | 23 / 3 |
| child | 0976dee8 | 587e7a85 | 7 / 3 | 1 / 0 | 96 / 51 |
| runtime-provider | 80c9aee0 | 8d109259 | 5 / 5 | 1 / 0 | 47 / 59 |

Full SHA-256, paths, sizes, DT_NEEDED **order**, SONAME/RUNPATH/FLAGS/FLAGS_1 and version-qualified symbol changes are retained. SONAME, RUNPATH absence and both flags fields are unchanged in all three pairs. No exported name is removed. Provider adds `libwestlake_art_abort_bridge.so` before `libart.so` and `libbase.so` after it, and removes `libopenjdkjvm.so`. Child DT_NEEDED is unchanged. See each `metadata-diff.json:1`, `versioned-symbols-diff.json:1`, and raw LLVM `dynamic.txt:1`, `symbols.txt:1`, `versions.txt:1`.

Host PT_TLS remains 48 initialized zero bytes, memsz 48, alignment 16, flags R. Child/provider have no PT_TLS. Host resolved init targets remain `__do_init`, `_init`; fini remains `__on_dlclose_late`, `__do_fini`. Child has neither array. Provider retains `__do_init` and adds `_GLOBAL__sub_I_westlake_android_runtime_provider.cpp`; fini targets retain order. Arrays are resolved through RELA, not compared as zero-valued on-disk slots. See each `inventory.json:1` and metadata semantic projections.

| Artifact | RELATIVE (1027) | GLOB_DAT (1025) | ABS64 (257) | JUMP_SLOT (1026) |
|---|---:|---:|---:|---:|
| host | 47 → 48 | 10 → 12 | 1 → 1 | 191 → 190 |
| child | 28 → 46 | 0 → 0 | 0 → 0 | 32 → 36 |
| provider | 7 → 8 | 10 → 10 | 1 → 1 | 69 → 69 |

Counts are independently cross-checked against LLVM relocation dumps; identical counts do not imply identical symbols. Full per-section counts and targets are retained in the raw dumps. Section offsets/sizes/flags/content hashes, allocated strings versus non-allocated debug strings, and symbol-table attributes are independently inventoried, including 1,503 printable-run set deltas. Printable runs have minimum length four and include incidental constant bytes: the report does not pretend every printable run is a path or configuration key. Each difference has a disposition and reason in its `*-diff.json`.

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

Validation: seven offline tests pass, including full hashes, LLVM relocation counts, function/executable-byte coverage, complete per-delta trace, negative normalization controls, corrected provider predicates/call ownership, and byte-for-byte unchanged host/child evidence. Lifecycle results and review status are recorded in `lifecycle-task56.json`; source restoration judgment requires review, not a test-only claim. Repository known-answer suite and exact counts are in `validation.json`. R2: inventory **verified**; function behavior/restoration design **partially**; device behavior/root cause **unverified**. No screenshot or runtime success claims.
