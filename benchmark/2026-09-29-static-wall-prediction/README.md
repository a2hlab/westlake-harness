# B10 offline static scan — first delivery + requested v2 columns

Run from the worktree root (Python 3, Android build-tools 37.0.0 `dexdump`/`aapt2`; inputs are pinned by SHA-256). No device command is used.

```sh
python3 benchmark/2026-09-29-static-wall-prediction/scan_jni.py
python3 benchmark/2026-09-29-static-wall-prediction/scan_apps.py
python3 benchmark/2026-09-29-static-wall-prediction/extract_runtime.py
python3 benchmark/2026-09-29-static-wall-prediction/scan_reachability.py
python3 benchmark/2026-09-29-static-wall-prediction/audit_build.py
python3 benchmark/2026-09-29-static-wall-prediction/finalize.py
cargo test --manifest-path tools/spec-checks/Cargo.toml b10_
python3 scripts/lab/jni_gate.py --package /Users/zhaoyue/orca/workspaces/westlake-generation-6cb40cd6 --allowlist benchmark/2026-09-29-static-wall-prediction/jni-allowlist.json
```

The gate currently rejects both packages: missing/stub/unknown are uncovered, and every exception is still **proposed**. Review requires exact method, generation, overlay hash, status, reason, evidence and `approved_by`. `--matrix benchmark/2026-09-29-static-wall-prediction/jni-results.json` uses a cache only after checking package/input/source/scanner hashes; omit it for a fresh deployment check. The test removes the bridge ELF from a local package and verifies rejection, then tests complete fixture-only exceptions. No real approval is created.

Known answers: all **6/6** match. In 6cb40cd6, `nativeParseManifestJson`/`nativeGetSysProp` are missing and `SQLiteConnection.nativeOpen` is stub; in v3 74d1d6d4, they are exported/exported/registered. The `notification` route for fd-etar is missing; `user` is an r8b stub. Current Java source has later stubs that are absent from the pinned r8b d5000c4e JAR, so coverage uses compiled bytes. JNI totals are 5,406 declarations/package; **4,726 unknown/package** are not counted as covered. Evidence/provenance is in `jni-results.json`, per-app evidence, and `evidence/runtime-disassembly.json`.

Use `service-matrix.csv` (421 rows, 20 apps), `predictions.csv` (40 app/profile rows), and `wall-ranking.csv`. V2 adds `startup_reachable`, path evidence and separate `stub_ok` / `needs_real` queues. Ranking uses `startup_affected_apps`; `full_reference_apps` remains separate. `yes-static` means a bounded APK call path from manifest Application/launcher Activity/provider or explicit androidx.startup metadata, conditional on initialization and branch execution. Unresolved dispatch/reflection/framework callbacks remain **unknown**, not “off startup.” `stub_ok` is the user's first-screen policy and still requires the caller's return-value contract. Flutter path behavior is a `needs_real` runtime follow-up, outside this static verdict. The Typeface candidate cites the requested ZigZag log at line 3819 and remains unapproved.

Retrospective first-wall agreement: **v1 4/7; v2 5/7 (71.4%)**. This is not prospective accuracy: observations were already available. `backtest.json` records every comparison/exclusion for #63/#65/#68/#69/#71. Missing fatal receipts, different configurations and runtime namespace failures are unscored. #71's missing child logs are a **measurement gap** (outer correction: 256K buffer/private logging), not evidence about JAR behavior. No screenshot or liveness total is claimed here.

Build checks: `build-audit.json` records 65 changed regions in 27 scripts; actual P2-B source-collection checks reject four independent missing inputs and print their paths. Full cross-compilation was not run. Remaining archival/conditional candidates are listed as unknown under the requested first-version timebox; this is not a claim that the entire legacy script tree has been hardened. B9's exact required-bridge-source diagnostic is reused. Source implementation pointers are in the prediction rows.
