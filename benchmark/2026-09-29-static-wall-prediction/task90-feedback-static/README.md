# Task90 feedback: static requirements for missed families

The frozen v4-r2/r15c comparison missed CommonEvent JNI, guest-thread readiness and ordinary native loader dependencies. This extension reuses the bounded startup graph and scans **32 exact APKs × seven families = 224 explicit verdicts**; it merges these latent requirements with the 66-key task90 observations in predictions.json/csv. Original v4-r2 and task90-r15c outputs remain frozen.

Run from repository root:

    python3 benchmark/2026-09-29-static-wall-prediction/scan_feedback90.py --out /tmp/task90-feedback-reproduce
    cargo test --manifest-path tools/spec-checks/Cargo.toml b90_

| Family | APK references | Bounded startup reachability |
|---|---:|---:|
| CommonEvent wrappers → native registration requirement | 31 | 22 |
| JobScheduler / WorkManager startup services | 23 | 16 |
| ShortcutManager | 23 | 4 |
| Flutter loader → guest-thread readiness | 6 | 4 |
| JNA native resource loading | 2 | 2 |
| EGL/camera JNI wrappers | 7 | 1 |
| APK ELF DT_NEEDED dependencies | 27 | unknown |

These counts are static requirements, not apps proven blocked. A wrapper/API reference does not establish missing implementation, and a library present in the package does not prove namespace visibility. All missing_implementation fields stay unknown. Native dependency rows preserve selected arm64 entry names, library hashes, DT_NEEDED and app/package provider presence, with runtime scope explicitly unknown. Calls through arbitrary app-defined aliases and reflection can be missed. Every DEX site has a line/offset and bounded startup path where available; no path means unknown, not unreachable.

matrix.csv/json includes no-static-evidence rows. Evidence is compressed JSON with original DEX locations and startup paths. provider-inventory.json pins reviewed v3a package libraries; it is not a live r16 mapping inventory. predictions.json keeps observed_wall_order separate from candidate_wall_order, which includes latent static requirements. No new first-wall certainty is manufactured from a latent reference.

Training evidence is r15c plus already-disclosed r16 sanity notes. This revision has **no prospective hit-rate claim**. Six Rust-dispatched checks pass across the observation pipeline, network gating, ranking, batch completeness, rule positive/negative cases and static matrix coverage. Additional runtime behaviors and unclassified exceptions remain unknown. Latest available full batch at delivery is r15c; r16 full-run evaluation waits for completed records, without needing further permission.
