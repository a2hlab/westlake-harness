# ANativeWindow_lock / ANativeWindow_unlockAndPost consumers static scan — U9 full corpus (166 keys), 30 keys / 38 rows (offline)

Dispatch (ACK(90) 2026-10-01T20:10:27): scan all U9 full-corpus APKs' `lib/arm64-v8a/*.so` for undefined references to `ANativeWindow_lock` / `ANativeWindow_unlockAndPost`; anchors: toutiao and fd-plus must appear.

## Numbers first

- Scanned: **66 original keys** (`~/a2hlab/app-inputs/<key>/*.apk`) + **100 cv2 keys** (`$WORKSPACES/westlake-inputs/corpus-v2/app-inputs/<key>/*.apk`).
- Consumers with undefined `ANativeWindow_lock` / `ANativeWindow_unlockAndPost`: **30 keys** / **38 .so rows**.
- By source: original-66 = 36 rows / 28 keys; cv2-100 = 2 rows / 2 keys.
- Anchor: **toutiao IS in list** ✅ (7 .so rows reference ANativeWindow_lock/unlockAndPost); **fd-plus NOT in list** → STOP per dispatch.

## Why fd-plus is not in the list (dispatch premise error, not scan error)

- fd-plus's `lib/arm64-v8a/libOsmAndCoreWithJNI.so` references **`AndroidBitmap_lockPixels` / `AndroidBitmap_unlockPixels`** (bitmap lock, not window lock) — not `ANativeWindow_lock` / `ANativeWindow_unlockAndPost`.
- The two symbol families are different: `AndroidBitmap_*` locks pixel buffers for bitmap operations; `ANativeWindow_lock` locks a window's surface for CPU rendering.

## Verdict distribution (by key, U8 sign-off)

| Verdict | Keys |
|---|---|
| lit | 10 (aegis, fd-android, fd-binaryeye, fd-droidify, fd-gallery, fd-k9, fd-tusky, wikipedia, cv2-com-armanmaurya-archiv, cv2-de-markusfisch-android-shadereditor) |
| dead | 13 |
| unknown | 13 |
| alive-black-window | 1 |

**Lit keys (regression candidates for U10 namespace change):** aegis, fd-android, fd-binaryeye, fd-droidify, fd-gallery, fd-k9, fd-tusky, wikipedia, cv2-com-armanmaurya-archiv, cv2-de-markusfisch-android-shadereditor.

## Method

- `llvm-nm -D --undefined-only` on each `lib/arm64-v8a/*.so` in each APK.
- Deduplicate by key (multiple .so per key counted once).
- Join with outer-signoff.json (U8 verdict) for regression candidates.
- No board writes; all files in t4 worktree.
