# Production-path evidence review

Token: `video-1919-production-evidence-review`.
Reviewed commits: f5e89d436f, 3156da234a, 0437f9880e (tip0437f9880e4901b4301c984d6c8ad6bab64f05a7).
Verdict: **revise the inference/checkpoint before relying on it for the next repair**. The raw evidence itself is authentic. This review finds no new defect in the previously accepted deployment executor and does not impose another platform gate.

## Standards

1. CHECKPOINT.md:7 gives a non-existing player path under `$WORKSPACES/../.local/share`. The real file is `$HOME/.local/share/westlake/toutiao-video-r2-gate-inputs/apk-lib/libttmplayer.so`, independently hashed to the stated b427614d… identity. Fix the locator only. The APK path exists and hashes to a1112a0c… .
2. Nine added raw REA JSON files match actual session-cache originals after only HOME-prefix sanitization (structural comparison). All15 changed files equal the requested commit blobs. The Java files are correctly described as derived/annotated decompiler extracts, not authored upstream implementation source. The original cache exists; the generic provenance placeholder is not a usable locator. Preserve a portable locator plus original SHA (source-pins.json does so without exposing the username-encoded directory).

## Spec

1. **Substantive overload mismatch** — REA-PROVENANCE.md:31–35 joins the six-argument TTVideoEngine.proxyUrl caller to a zero-reference result for a different five-argument overload. The raw DEX descriptors prove the difference (overload-evidence.json). CHECKPOINT.md:18 therefore cannot infer that the internal play path does not use that public chain. Keep the valid five-argument zero-using-node result, but remove the chain-dead-end/exclusion claim; inspect/trace the actual six-argument descriptor or leave its upstream callers unknown. Static results still do not exclude reflection/JNI/hotfix.
2. CHECKPOINT.md:16 `crash gone` must be limited to the original OBJECT/FUNC fault not recurring in the bounded r4 observations, with sampled GOT bindings corrected. It is not random-crash elimination, full player-load proof, or playback acceptance. The subsequent r5 pre-video exits remain separate, unexplained observations.
3. CHECKPOINT.md:9 calls :71884 an r4 crash stack, while the already committed player-log-gate-and-datapath.md:38 identifies it as a caught screen_brightness Settings exception. Cite the exact original log/SHA/range and call it an observed Java call-stack slice, not a new fatal-crash fact. At CHECKPOINT.md:25, the missing production log does not prove why it was absent. Also reconcile REA-PROVENANCE.md:27's pending-caller assertion with :33's correct UNKNOWN owner.

The doPrepareAction extract supports setDataSource and a play branch as static source evidence. It does not by itself identify the MDL/direct choice actually taken by the clicked content. No new runtime modification follows from this review. No board calls, build, REA invocation or old tests were run; no frozen packet was edited. The public report contains only small metadata and exact method identifiers, not commercial decompiler bodies or private logs.
