# U7 compound generation format — offline prototype

The existing native package cannot express an inseparable boot-image/stubs change alongside a runtime JAR. Sequentially calling today's native deployer and then adding Java mounts would restart appspawn between components, exposing an intermediate generation. This proposal keeps the parent stopped across the entire transaction. **No new device writer or deployable release is delivered here.**

The final example follows outer ACK(95) 04:57: **U5/N4-order native + J7b `381110a6` + T7d stubs `d8b2406e` and its 27 images**. N8 is a separate unaccepted candidate for a later generation. `example-identity.json` identifies the example directory and complete hashes. Nothing was installed on a board.

## Format

`bundle.json`, schema `westlake-generation-bundle/v1`, contains:

| Component | Members | Binding |
| --- | --- | --- |
| `native` | Existing complete generation package | Child package.json SHA plus all sealed payload hashes; unchanged native sidecar |
| `boot_group` | Exactly 9 segments × art/oat/vdex + adapter-mainline-stubs.jar | One 28-member target→SHA map and group digest |
| `runtime_jar` | oh-adapter-runtime.jar | Separate target and SHA |
| `reference` | Recorded U5 runtime and boot fingerprints | File SHA plus parsed target→SHA maps |

All package members are relative regular files below the bundle root. Absolute/traversing/symlink sources, unexpected image targets, duplicate targets/sources, missing members, byte drift, or undeclared native payload files are rejected. Native package code is not executed. Trusted validators come from the repository/master checkout.

The group identity is the SHA256 of the sorted canonical JSON target→SHA map. A comparison adapter may count the whole boot group as **one variable only after verifying its exact 28 targets and hashes**; it must still list all 28 component differences. An arbitrary partial image change is not eligible for grouping. The native and runtime-JAR groups remain separate. This prototype does not modify `compare_runs.py` or suppress its current raw differences.

## Gates and fingerprints

`generation_bundle.py --dry-run` validates structure and bytes, derives a complete expected target map, and produces a non-executable transaction plan. It has no `apply` switch and never creates a Board, runs hdc, locks a device, mounts, or restarts anything.

- G1/G2 reuse `knowledge/toolchains/art-r155/image_predeploy_gate.py` from master, with `swap_jars=[adapter-mainline-stubs]` and G2 always required. No caller flag can label this image-changing transaction data-only. G2 uses the actual candidate BCP (eight native-package jars plus the selected stubs), not the reference BCP for both sides.
- The real T7d example passed G1 and G2; String.hashCode matched **36 instructions to 36**. Remote host oatdump was used through the existing wrapper; no board was accessed.
- The same example without oatdump failed G2 and returned exit 2. Missing or skipped required evidence is not a pass.
- G1's swapped-segment exemption is not itself proof that a JAR was used to build the image. A production bundle must retain the builder's receipt binding all nine input JAR hashes, the dex2oat/toolchain identity and all 27 output hashes. The currently copied stage manifest lists image hashes but lacks that complete receipt; the example records this gap rather than inventing one. Actual G2 loaded the supplied paired BCP successfully, which is additional compatibility evidence, not source-build provenance.
- Native N1/N2 are run against the native child package with the trusted current master registry. The master registry currently contains **0 exceptions**, while this worktree contains 257 previously approved entries (131 for U5). Actual U5 package/input identities still match those local entries. Strict master checking therefore rejects **N1 28 + N2 103**, with no scanner errors. We did not copy exemptions into master or grant the new bundle authority. Both identities and the registry discrepancy are retained in the results.
- Frozen artifacts are checked against the composed expected hash map, using master's registry. The real example has zero artifact violations. Source-only freezes still require the normal build/source checks; absence from an artifact report is not proof of their verification.
- `probe_fingerprints` use the same sorted `sha256sum` line encoding as master batch, separately for the reference runtime target set and the 36 boot targets. The whole-target map also has an independent digest; private libraries outside the batch glob are therefore not silently omitted from bundle identity.

The design does not allow a native-only exception grant to authorize arbitrary Java overlays. A future release receipt must bind the complete bundle digest, every child identity, gate input/checker/registry hashes, original board baseline and outer approval.

## Stopped-parent transaction and recovery

1. Validate all bytes, image pairing, G1/G2, N1/N2 and frozen rules before requesting the board window. Stage all components and rollback files; verify staged SHA before changing mounts.
2. Under the lane lock, capture boot_id, current package receipt, every mount layer and runtime-JAR source, full baseline hashes, and absent-target ledger. Reject drift. Record both bundle and native generation identities; they are not interchangeable.
3. Stop only receipt-owned Android apps and verify their children exited. Stop appspawn-x with begetctl. Keep it stopped while switching native, all 28 boot-group members and runtime JAR. Each completed mount operation is journaled; do not claim that 28 Linux mounts are a kernel-atomic operation.
4. Verify the complete target map before starting the parent once. Verify the parent/child root views, one ART instance, route-a openjdk owner, bridge version, both fingerprints, and all component hashes. Then run the externally scheduled controls.
5. On any failure, stop new children/parent and restore **all components**, including the exact original JAR layer stack. Remove only receipt-owned additions whose prior state was recorded absent. Verify original hashes before restarting and after child creation. Unlock only after successful restoration; failed rollback retains the lock and reports the journal.
6. On reboot, replay starts with a fresh boot_id and baseline discovery. Never reuse stale mount IDs or blindly pass upgrade against a previous boot's receipt.

The existing `sweep_bind_deploy.py` (master e8924c4df) already demonstrates the 29 Java bind operations and scoped rollback for sweeps. `deploy_generation.py` already demonstrates native hash checks, owner receipts and rollback. A production U7 executor needs their **stop/stage/activate/verify/rollback primitives**, with parent restart removed from intermediate activation. Calling the current full commands sequentially does not satisfy this design. This work deliberately stops at the format, gates, plan and dry-run boundary.

## Reproduce and validation

Run `prepare_example.py` once in the normal workspaces layout. For schema and negative tests:

```
python3 benchmark/2026-10-01-u7-generation-format/test_bundle.py
python3 scripts/lab/generation_bundle.py --package "$WORKSPACES/westlake-generation-u7-format-example-u5" --dry-run --out /tmp/u7-plan.json
```

For real gates add `--run-image-gates --oatdump <trusted oatdump_remote.sh> --run-native-gates --readelf <host readelf>`, with `LAB_HOME` configured per RUNBOOK. Current master exceptions produce exit 2 for native findings. `deployable` remains false even when all requested offline checks pass, since no board executor/acceptance is provided.

The unit fixtures use tiny fake files for schema/path/transaction checks; they do not stand in for G1/G2. Real-artifact gate outputs and the missing-G2 negative are stored separately. No screenshot or survival count is claimed for this offline task.
