spec: project
name: "U8 three-freeze scoring preparation"
---

## 意图

Score a future complete outer U8 visual signoff against three immutable prediction cohorts and compare all 166 keys with their signed U7 baseline.

## 约束

- Offline only; do not mutate any frozen CSV or previous scoring result and do not write devices or push.
- Formal scoring requires exactly 166 signed unique keys with U8 state; a 100-key cv2 replay is explicitly a fixture, not U8 evidence.
- Unknown prediction means abstention, not predicted failure; functional lit differs from WebView fallback.
- An ActionBar risk tier is not a binary t20 prediction. No late-page non-execution can be labeled a disproved wall from a lit screenshot.
- Visual signoff does not supply an exception root, API checkpoint or exact APK byte attestation.
