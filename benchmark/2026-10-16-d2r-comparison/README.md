# D2R Mobile transferability: evidence before acceleration claims

The earlier assessment described likely benefits without measuring a bridge development speedup. That is not evidence of an improvement already delivered. This review separates existing Westlake capabilities, an executed upstream technique, and future transfers. **No production Android/OH bridge change derived from D2R was delivered in this experiment; speedup remains unmeasured.**

## Executed experiment

Upstream is pinned to [211be64fcfbc6d73a4ec08fd238b42f1caa2181f](https://github.com/d2r-mobile/d2r-mobile/tree/211be64fcfbc6d73a4ec08fd238b42f1caa2181f). On macOS arm64, compile its actual `dm/host/entry.S`, `gate_test.c` and `gate_tramp.S`. Supply 60 **synthetic** entries: 58 counter-register combinations (x0–x29 except Apple's x18, for two counter kinds), one system-call gate and one observation gate.

| Implementation | Build | Execution | Result |
|---|---:|---:|---|
| Original upstream entry | 0 | 0 | 60 cases, zero failures |
| One deliberately omitted x10/x11 restore instruction | 0 | 1 | All 60 cases detect the defect |

See [raw output and source hashes](gate-experiment/results.json), [positive output](gate-experiment/original.stdout.txt), and [negative output](gate-experiment/missing-register-restore.stdout.txt). This demonstrates an offline check that distinguishes this calling-boundary defect. It does **not** measure elapsed bridge development time, cover the game's actual gate inventory, prove floating-point/vector preservation, or test our Android/OH implementation.

Reproduce on macOS arm64 with a C compiler and the three source files at the pinned commit:

```sh
python3 benchmark/2026-10-16-d2r-comparison/replay_gate.py \
  --source-dir "$D2R_SOURCE" --out "$NEW_EVIDENCE_DIRECTORY"
```

The replay checks the upstream file hashes before compiling and refuses an existing output directory. Original game assets are not needed for this synthetic experiment. Full D2R acceptance does need assets and reference recordings; its public repository does not supply all reference-recording drivers.

## What is transferable

| Technique | Concrete transfer to Android/OH | Evidence and boundary |
|---|---|---|
| Independent ABI boundary tests | Exercise argument/return and register preservation at native adapters before launching an APK | The 60-case experiment above; adapt to our actual boundary rather than copying Apple-specific x18 rules |
| Differential and mutation checks | Compare selected Android reference calls with OH calls, including errors and state changes; intentionally break adapters to test the assertions | [Upstream equivalence checker](https://github.com/d2r-mobile/d2r-mobile/blob/211be64fcfbc6d73a4ec08fd238b42f1caa2181f/dm/verify/equiv.py); its CPU rewrite tests do not automatically establish Android API equivalence |
| Fresh build verification | Rebuild with current sources, then compare selected outputs to the candidate | [Actual regression entry](https://github.com/d2r-mobile/d2r-mobile/blob/211be64fcfbc6d73a4ec08fd238b42f1caa2181f/dm/verify/regress.sh); existing Westlake provenance checks already cover a different part of this problem |
| Input-to-state assertions | Test a touch's resulting action, position or UI transition as well as screenshots | [Verification descriptions](https://github.com/d2r-mobile/d2r-mobile/blob/211be64fcfbc6d73a4ec08fd238b42f1caa2181f/dm/verify/README.md); the original recording drivers and game-specific states cannot be assumed available here |

## Existing Westlake strengths

These capabilities predate this comparison; they must not be credited to D2R:

- Cross-APK public-API freezing with multiple application evidence and guarded updates: [check_frozen.py](../../scripts/lab/check_frozen.py).
- Host/child library-open namespace analysis and native initialization/dependency gates: [open_site_scan.py](../../scripts/lab/open_site_scan.py), [native_predeploy.py](../../scripts/lab/native_predeploy.py).
- API-to-source/build/evidence correspondence: [315-row atlas delivery](../2026-10-14-api-source-delivery/README.md), with 392 source references and 143 non-null build entries. These are references/records, **not** counts of fully implemented APIs or reproducible complete applications.

The current local checks passed: open-site scanner 19 tests; frozen guard 19; native predeployment 19; atlas verifier 13. These 70 tests exercise tooling, not 70 APKs. [Results](results.json) retain the scope and upstream experiment. The separate [local evidence review](local-evidence.md) traces further deployment and multi-device claims.

D2R targets one specific game's Switch-to-Apple adaptation and explicitly excludes online game services; Westlake targets reusable Android application compatibility on OH. Cross-APK capability management and namespace/deployment diagnosis are stronger specializations in the reviewed Westlake evidence. D2R's fine-grained behavioral checks are a stronger reference for testing. Neither different scope nor this one experiment establishes overall technical superiority, graphics performance, or a measured speedup.
