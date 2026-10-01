# libjnigraphics.so consumers static scan — U9 full corpus (66 original + 100 cv2)

Dispatch (ACK(90) 2026-10-01T19:41:39): scan all U9 full-corpus APKs' `lib/arm64-v8a/*.so` NEEDED entries for `libjnigraphics.so`; anchor: toutiao at least 13 `.so` rows must appear.

## Numbers first

- Scanned: **66 original keys** (`~/a2hlab/app-inputs/<key>/*.apk`) + **100 cv2 keys** (`$WORKSPACES/westlake-inputs/corpus-v2/app-inputs/<key>/*.apk`).
- Consumers with NEEDED `libjnigraphics.so`: **161 .so rows** / **37 keys**.
- By source: original-66 = 159 rows / 35 keys; cv2-100 = 2 rows / 2 keys.
- Anchor: **toutiao's 13 .so rows ARE in list** ✅ (toutiao has 13 `.so` with NEEDED libjnigraphics.so).

## Verdict distribution (by key, U8 sign-off)

| Verdict | Keys |
|---|---|
| lit | 10 (aegis, fd-android, fd-binaryeye, fd-droidify, fd-gallery, fd-k9, fd-tusky, wikipedia, cv2-com-armanmaurya-archiv, cv2-de-markusfisch-android-shadereditor) |
| dead | 13 |
| unknown | 13 |
| alive-black-window | 1 |

**Lit keys (regression candidates for U10 namespace change):** aegis, fd-android, fd-binaryeye, fd-droidify, fd-gallery, fd-k9, fd-tusky, wikipedia, cv2-com-armanmaurya-archiv, cv2-de-markusfisch-android-shadereditor.

## Per-key consumers (sample)

| Key | .so count | U8 verdict | Source |
|---|---|---|---|
| toutiao | 13 | dead | original-66 |
| aegis | 2 | lit | original-66 |
| fd-android | 2 | lit | original-66 |
| fd-binaryeye | 2 | lit | original-66 |
| fd-droidify | 2 | lit | original-66 |
| fd-gallery | 2 | lit | original-66 |
| fd-k9 | 2 | lit | original-66 |
| fd-tusky | 2 | lit | original-66 |
| wikipedia | 2 | lit | original-66 |
| cv2-com-armanmaurya-archiv | 2 | lit | cv2-100 |
| cv2-de-markusfisch-android-shadereditor | 2 | lit | cv2-100 |

## Method

- `llvm-readelf -d` on each `lib/arm64-v8a/*.so` in each APK.
- Deduplicate by key (multiple .so per key counted once).
- Join with outer-signoff.json (U8 verdict) for regression candidates.
- No board writes; all files in t4 worktree.

## Outer-loop reading (2026-10-01 19:47)

The 10 lit consumer keys do **not** show that libjnigraphics.so resolves today: in their U9 runs (t5 maps), none of
their consumer libraries is mapped -- aegis / k9 / android / droidify / shadereditor `libimage_processing_util_jni.so`,
binaryeye `libzxingcpp_android.so`, gallery's four image codecs, tusky `libavif_android.so`, wikipedia
`libmaplibre.so` are loaded on demand (camera, image decode, maps), not at startup; their hilogs never mention
libjnigraphics. So cc-t3's prediction (unresolvable today) stands, and adding libjnigraphics.so to shared_sonames
cannot change these apps' startup -- any effect is on those feature paths. Regression watch for U10: open one such
feature on a lit key (e.g. a wikipedia map, a gallery AVIF) after U10 lands.
