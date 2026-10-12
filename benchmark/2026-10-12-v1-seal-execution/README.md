# v1 seal execution: not sealed

The previous offline checks missed a deployed executable-path mismatch: the Route B launch script executes `/data/local/tmp/asx/appspawn-x`, while three ownership guards accepted only the historical `asx-spawner` path. Candidate `0cc5a5bd` adds exact aliases while preserving all identity predicates. Independent review passed 18/18 inventory bindings and 6/6 tests. The rule is to compare every guard with the actual deployed launch command and captured process identity before a reboot.

The revised 23-member controls package was placed with exit 0 and per-member byte/metadata readback. A complete preboot snapshot, supplemental labels and 32 policy proofs preceded exactly one reboot for this revision. New boot `ad2ba003-0d0a-43d2-a85d-e023e7702db7` autonomously reached U13 READY with 56 layers and Permissive mode; all 319 baseline hashes match. No Mac runtime repair was applied.

**The seal failed its Toutiao acceptance.** Parent 4421 was accepted and child 5968 was spawned, but the guardian rejected child identity at uptime 66. The child was still present in the t20 process table and later died from signal 11 according to the parent reaper. These are separate observations; the failing guard predicate and native crash cause remain unknown. Both Toutiao snapshots show only the IME host. HelloWorld t20 is visually lit. Process liveness is not UI acceptance.

See `results.json` for pinned evidence. Raw process, parent and child logs stay in this directory; large stderr is not committed. `alias-round20` is prepared disabled for exactly 20 keys plus the existing 5cd 128-key reference; its legacy prepare stdout incorrectly prints 128. Regression, refresh/article acceptance and a real spare restore rehearsal remain pending. No acceptance or seal signature was issued. The board lock was released after this bounded window.

The independent API atlas is complete in `../2026-10-12-api-progress/API-PROGRESS.zh.md`. Restore adapters continue in isolated t0/t4 trees; 5cd only received its previously missing original host HAP, with actual UID 20011300. No restore success is claimed.

## Subsequent static closure (21:41 CST)

The original 221-file archive was an immutable suffix subset, not a complete restoration inventory. A live, stable-boot read matched 239 additional runtime files to retained local sources; their CAS copies were independently hash checked. The sets are disjoint. Fresh SHA checks match 218 of the original 221 files; exact diffs of the other three contain only host UID and `WL_PARENT_ID` changes. Per-file modes, ownership and labels are retained. See the four `restore-*` index files named in `results.json`. No restoration was performed.

The next child-readiness candidate is still under test and independent review. All required shell tools were read-only checked on the target. Twenty-three current controls were matched to retained preimages and the new helper path was proved absent. This preparation is not candidate approval or UI acceptance. The independent review also caught a shell global-variable collision before placement; that candidate must pass regression before deployment.
