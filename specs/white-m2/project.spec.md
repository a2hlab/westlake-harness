spec: project
name: "M2 WebView route evidence"
---

## 约束

- Offline and read-only: no deployment, renderer candidate or package modification.
- Signed screenshots remain ground truth; native controls are not proof of WebView content rendering.
- Preserve app PID, artifact identity and absent instrumentation; only conditional predictions may exceed zero.
