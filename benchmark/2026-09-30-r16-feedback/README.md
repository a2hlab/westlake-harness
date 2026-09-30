# R16 post-evaluation static feedback

The prospective run overestimated recovery after JobScheduler/network changes and omitted several service/provider contracts. This new scan is explicitly trained on r16 outcomes. It does **not** alter or improve the already-scored r16 forecast retroactively.

32 pinned APKs × eight requirement families produce **256 explicit rows**. coverage.csv keeps all 66 run keys; 34 remain outside this static APK cohort. matrix.csv/json retain call locations, hashes, bounded startup evidence and unknown runtime-failure status. family-summary.csv separates total references from startup reachability.

| Requirement | APK references | Bounded startup paths |
|---|---:|---:|
| Service foreground / activity-manager attachment | 27 | 4 |
| Battery service | 1 | 0 |
| Vibrator / vibrator manager | 20 | 0 |
| PendingIntent | 31 | 5 |
| AlarmManager | 25 | 2 |
| Process CPU-time JNI | 1 | 1 |
| DocumentsProvider permission contract | 2 | 2 |
| Storage / Environment initialization | 27 | 6 |

Zero bounded paths means unknown execution reachability, not safe/unused. Several r16 failures are outside the available 32 APKs. Arbitrary app subclasses, reflection, asynchronous callbacks and framework-internal calls remain limitations. Empty service stubs must still satisfy typed/non-null return contracts; marking stub_ok is a first-screen implementation policy, not proof that returning null is safe.

Known-answer correction: both matched DocumentsProviders already declare MANAGE_DOCUMENTS in their APKs: Termux manifest line 155 and Minetest line 72, with provider attributes recorded in evidence/providers-*.json. The static manifest-gap count is therefore **zero**. Runtime MANAGE_DOCUMENTS failure must be investigated in installed/projected ProviderInfo rather than falsely attributed to missing APK declarations. Inherited or unrecognized DocumentsProvider subclasses remain unknown.

Run from repository root:

    python3 benchmark/2026-09-30-r16-feedback/test_feedback.py
    cargo test --manifest-path tools/spec-checks/Cargo.toml r16_feedback

scan.py is the reproducible scanner entry and refuses to overwrite an existing freeze. Its input cohort and scanner hashes are recorded in freeze.json. For a rerun, copy this scanner/rules into a new sibling benchmark directory with the same repository-relative predecessor layout, or remove only disposable outputs in an isolated checkout; never overwrite the prospective directory.

R2: static references and the two manifest permission declarations verified; runtime null/missing-implementation and repair causality unknown. No devices, APK writes or git operations. Two checks pass and the original prospective SHA manifest is verified unchanged.
