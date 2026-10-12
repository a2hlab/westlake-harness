# Spare restoration acceptance proposal — pending user decision

The current task requires the spare selfcheck to match the original sealed fingerprint except its serial. No canonical-template mechanism exists in the current seal compiler, restore driver or selfcheck. Current 61b host UID is 20011206; freshly installed 5cd host UID is 20011300. Exact per-board control bytes consequently differ. No 61b seal has been signed yet and no derived-spare restoration is authorized by this proposal.

## Concrete transformation scope

| Object | 61b source | 5cd realization | Verification |
|---|---|---|---|
| Host identity | UID/GID 20011206 | UID/GID 20011300, read from installed original HAP | Same HAP SHA df385638..., exact BMS and directory evidence |
| UID-bearing scripts | Existing frozen Route B template | Only enumerated UID fields changed | Source/template/compiler SHA plus exact textual diff |
| Spawn request | Captured 672-byte request | UID/GID little-endian offsets 312/316 | All other bytes equal; field values checked |
| Startup board binding | 61b full serial | 5cd full serial | Exact literal substitution and authorization |
| Candidate control path | Existing 61b attempt | New independent 5cd attempt | Exact path substitution; no old state/data modified |
| Ordinary runtime and APKs | Frozen source hashes | Same bytes | Exact SHA equality for every non-derived file |

The proposed acceptance is an **explicitly declared equivalent spare realization**, not byte-identical restoration of the original 61b board. A realization document must pin the eventual original seal SHA, target serial/UID/boot, compiler and every input SHA, and every allowed old-target/hash to new-target/hash transformation. The generated target file map is independently reviewed and signed, then checked exactly on 5cd. Unknown differences fail. Original seal and existing exact comparison gates remain unchanged. The run report must name this acceptance and retain both manifests and all raw execution receipts.

Pending decision: allow this narrowly bounded equivalent spare rehearsal to satisfy the cross-board restoration requirement. If declined, retain the strict original requirement and report the cross-board rehearsal incomplete; do not manufacture success by excluding generated controls or calling a synthetic 5cd seal a serial-only copy. Main 61b runtime/guardian repair and regression preparation continue independently.

Evidence: ../2026-10-12-v1-seal-execution/5cd-host-install/, restore-5cd-preimages/, restore-spawner-source/; independent review PROGRESS(91) 2026-10-12T21:25:20+08:00. No board writes, gate changes, signing or acceptance changes are performed by this document.
