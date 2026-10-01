spec: project
name: "Corpus-v2 APK evidence and prediction freeze"
---

## 意图

Replace repository-index priors with offline APK evidence before the expanded corpus reaches any device.

## 约束

- Work only in this lane; preserve the original candidate list, old apps.json and all frozen predictions.
- Device actions and screenshots are outside this task. Own-ui remains a prediction rather than a measured result.
- Reuse the existing B10 JNI, service and native evidence rules; unresolved registration, reflection, dispatch and namespaces remain unknown.
- Freeze only one hundred exact candidate identities with verified signer fingerprints and complete APK scans bound to a runtime profile.
