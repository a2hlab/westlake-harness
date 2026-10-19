# Actual r10 build and reproducibility

The outer production build completed all 16 stages with rc=0. The stripped deployment artifact is `libopensles_android_compat.so`, SHA256 `5f591f5ed92e608a622ab4b59bb2061a846600d0ac5e5d4698405e6301ac8c3c`. Source, exact image/toolchain pins and output checks are in `build_candidate.sh`, `core-freeze.json`, and `deployment/build-review.json`. Remote durable archives and independent SHA/size verification are in `deployment/outer-window-admission.json`.

The original bind-mount build environment was unavailable. A dedicated zero-mount container with the same pinned image was used, with the exact repository and native toolchain copied into matching paths. `copy_dockbuild.sh` checks running container/image/zero mounts and only copies designated output files back; the original stdout, stderr and return-code files remain host-side. This changes transport, not compilation flags or source. The first actual attempt failed because the linker host dependency `libxml2.so.16` was absent. The pinned SDK copy supplied it, the complete build reran successfully, and both attempts remain archived.

To reproduce, restore the native toolchain archive and the exact r8 inputs described by the recipe, create a dedicated running zero-mount container from the pinned image, and copy repository/toolchain into the same paths used by that invocation. Ensure uid501 can write the output parent. Then run:

```sh
SOURCE_REPO="$MAIN" OH_NATIVE="$NATIVE" LIBLOG_INPUT="$EXACT_D8AD_LIBLOG" \
OUT="$FRESH_PERSISTENT_OUT" R10_CONTAINER="$DEDICATED_CONTAINER" \
R10_DOCKBUILD="$MAIN/benchmark/2026-10-19-toutiao-video-playback/candidate-r10/copy_dockbuild.sh" \
bash "$MAIN/benchmark/2026-10-19-toutiao-video-playback/candidate-r10/build_candidate.sh" --run
python3 "$MAIN/benchmark/2026-10-19-toutiao-video-playback/candidate-r10/verify.py" accept-build --inputs-root "$MAIN" --build "$FRESH_PERSISTENT_OUT"
```

Do not deploy link-only anchors or input liblog. Only the exact stripped compat artifact is new; player, media and run remain the r9 tuple. Build success proves neither actual provider binding nor playback. See the separate bounded-window admission and subsequent runtime evidence.
