# Native deployment preflight: master landing

Master had the strict N1/N2 checkers but lacked the deployed `deploy_generation` entry point and its approved baseline table. Consequently the signed U5 package rejected 131 known findings. This change imports the exercised deployment entry point and trusted preflight adapter, without changing either scanner or the master frozen checker/registry.

## Evidence

- Real U5 manifest `7bc02de7`: dry-run PASS, 28 N1 + 103 N2 findings explicitly EXCEPTED, zero remaining rejection; no device I/O.
- Real N8 manifest `3dd48299`, without a window grant: dry-run REJECT, 31 N1 + 154 N2 findings, zero exceptions. The A table cannot authorize N8.
- The permanent table is the exact approved 02:30:26 table: SHA `d40f3b9d44d248fd6b7b665aa90b78bd35464db60e42ea90c275b1ce85d7a9da`, 257 entries. U5 has 131; the N5-bound baseline subset has 126. All entries bind package, sidecar and finding, state reason/evidence/removal condition, and retain approval attribution. Their two U5 evidence files are included unchanged. These exceptions record accepted uncertainty, not proof that each finding is harmless.
- Temporary N5/N6/N7/N8 experiment rows are not in the registry. The optional experiment reader still requires serial, exact candidate/counts and an active bounded timestamp. Restoring a separately approved baseline does not depend on a failed candidate's expired grant.
- 10 hook tests cover forward modes, missing inputs/readelf, immutable bindings and restoration; 6 frozen tests retain pre-mutation refusal; the registry audit checks exact bytes and evidence existence. Lifecycle has three passing scenarios.

## Deployment boundary

The deployer runs artifact freeze checks and trusted repository N1/N2 before dry-run success, Mac-to-VM dispatch, or board construction. The ticket binds payload hashes, sidecar contents, checker bytes and exception table; the VM checks it again. Candidate-provided checkers are not imported. Upgrade verifies the previous owned package before mutation. Rollback requires an owned state receipt and validates the actual restoration package and boot/serial identity; it cannot claim a raw underlay is approved.

The public entry point was absent on master, so this landing includes the full existing deployer (same-platform upgrade, single replacement/addition, mount journal and rollback). It is copied from the tested cx-t0 branch, not rewritten. `source-identities.json` records hashes and source commits. Production board execution is not part of this landing test. The checker still limits artifact freezes to declared paths; source freeze audit remains the separate master `check_frozen.py --git` operation.

JAR/image overlays remain distinct from native deployment: preserve their receipt, temporarily expose the native package's JAR during an authorized native swap, and restore overlays before app tests. This commit does not implement the proposed U7 compound transaction executor and does not authorize a board window.

## Review and reproduction

This branch is based on master `7bd0060b5`; cherry-pick the landing commit after review. It does not require cherry-picking N8 candidates or the entire cx-t0 history. Do not copy a whole worktree over master. No native binary, temporary grant, or runtime/JAR payload is included.

```
python3 benchmark/2026-10-01-native-gate-landing/test_predeploy_hook.py
python3 benchmark/2026-10-01-native-gate-landing/test_registry.py
python3 scripts/lab/test_deploy_frozen.py
NATIVE_READELF=llvm-readelf scripts/lab/deploy_generation.sh <serial> <U5-package> --dry-run
```

`gate-results.json` summarizes real dry-runs; compressed raw logs retain findings. Neither a dry-run PASS nor a successful deployment establishes app lighting; screenshots remain a separate acceptance gate.
