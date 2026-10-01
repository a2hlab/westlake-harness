spec: project
name: "WebView startup impact before U8"
---

## 意图

Predict the seven WebView-cluster apps against the no-renderer provider-cache fix before U8 observations.

## 约束

- Offline only; do not write devices or modify previous freezes or scores.
- SHA-bind selected APKs, runtime candidate and source evidence.
- Distinguish startup, later page and unresolved callbacks; references alone do not prove execution.
- Removing getProvider exceptions is not functional WebView content; preserve unknown visual outcomes.
- Freeze CSV and register SHA before U8 starts; if it starts earlier disclose late rather than backdate.
