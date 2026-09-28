# B6 task 44: live admission repaired; HelloWorld class linking blocked

The missing ART C bridge was an omitted recipe source, now restored unchanged.
The real-work cohort passes strict host linking and the live identity gate, but
HelloWorld exits 1 with a primitive-return-type `LinkageError` before UI.
Both trials were fully rolled back; B5 HelloWorld and ZigZag screenshots are restored.
See the [current task 44 report](task44/README.md), [current results](results.json),
and [prior task 41 results](task44/prior-task41-results.json). Lit delta remains zero.

The following task 41 report is retained as historical evidence; its missing-bridge
blocker is resolved by task 44.

# B6 task 41: generation rebuilt; activation and replacement route blocked

The original inference that the `libartbased.so` probe meant a missing debug
dependency was wrong. The decisive first-trial failure was an unfinished Android
entry in latest `00.Workspace` cd5b329: it returns -3007 unconditionally, and the
child maps that to exit 210. The complete candidate was rolled back. The newly
authorized real-work route has an implemented entry but fails strict host linking
against the fixed AOSP14 ART provider. **B6 remains blocked; lit delta is zero.**

## Current blocker: real-work interface

Source `real-work` be16148da9ae7bb89c62e81e144ed0bceb5c4669 implements
`WLAR_EnterAndroidAfterStockSpecialization`: it validates prerequisites, commits
A02 handoff and calls `ChildMain::runAfterStockSpecialization`. Its
`appspawnx_runtime.cpp:52` also requires
`westlake_art_copy_fault_message_for_abort_logging`. The compiled consumer has
that undefined symbol; rebuilt `libart.so` 889de8d0 does not export it. The
real-work provider recipe fails with `-z defs`, `--no-undefined`, and
`--no-allow-shlib-undefined` intact. No fallback implementation was added.

See [source excerpts](real-work-entry/source-excerpts.txt),
[link failure](real-work-entry/strict-link-failure.txt) and
[interface receipt](real-work-entry/results.json). The original **26/26 provider
outputs remain byte-identical to their saved second-build hashes**. This second
route stopped before generating a new manifest/child/host and made zero board
writes, as explicitly required for an incompatible provider interface.

## Completed host work

- AOSP14 r1 plus historical patches recovers runtime.cc and class_linker.cc
  exactly. The final fingerprint inventory is **16,909/18,060 exact, 348 missing,
  803 different**. Header/generated/metadata deviations remain enumerated; see
  [recovery report](art14-recovery/README.md).
- Unified OH 6.1 compiler b107ce03 compiled ART **245/245**, strict bridge
  **55 units**, ICU **199/199**, androidfw **26/26**, and the native runtime.
  The original 26 providers reproduce byte-for-byte over two builds. Added
  OpenJDK JVM also reproduces separately over two builds.
- Final ABI inventory covers **33 libraries** (5 lack an R155 counterpart),
  comparing exports, NEEDED, SONAME and sections. This is an inventory, not proof
  of runtime equivalence. No claim that all differences are diagnostic is made.
- Latest00 generation `44865eb264fd2168160b69498cf3e68a9554d6e6a42fe9298c0e2cc895805180`
  passed generation and TGR product verification. Only the tuple-receipt predicate
  was waived under the user's explicit instruction: its generator and historical
  receipts could not be found. All other checks remained active
  (`art14-recovery/tuple-waiver.json`).
- Host NEEDED closure: **34 required, 338 reachable, 3,023 edges**, zero unresolved.
  Four original negatives plus a false absent-SONAME declaration were rejected.
  The new ART's four sigchain APIs are covered; removing each export blocks
  admission in the symbol negative controls. `sigaction` belongs to platform
  musl libc; new live binding was not verified.

## First candidate trial and complete rollback

Only 5ea was locked and written. Candidate host **5c97aff6**, child **ef547828**,
ART **889de8d0**, and sigchain **6d5d5538** were staged as one cohort. Deployment
replaced all existing provider aliases, both TGR paths and the native roots;
`deployment.json` records **36 mounts** and their previous SHA values.

HelloWorld child **11441** exited **210**. Its final image is the OH desktop:
[evidence/helloworld-r1/final.jpeg](evidence/helloworld-r1/final.jpeg).
Source and disassembly both show the unconditional -3007 return
(`art14-recovery/provider-entry-*`). Wikipedia, NPE and candidate ZigZag were not
run after the failed first control. WLCGATE writes stderr, which
`AppSpawnEnvClear` closes. Exit-path analysis suggests admission advanced, but
without raw gate messages or the late sigchain mapping **live identity is not
claimed passed**.

All **36 mounts were removed and every original target SHA restored**. The B5
host is **1f6cf53b**, child **0976dee8**, JAR **250958dc**, with unchanged boot ID.
Regression observation after rollback produced HelloWorld PID 14870 and ZigZag
PID 15878, without new faults. Both final screenshots were read: HelloWorld shows
its buttons/lifecycle and ZigZag its game title screen. These are **B5 recovery
proof**, not candidate-regression acceptance:

- [HelloWorld after rollback](evidence/rollback-r1/helloworld/final.jpeg)
- [ZigZag after rollback](evidence/rollback-r1/zigzag/final.jpeg)
- [Restored identities](evidence/rollback-r1/identity-after.txt)

The board lock is released. VM raw evidence is under
`~/a2hlab/board/b6-41-helloworld-5ea-r1`, `b6-task41-44865eb264fd`, and
`b6-41-rollback-5ea-r1`. No other board was touched.

## Validation and limits

Known-answer tests: **69 run, 2 skipped, 0 failures**. Fresh B6 lifecycle:
**3 pass / 5 fail / 0 skipped / 0 pending review**. Pass: caller identified,
absent-artifact negative, new-ART sigchain coverage. Fail: Wikipedia UI,
HelloWorld/ZigZag candidate regression, advancement beyond getTheme, NPE retest,
and live loader identity. `lifecycle.json` preserves every scenario verdict.

R2 verified: source fingerprints, deterministic host builds, static closure and
negative controls, both concrete blockers, complete rollback and baseline UI.
Partially verified: first-trial identity progression inferred from the exit path.
Unverified: repaired VM/boot-image compatibility, Wikipedia UI, NPE conversion,
and candidate ZigZag. The previous `null_check_mode=sigsegv` is retained with
explicit task-31 provenance; it is not a task-41 retest.

The deployment/observation scripts are historical, guarded 5ea trial recipes,
not automatic authorization to reactivate this failed candidate. Build recipes
under `art14-recovery/recipes` require the recorded recovered input trees and
must be restored to their corresponding staging locations; they are not a
standalone source bootstrap. Published path placeholders are account-neutral.

Public ABI receipts compact unchanged export lists to counts/hashes while retaining
added/removed symbol deltas. Full lists remain locally; hilog excerpts carry line
numbers and full-log hashes. Plain text strips trailing whitespace; patch files
preserve their context whitespace.
