# B10 scanner v3 — offline, timeboxed

V2 left compiled AOSP JNI tables unattributed and confused startup risks with final fatal causes. V3 adds explicit class/table ownership, compiled ELF evidence and separate fatal/prerequisite backtests. No device operations or runtime repairs were performed.

Run from this worktree with the pinned local package/APK inputs (Python 3 and Android build-tools 37.0.0):

```sh
python3 benchmark/2026-09-29-static-wall-prediction/scan_jni.py --output benchmark/2026-09-29-static-wall-prediction/v3/jni-results.json
python3 benchmark/2026-09-29-static-wall-prediction/publish_jni_v3.py
python3 benchmark/2026-09-29-static-wall-prediction/scan_risks_v3.py
python3 benchmark/2026-09-29-static-wall-prediction/finalize_v3.py
cargo test --manifest-path tools/spec-checks/Cargo.toml b10_
python3 scripts/lab/jni_gate.py --package /Users/zhaoyue/orca/workspaces/westlake-generation-v3-74d1d6d4 --matrix benchmark/2026-09-29-static-wall-prediction/jni-results.json.gz --allowlist benchmark/2026-09-29-static-wall-prediction/jni-allowlist.json.gz
```

AOSP source is the existing read-only real-work frozen slice, `frameworks/base` commit **99b01a65**, tagged **android-16.0.0_r2**; no download was needed. Exact paths/tags are in `v3/evidence/aosp-provenance.json:1`; every attribution includes source file/line, explicit registration, ELF table address, function symbol and compiled-file check. ART's AOSP14 version was not used to infer the framework version.

Each package gains **1,434 registered methods**. Known JNI answers remain **6/6**. After the unchanged **6,554 approved exceptions**, v3 has **335 unknown blockers** (previously 1,450); 6cb has **335 unknown + 4 missing + 50 stub**. Both gates still reject. Of the remaining unknowns, 155/package have direct calls in the 20 APKs; nothing was automatically approved (`v3/jni-summary.json:1`, `v3/jni-blockers.csv:1`). A source table alone is insufficient; cache validation also hashes the attribution scanner and its source inputs.

Machine entrypoints: `jni-matrix.csv.gz`, `service-matrix.csv.gz` (unchanged 421-row v2 inventory), `predictions.csv` (40 rows), `wall-ranking.csv`; new `v3/risk-matrix.csv.gz`, `v3/jni-delta.csv.gz`, `v3/jni-blockers.csv`, `v3/backtest.csv`, and `v3/coverage-gaps.csv`. Rich evidence is in the corresponding JSON/gzip files. The **134 risk rows** cover dlopen/Flutter paths, Koin, WorkManager and nullable startup service/context contracts. Risks remain conditional; startup counts are bounded static paths. `stub_ok` and `needs_real` remain separate (`v3/risk-results.json`, `v3/wall-ranking.json`).

Backtest (`v3/backtest.json:1`): #75 final-fatal first-wall agreement is **v2 1/12 → v3 5/12**; any-candidate coverage is **11/12**, with the display/window failure still missed. This is retrospective, and the receipt lacks observed APK hashes: exact-identity denominator **0**. The shared caught theme-sync exception is not counted as the fatal cause. #78 uses the original frozen **2d8c9a54** predictions: coverage **1/13**, OONI's evidenced JobScheduler prerequisite **1/1**, exact final-fatal label **0/1** (WorkManager initialization). v3/v3a are different profiles; service comparison is conditional, exact-generation denominator **0**. The other 12 APKs stay unscored, including the different-SHA noice alias.

Validation: **14 tests pass**, including real bridge-removal rejection, wrong-class/overload negatives, source/dependency cache invalidation and approved-exception preservation. Contract lint **100%**, four v3 scenarios pass (`v3/evidence/lifecycle.json`, `regressions.txt`, `gate-regression.txt`). Unresolved JNI, runtime namespace/initialization behavior, screenshots and process survival remain unknown. Commit is left to the outer lane.

Class-absence extension (#80): `scan_classes_v3.py --cohort benchmark/2026-09-29-static-wall-prediction/v3/classes/cohort.json`, then `finalize_classes_v3.py` and `package_v3.py`. See `v3/classes/README.md`: **33 memberships / 32 unique APKs**, 38,872 grouped rows; r13 **13/14 interfaces have definitions**, missing `IConnectivityManager` reaches **15 bounded startup graphs**. Known answer 1/1 retrospective; class presence is not loading/initialization success. Two added scenarios pass.
