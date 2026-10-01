spec: project
name: "F-Droid corpus-v2 selection"
---

## 意图

Select one hundred new F-Droid packages for the next U7 baseline, prioritizing low-native local applications and preserving twenty Compose/WebView/GL coverage samples.

## 约束

- Work offline on supplied index bytes in this worktree; use official source links for published metadata.
- Do not change apps.json, install apps, move input files or claim screenshots from package metadata.
- Keep downloaded APKs and the full index outside the public repository; record exact identities and compact selection evidence.

## 排除范围

- APK input preparation, signature acceptance, deployment and final frozen sixty-six-key U8 prediction.
