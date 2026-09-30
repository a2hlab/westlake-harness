# N9 damage premise checked; candidate paused

The empty `Region` argument is **not evidence of empty compositor damage**. OH6.1 graphic_surface `0bf226a1f0a79fdbad70a0ac5565002ce69e942c`, `surface/src/native_window.cpp:245-263`, explicitly fills one rectangle `{0,0,GetWindowConfig().width,GetWindowConfig().height}` when rects is null or the count is invalid. The public header defines `Region` as **pointer first, count second** and documents the full-buffer default.

The local system-library copy has SHA `8f1879f8...f4a3`, identical to the previously captured 5ea system inventory (`benchmark/2026-10-01-n5-baseline-gates/snapshot.json`). Its disassembly implements that fallback. Retained bridge `84695d62` at `aanw_queueBuffer+0xf4` (`0xd6758`) clears x3 before the flush call: rects is null. The wrong one-int source declaration leaves the count register unspecified, but this binary's null pointer still forces the full-window fallback. This establishes this particular call's branch, not general ABI correctness.

The remaining unanswered question is whether the first `GetWindowConfig` width/height are zero or stale relative to the queued buffer. No live trace proves that. We have not changed the ABI declaration, damaged rectangles, bridge source or binary. An explicit first-buffer rectangle would test a **dimension-source** difference, not simply empty versus full damage.

Outer ACK(90) at 06:01 paused N9. No candidate package or build was produced. Also, retained bridge source/object provenance is incomplete; see [the provenance report](../2026-10-01-bridge-846-provenance/). Replacing it with a known different bridge cohort would invalidate a single-change claim. Await cc-t3's compositor trace and the outer decision.

`upstream/` preserves the read-only source/header retrieved from hw248. `results.json` pins hashes and revision. The two disassemblies are from unchanged local artifacts. No board access occurred in this investigation.
