# One-row append: review02 offline candidate

Base main observation JSON: **`104484cbeaf64b1f406627b73791ed8c3cc9e250e6126a9fca848800cc5ab36e`**, 64 rows. The isolated proposed JSON has65 rows; all64 old row objects and all top-level metadata are unchanged. No main file was written. The candidate remains `BUILT_OFFLINE_REVIEW02_BOARD_VALIDATION_PENDING`, not verified or frozen. Snapshot01158c remains historical within the same new observation; no second row is added.

The new row uses only canonical main source/test/recipe/build evidence, including `candidate-build-02`. Its **26 exact references pass**, and the unchanged renderer generated the **one-row preview** with rc0. The row records the actual1422 offline assertions, including loop iterations; it does not claim device acceptance.

## Existing full-table red gate

Both the unmodified64-row baseline and65-row proposed table fail the same original renderer check. Two old rows reference `benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh`: expected `c2855d54eb7acea0502731a5be5c1310a6d9471048beae11df59d8186a3b0667`, current main `0862a334f863d4de3bf3d4c4dda7ab1df7c6000e3b0e3d02e6c46f014aaf84d3`. The mismatch is pre-existing; neither row nor script was altered. All1624 old reference occurrences were checked, with only these two occurrences failing.

**No full65-row HTML/CSV was generated or claimed.** `row-preview/` is a diagnostic single-row render, never a replacement for the full canonical table. Generated relative links assume the renderer's canonical placement. `views/observations.json` is the full additive data proposal; `new-row.json` permits rebasing on newer main without overwriting concurrent additions. `merge-map.json` states the intended destinations and the outstanding existing gate.

Baseline, appended and row-only renderer stdout/stderr/rc are preserved privately and summarized with hashes in the corresponding public receipts. No old evidence was repinned to make the gate green. Historical315 files remain unchanged. This package performed local rendering and hashing only.
