# 2026-09-26 operator layout79 (#48)

Diagnosis of the post-hollow-stub failure: `IllegalArgumentException: Layout: -79 < 0`
(ArticleInflowActivity, main thread, exit(1)) + classification of the `work_thread`
SIGABRT banner. No new binary artifact — analysis only.

## Layout

| Path | What |
|------|------|
| evidence/layout79-window-collapse-48.txt | Root cause (OH_WSA window-width collapse 1200→1px, screenWidthDp=0 → title StaticLayout width = collapsedWidth − card chrome ≈ −79), fix direction (clamp WindowSessionAdapter.relayout / outMergedConfiguration output, never emit width ≤1 / screenDp 0), and work_thread SIGABRT classification (SI_TKILL "…is null" background abort, non-fatal, in survivors too). |

## Verdict
- Layout −79 = geometry (window collapse), constant, RECURRING (stub-r1 survivor also ends in it), not content-specific. Dominant remaining wall after heap corruption was eliminated by the hollow npth stub.
- work_thread SIGABRT = non-fatal, pre-existing background noise present in all rounds; distinct from both mallocng SEGV and the Java −79. Do not merge.
