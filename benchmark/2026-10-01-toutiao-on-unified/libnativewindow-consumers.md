# libnativewindow.so consumers static scan — U9 full corpus (166 keys), 0 consumers (offline)

Dispatch (ACK(90) 2026-10-01T20:07:13): scan all U9 full-corpus APKs' `lib/arm64-v8a/*.so` NEEDED entries for `libnativewindow.so`; anchor: toutiao must appear.

## Numbers first

- Scanned: **66 original keys** (`~/a2hlab/app-inputs/<key>/*.apk`) + **100 cv2 keys** (`$WORKSPACES/westlake-inputs/corpus-v2/app-inputs/<key>/*.apk`).
- Consumers with NEEDED `libnativewindow.so`: **0 .so rows** / **0 keys**.
- Anchor: **toutiao NOT in list** → STOP per dispatch.

## Why the anchor failed (dispatch premise error, not scan error)

- toutiao's `lib/arm64-v8a/*.so` NEEDED entries are `liblog.so`, `libm.so`, `libstdc++.so`, `libdl.so`, `libc.so` — **no `libnativewindow.so`**.
- libnativewindow.so is not consumed by any of the 166 keys in the U9 full corpus.

## Conclusion

No libnativewindow consumers in the U9 full corpus. The U10 facade's libnativewindow implementation has zero regression risk on this corpus. The libjnigraphics.so consumer scan (161 rows / 37 keys) is the relevant regression set for the U10 namespace change.

## Method

- `llvm-readelf -d` on each `lib/arm64-v8a/*.so` in each APK.
- Deduplicate by key (multiple .so per key counted once).
- Join with outer-signoff.json (U8 verdict) for regression candidates.
- No board writes; all files in t4 worktree.
