spec: project
name: "Disabled U13 native assembly draft"
---

## 约束

- Offline only; no deployment, board operations, registry application or current bundle edits.
- Exact U12 bf6c0fb6 / 2a3fac81 base; any confirmed Stage A regression requires outer review.
- Compose runtime18763dd4, VLCcompatb2be657c and policyb8be63d2 only.
- Hold hostc2883376; preserve U12 host2a87118e and boot/JAR paired receipt.
- Root/route aliases change and roll back atomically. Raw gate failures are evidence, not success.
- Dry-run surface labels require actual OS evidence; a Mac client timeout is not a VM pass.
