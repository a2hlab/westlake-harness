spec: project
name: "Corpus-v2 immutable scoring and scanner feedback"
---

## 意图

Score late-frozen predictions against the outer reviewer and improve offline evidence without rewriting historical predictions.

## 约束

- Preserve the v1 CSV, freeze receipt and all v1 code and evidence byte for byte.
- Unknown is abstention, never a predicted failure. Distinguish functional UI from WebView fallback UI.
- Do not touch devices, push, or infer fatal causes from a dead verdict without target-PID evidence.
- New scanner results are retrospective and must not be reported as held-out validation.
