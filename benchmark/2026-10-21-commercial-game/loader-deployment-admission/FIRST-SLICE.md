# G19 first slice

Not ready for deployment. Existing entry points are located; no new orchestrator or ownership state was created.

- `scripts/lab/deploy_generation.py:143-161` single-file replacement requires exactly one changed package source and one changed live target. The two independent U13 loader aliases cannot be represented by one `--replace` transaction. `--upgrade` is multi-target but requires an owned verified current-boot resident state and an exact complete package.
- `scripts/lab/u7_executor.py:51-65,293-329,336-367` is the U13 stopped-parent multi-target apply/rollback implementation. It expands both aliases, journals each bind before applying it, and reverses them under a stopped parent. Its complete bundle, actual baseline, native/static inputs and paired image receipt prerequisites remain to be qualified; G18 is an ELF evidence package, not that deployable bundle.
- One read-only 5ea query was attempted: `readonly-01/`. HDC returned rc0 but `Connect server failed` on stderr and zero stdout. This is transport failure, not a boot/mount/SHA observation. No retry, alternate transport, environ read or device write follows.
- Latest existing normal-ui-02/attempt2 final-boot receipt: `a1d869b4-69a2-40a4-937e-4860f5b54239`, recorded `2026-10-21T18:50:38.732942+08:00`. None of six local `westlake-generation-state/5ea.../*.json` receipts belongs to that boot. The current boot is unknown after the failed query; no historical state is admitted as current.

Next: pin reusable sources and exact U13 baseline/restore artifacts, identify hash consumers without duplicating cx-seal's call-chain analysis, and deliver an explicit false admission with the smallest remaining gaps.
