# B92 handoff to cc-wiki

Baseline reproduced byte-for-byte: runtime-provider `a24bc454`. Candidate `0509fe23` repeats identically in two builds. NEEDED order and export sets unchanged. ANL `a9c9187d` combines oc-t4 READY policy with the existing v2 permitted-path fix; 138 host checks pass, including permitted-path escape negatives.

5ea remains owned by cc-wiki. cx-t0 performed no device writes.

## Apply

Before deployment, preserve the v4 Java overlay receipt, temporarily unmount it back to the package r8b (`d5000c4e`). The deployer checks the resident package JAR. Installer receipt already records the accepted `eb6824b4`; do not replace installer. Boot must remain `1afff219-03f6-48cf-a566-54ddbba66d0e`. If changed, stop and replay the current baseline first.

Run these in order under cc-wiki lock. Both are single-file replacements of the actual route-a load path. The old android alias binds intentionally remain untouched in this experiment; v3c will unify aliases. Never use the unused `westlake-b92-anl-system-a9c9187d` intermediate package.

```sh
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh 5ea34a4500000000000000001123012c /Users/zhaoyue/orca/workspaces/westlake-b92-anl-route-a9c9187d --replace /system/lib64/westlake/route-a/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac/libapp_native_loader.so --lane cc-wiki
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh 5ea34a4500000000000000001123012c /Users/zhaoyue/orca/workspaces/westlake-b92-bigstack-0509fe23 --replace /system/lib64/westlake/route-a/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac/libwestlake_android_runtime_provider.so --lane cc-wiki
```

The deployer restarts appspawn-x and runs the HelloWorld child SHA/maps/single-ART/846 bridge check for each replacement. It rolls back its current single file on failure. Then reapply the same v4 JAR (`2fbfd8bc`) using its existing overlay procedure, preserving Java as the controlled variable. Run master bms_batch Wikipedia and HW/ZigZag with preflight, `--hilog 20 --shots 5,20 --focus-check`.

Require maps to show `libapp_native_loader.so` and `libwestlake_android_runtime_provider.so` from the route-a directory, and verify SHA through the child root. Require `[CM-BIGSTACK] ActivityThread on dedicated pthread stack=...` >= 8 MiB and launcher detach rc=0; compare fatal exception and screenshot to prior inflate stack crash. Screen success remains human review.

## Rollback

Remove the temporary v4 overlay back to r8b before the deployer SHA checks. Roll back in reverse order, then reapply the original v4 overlay:

```sh
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh 5ea34a4500000000000000001123012c /Users/zhaoyue/orca/workspaces/westlake-b92-bigstack-0509fe23 --replace /system/lib64/westlake/route-a/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac/libwestlake_android_runtime_provider.so --rollback --lane cc-wiki
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh 5ea34a4500000000000000001123012c /Users/zhaoyue/orca/workspaces/westlake-b92-anl-route-a9c9187d --replace /system/lib64/westlake/route-a/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac/libapp_native_loader.so --rollback --lane cc-wiki
```

Original SHA per target and all candidate hashes: `replacements.json`. No APK, ART, child plugin, appspawn host, installer or boot image changes.
