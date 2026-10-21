# R3 guardian video successor: independent delta review

The previous video tools accepted the r2 guardian root and cfg. This successor changes those two bindings while preserving the runtime candidate, transaction, UI execution and recovery code. This review does not establish a fresh board baseline.

Author commit: `9d07b318349049709ca09b62b502ec24aedc92ef`. The actual derivation reproduced all 19 outputs. Six real-entry host tests passed, including unsigned preparation, rejection of old/mixed/foreign controls, preserved identity/runtime guards, pinned transport preview and recovery verification. Source hashes were unchanged after replay.

Independent byte comparisons confirmed that the executor differs only in cfg SHA and guardian root, the reference differs only in cfg and 18 controls, and both candidate descriptions, binder, executor source pins and execution/recovery drivers remain identical to their donors. Every helper pin was checked against its actual source. See `results.json` and the two replay receipts. Receipt argv use explicit source aliases; no device command was executed.

For replay, resolve `$MAIN` to the main checkout, `$SUCCESSOR` to `benchmark/2026-10-21-t34-demo61b-video/guardian-r3-video`, and `$GUARDIAN_PACKAGE` to the published `reentry-retirement-01/deploy-package-r3-root`. Run the recorded commands with the recorded environment.

**Result: accepted for offline successor integration only.** A new readback of the r3 cfg and all controls, runtime and process identities, and outer authorization with the exact holder/start remain necessary. No runtime, screenshot, audio or retention result is claimed.
