# T122 ordinary rendering-stage boundary

**PARTIAL: no proven public API defect/candidate.** New since the previous T122 review: both failed runs progressed beyond session/node creation to NativeWindow return and BLAST surface delivery; their later positive boundaries differ. This review does not repeat JSON/dependency-warning analysis.

Original full-file line numbers (`$HOME/.local/share/westlake/t122-hdc-outer-check-20261024/collection-01/{7011,9860}-payload.stdout`), compared with successful `$HOME/.local/share/westlake/startup-stage-coverage-20261023/extended-01/head.stdout`:

| Marker | 7011 | 9860 | Success6291 |
|---|---|---|---|
| Activity transaction posted | 1188 | 754 | 1420 |
| Session created | 2722,4298 | 2735 | 4360,7179 |
| Relayout | 3441,4077 | 3310 | 5274,5873 |
| NativeWindow returned | 3597 | 3503 | 5623,8777 |
| BLAST surface | 3604 | 3508 | 5639,8782 |
| UI RS post | 3530 | 3436 | 5485,7973 |
| UI RS completed | 3853 | not logged | 5868,8868 |
| EGL swap entry | not logged | not logged | 6945,10939 |
| EGL swap return | not logged | not logged | 6965,7076 |

The table groups stage types; `results.json/ordered_evidence` preserves actual file order, including UI-RS post before NativeWindow completion. Thread interleaving prevents treating file order as a single-thread call chain or elapsed time.

- **9860:** main session39 returns NativeWindow at3503 and BLAST surface at3508, after UI-RS post3436. The next selected success-path witness absent here is UI-RS callback completion (success5868); subsequent visible-relayout and EGL submission markers are also not logged. Absence does not prove non-execution or explain why.
- **7011:** main session31 has BLAST surface3604, UI-RS completion3853, visible relayout4077 and another BLAST update4137. The next selected submission witnesses absent are EGL swap entry/return (success6945/6965). Later popup session33 at4298 is a different window, not further main-window progress.
- There is no explicit full traversal-completion witness. Queue entries and JIT compilation of `performTraversals` are not execution/completion proof. Initial relayout visibility8 also appears in successful6291; it is not a demonstrated API defect. RS flush or EGL rc1 alone is not first-content-frame proof.

Source/identity handoff, bounded and now closed: exact index `sources/api-implementations/shared-native-production/source-index.json` labels `related-source/framework/window/jni/oh_window_manager_client.cpp` (SHA357ca49f…) and `related-source/framework/android-runtime/src/android_view_SurfaceControl.cpp` (SHA1740a425…) **RELATED_ONLY_UNPROVEN**. These are related snapshots, not proven deployed producers. The ordinary Java marker exists in `sources/api-implementations/source-build-host/westlake-java/framework/window/java/WindowSessionAdapter.java:1088`; local lines1080–1126 compute dimensions, print visibility, then call visibility/rect/surface operations. Last-touch/import commit `d19faba2dbed410431e511e9193ac6d5f04d1a7d` is **not** a producing build commit; exact deployment binding remains unknown. No deeper source/binary search follows.

T106 `benchmark/2026-10-23-cross-board-startup-inputs/comparison/results.json` binds these native identities for successful6291 and older5cd successful21639, not directly for failure7011/9860:

- `libhwui.so`: `a11c9154ca16dd7acf5e3ea99727ae37c25b1b4494a9133816bc58c553c128e2`
- `liboh_adapter_bridge.so`: `b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4`
- `liboh_android_runtime.so`: `8ab6742d58de5b9df94a2bfa80cebed46f136c0251083793fcbef8293cc23ab1`
- `liboh_hwui_shim.so`: `5e54081289d112c8819f1ceec2dbf1b3bc4b4b6bbeacba28db9283487fd2cf1c`

Full source/index pins and observed deployment paths/PID/birth are in `results.json`; cx-seal owns any further producer chain review. Native equality does not prove Java/BCP source equality. Success6291 is a different board/run and longer sample, not a controlled experiment.

Minimum remaining ordinary observation gap: same-main-session UI-RS completion for9860; traversal/draw completion and first EGL submit entry/return for7011. Marker producer/build binding must precede any interpretation of absent markers as code conditions. No new collection/instrumentation is performed or proposed as an implementation fix.

Reproduce evidence extraction with `python3 benchmark/2026-10-24-ordinary-log-suffix/render-stage/evidence.py`. Only these three deliverables are written. No device/REA/runtime edit/push, stopped implementation or fault/protection analysis; no raw logs copied into the repository.
