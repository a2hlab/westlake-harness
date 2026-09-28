# M05 Bionic/Musl Reliability Risk Register

Status at base `c919f07c347ceba092b6b5112cb9daa1eefaec15`: no current M04
candidate is available, so every candidate-specific risk remains open and
`device_admission=false`.

| ID | Boundary / risk | Required discriminator | Owner of next evidence | Current status / stop-line |
|---|---|---|---|---|
| M05-R00 | Canonical verifier contract: the lane names `BIONIC-MUSL-UNITY-INDEPENDENT-VERIFIER-BOOTSTRAP.md`, including S1-S7, but it is absent | Hash-bound local canonical document and explicit S1-S7 mapping | integrator | **BLOCKED INPUT**; M05 must not invent stage semantics |
| M05-R01 | Current-byte provenance can drift across source, APK, Unity DSOs, loader, bridge, Musl and providers | `NativeGenerationReceiptV1` with local paths, SHA256, byte size, ELF identity, generation token and immutable source/input manifests | M04 + integrator | **OPEN**; no offline-generation receipt; this receipt does not prove runtime readiness |
| M05-R02 | Old 22/22 runtime-generation PASS can be transferred to new bytes | Import exactly 22 named gates from the local canonical source, bind each result/evidence to the current generation, rerun all | integrator supplies source; M05 reruns | **BLOCKED INPUT**; canonical `A12/runtime-generation-redteam/**` is absent |
| M05-R03 | Flat/ambient symbol resolution or duplicate providers select a wrong ABI implementation | Recursive `DT_NEEDED` and strong-UND closure, unique provider identity, namespace/search-path receipt and wrong-provider mutant | M04 produces; M05 verifies | **OPEN**; missing current ELF/provider graph |
| M05-R04 | Loader path/FD race admits bytes different from the inspected file | Opened-FD dev/inode/size/hash receipt, sealed lifetime, mapped ELF SHA/Build-ID equality | M04 produces; M05 verifies | **OPEN**; missing sealed-FD receipt |
| M05-R05 | `FILE*`, pthread/TCB/TLS objects or C++ objects cross domains as opaque memory | Crossing ledger classifies every edge `direct`, `translated` or `unsupported`; wrong-owner mutants fail | M04 produces; M05 audits | **OPEN**; missing crossing/ownership ledger |
| M05-R06 | Allocator/free domain mismatch, double free, UAF or unload lifetime leak | ASan/UBSan/LSan lanes where available, owner-tagged alloc/free matrix, fault injection and unload regression | M05 | **NOT RUN**; no candidate/harness |
| M05-R07 | TLS key, stack guard or fork epoch is stale on main/pthread/JNI/callback/post-fork/signal entry | Six-entry generation/epoch/guard oracle before first guest instruction plus publication and stale-epoch mutants | M04 produces; M05 stress-verifies | **NOT RUN** |
| M05-R08 | Mutex/cond/rwlock/once/sem split lock domains, lost wakeups, weak-order failure or deadlock | 10M-op stress, N-first-use and mixed-inline/wrapper mutants, watchdog stack/wchan/futex evidence | M05 | **NOT RUN**; host/QEMU cannot close ARM64 device risk |
| M05-R09 | Signal layout corruption, recursive handler or installed-but-not-delivered false green | 8B/128B canary, delivery oracle, nested/altstack/fault cases and timeout stack | M05 | **NOT RUN**; historical shell result is only a negative oracle |
| M05-R10 | Namespace create/open/close/reset leaks FD, thread, TLS key or stale handle | Repeated lifecycle with pre/post baselines, stale-generation mutant and monotonic-slope rejection | M05 | **NOT RUN** |
| M05-R11 | Crash, futex hang, D-state/device freeze and HDC loss are conflated | Four distinct fault corpus outcomes with pid/starttime/generation, threads, wchan, Binder/futex and watchdog dumps | M05 + integrator device lane | **NOT RUN**; no device request in round one |
| M05-R12 | Process survival hides stalled presentation or growing resources | Same pid/starttime/generation; frame/present progress; FD/thread/maps/RSS/PSS slopes; 5-minute interaction then 30-minute bounded soak | integrator device lane; M05 verifies | **NOT RUN**; does not prove first frame |
| M05-R13 | Prebuilt Unity inline/TLS/syscall paths bypass an apparently complete symbol bridge | Exact APK-entry SHA/Build-ID plus relocation/disassembly classification and runtime hit/canary/fault evidence | M04/M07 produce; M05 audits | **OPEN**; symbol existence alone is rejected |
| M05-R14 | Stub, no-op, hijack or app-specific shim is reported as production behavior | Inventory with owner, reason, removal condition, test and scope; unsupported paths fail explicitly | owning module + M05 | **OPEN**; no current inventory |
| M05-R15 | Host/self-test evidence is promoted to candidate/device/Unity PASS | Machine rule keeps `product_claim=false`; self-test admission is impossible; device labels require exact device receipt | M05 | **CONTROL IMPLEMENTED** by the baseline validator |
| M05-R16 | Offline generation identity is mistaken for a live child ready for attach | Separate `ChildRuntimeReadyReceiptV1` bound to `SpawnBirthReceiptV1`, pid, startSeq, generation and epoch; all bindings match the offline generation | process/spawn owner + integrator; M05 verifies | **OPEN**; no child-ready or spawn-birth receipt; runtime gates remain `not_run` |
| M05-R17 | Unfrozen HP-9 or sibling-project code enters the verifier/product generation | Project-local freeze receipt before use; reject 02d and every non-standard sibling source | integrator | **BLOCKED INPUT**; HP-9 is not frozen into 02 and is not consumed |
| M05-R18 | M05 silently changes an OH system-service patch | Read-only by default; any future need is an integrator-approved exact-file request | integrator + owning module | **NOT TOUCHED** in round one |

## First failure gate

`F00_REQUIRED_LOCAL_INPUTS` is the first gate: the canonical bootstrap, the
22-gate red-team source and an integrator-approved M04
`NativeGenerationReceiptV1` must all exist in this worktree and be hash-bound.
Even after F00, runtime attach is independently stopped until
`ChildRuntimeReadyReceiptV1` binds `SpawnBirthReceiptV1`, pid, startSeq,
generation and epoch. Until then, runtime gates are `not_run`, not inferred
failures or inherited passes.

## Explicitly not proven in round one

- Correctness or completeness of any M03/M04/M07 product implementation.
- The meaning or satisfaction of S1-S7 while the named canonical bootstrap is
  absent.
- Admission of any current bytes, true-device behavior, Unity loading, first
  frame, interaction, 5/30-minute stability or resource convergence.
- That older shell, test-APK, QEMU, host, warm-run or device-readback artifacts
  belong to the current generation.
- Runtime readiness from `NativeGenerationReceiptV1`, or any property of HP-9
  while its source is not frozen into this project.
