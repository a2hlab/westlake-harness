# r4 deploy inputs (four files; executor = cx-seal CAS r6 draft)

r4 ADDS one derived file to r3; r3's three files are unchanged.

| # | physical target | after | source |
|---|---|---|---|
| 1 | `$RT/run.sh` | `79275cf9` (WID-derived) | `../../candidate-r2/deploy-inputs/run.sh` (r3 reuses it) |
| 2 | `$RT/libopensles_android_compat.so` | `9f558aaf` | `../../candidate/deploy-inputs/libopensles_android_compat.so` |
| 3 | `$RT/lib/arm64-v8a/libmffmpeg.so` | `d2882303` | r3 derive (`../../candidate-r3/derive_mffmpeg.py`) |
| 4 | `$RT/lib/arm64-v8a/libttmplayer.so` | `5fba8050` | **r4** derive (`../derive_ttmplayer_selfrel.py`, from b427614d) |

The two derived `.so` (mffmpeg, ttmplayer) are large and not committed; recipes are. Each replaced physical lib gets a single-file backup (`...ttvideo-before-<boot8>`) and rollback. Preimages/metadata from `video-r4-readonly` / `video-r3-readonly`.
