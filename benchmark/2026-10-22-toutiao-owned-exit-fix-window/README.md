# T52: natural exit classification validated, baseline restored

The owned watchdog previously treated some natural process-exit races as ownership refusal. T50 fixes that classification; this window tested its exact T51 package through the normal boot chain on 5cd.

The candidate produced `classified=gone` and `classified=zombie`, continued recovery, then reached `RETRY_LIMIT`. Its captured views remain white. The restored original baseline subsequently displayed the Toutiao feed. **Neither close/reopen nor white-screen repair is accepted; this is not a seal.**

- [Actual window report](WINDOW-REPORT.md), [machine results](results.json), [independent outer checks](independent-checks.json), and [outer disposition](execution-review.json), and [independent peer review](review/actual-review.md).
- [Signed plan](plan.json) and [original authorization](outer-review.json) bind the temporary candidate and exact rollback. [Preparation README](README.pre-execution.md) preserves the earlier pending state; it is historical.
- [T50 source and reproduction](../2026-10-22-toutiao-owned-exit-fix/README.md) and [T51 package recipe](../2026-10-22-toutiao-owned-exit-fix-package/README.md) remain the implementation/build authority. This changes harness recovery control, not a newly frozen Android-to-OH API.
- [Candidate t30](evidence/candidate-t30.jpeg), [candidate final](evidence/candidate-after.jpeg), [restored baseline](evidence/restored-baseline.jpeg). Images are tied to their actual phase, not substituted between versions.

Four normal boots; window approximately 810 seconds. Six original controls, runtime124/boot36, host identity and power settings were restored, then the device lock was released. The last observation began 3.217 seconds beyond the 180-second limit; the final candidate screenshot began 3.809 seconds beyond it. These deviations remain failures of the timing requirement, so there is no full contract PASS.

Original command evidence is persistent and independently SHA-verified: see [raw integrity](raw-integrity.json). The signed original file-list hash is retained as `plan-files-original.sha256`; its original `README.md` bytes are now `README.pre-execution.md`. Plan, helper and env bytes have not changed. The current `SHA256SUMS` indexes the post-execution publication.
