spec: project
name: "B10 actionbar and graphics construction impact predictions"
---

## 意图

Predict the 166-key impact of the actionbar theme wall and deployed graphics JNI constructors using APK resources, whole DEX and exact deployed native bytes.

## 约束

- Do not touch boards, push, or change runtime/scanner freezes and previous scoring results.
- Run artifact_identity before inspecting runtime bytes; current U7 expected-run is the analysis baseline, not an unobserved N10 candidate.
- Distinguish API references, bounded execution candidates, later Activity/callback candidates and observed failure calibrations.
- A compiled registration table does not prove RegisterNatives ran; an absent source attribution remains unknown.
- Counts are unique app keys, with duplicate APK identities disclosed; no static upper bound is claimed as an actual unlock count.
