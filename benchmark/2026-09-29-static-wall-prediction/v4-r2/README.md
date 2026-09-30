# Task85 — five static wall families

The earlier table omitted window attributes, own-service binding, VelocityTracker, bionic imports/header checks and SharedPreferences return contracts. This version emits **160 verdicts / 32 APKs**, retaining the prior r13 class-risk columns in the new prediction CSV.

Run from the repository root:

    python3 benchmark/2026-09-29-static-wall-prediction/run85.py --out /tmp/b85-fresh-scan
    python3 benchmark/2026-09-29-static-wall-prediction/backtest85.py --triage <auto_triage.json>
    python3 benchmark/2026-09-29-static-wall-prediction/publish85.py
    python3 benchmark/2026-09-29-static-wall-prediction/package85.py
    cargo test --manifest-path tools/spec-checks/Cargo.toml b85_

The first command reproduces the detector in a fresh directory; the following commands score/publish the released freeze in v4-r2. The scanner refuses to overwrite a freeze. Inputs are the existing 32 hashed APKs, v3a ELF export set, prior JNI matrix and source window-flag policy. No device command or runtime change.

Machine entrypoints: **hits.csv**, **predictions-v3a-r13.csv**, **family-summary.csv**, **backtest.csv**, **coverage-gaps.csv** and **unmodeled-observations.csv**. Per-app evidence gives DEX method/line/offset, conditional startup paths, selected arm64 ELF header hashes and strong/weak bionic imports. source-references.json supplies detector/source file lines. Flags include LayoutParams constructors; own-service class co-reference is a candidate, not proven Intent flow. JNI unknown stays unknown. Valid ELF headers do not predict runtime “header failed”; symbol versions and effective namespaces are unresolved.

Prediction freeze: **18:11:36 +0800**, before undisclosed r14 outcomes were read. Seven APK clicks occurred after this freeze, including the held-out fd-stk window-family case (timestamps in backtest.csv). The 18 board-disclosed keys are seed cases. Seed five-family candidate coverage is **6/6**; first-new-family agreement is **2/6**. Held-out five-family coverage is **1/1**; held-out first-family agreement **0/1**. A zero denominator is unknown, never a pass. Outcome-blind evaluation is not a claim that these predictions predate the existing board run.

At this cutoff, **32/32** predictions have exact, finished APK records among **66** triaged run rows. Missing/unclassified/out-of-cohort rows are explicit. #83's old system-library loader warnings are excluded using the corrected #84 triage; a warning without an exit cannot be a first-fatal hit. No screenshots or process totals are claimed.

Validation: **3/3 scenarios pass**, lint **100%**, including rule negatives, strong/weak import distinctions, frozen hashes and seed/held-out/nonfatal partitions. Broad API hits are candidates, not precision or proof of execution. Frozen detectors were not tuned after reading results.
