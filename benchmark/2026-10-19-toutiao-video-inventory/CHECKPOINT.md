# Toutiao video inventory checkpoint — 2026-10-19

## Evidence first / what is not established

**No current or historical end-to-end Toutiao video playback PASS was located in this bounded local inventory. This is not a current root-cause diagnosis.** The 2026-09-28 README's headline is stronger than its retained evidence: PID20465/TikTokActivity cover freeze, ReliableSurface reserveNext37265/init27 and Bufferqueue SetMetadata(-5)280 are **historical reported observations**, not fresh counts or proof that today's failure follows that path. Its directory contains README and two screenshots, not original stderr/hilog or the second timed frozen-frame sample. Installed decoder libraries do not prove actual decoding; absent log messages do not prove a route was unused.

Read local DIGEST and RUNBOOK first. No board, remote, build, implementation change, user-data inspection or push was performed. Contract preparation stays with outer; this delivery only inventories already-existing material. `results.json` records exact real source paths, last-touch Git commits, SHA256, route/generation and evidence limits for8 groups.

## Reusable implementation inventory

| Capability | Actual local source | What it implements / validation boundary |
|---|---|---|
| MediaCodec audio | `$WORKSPACES/vm-copies/westlake-current/framework/core/jni/oh_mediacodec_shim.cpp` | Real OH_AudioCodec async-to-sync adapter; source describes Noice MP3, codec-list audio/MP3. `native_configure` ignores Surface. Not video codec output. SHA `6cf6caba…`; source checkpoint last-touch `f82d1f1a…`. No timed Noice playback receipt located. |
| AudioTrack | same tree `framework/core/jni/oh_audiotrack_shim.cpp` | Real OH_AudioRenderer ring/pull/PCM/timestamp accounting, SHA `8e922c5d…`. No current audible-output claim. Ledger mousepounce says audio while window absent; this remains reported historical, not our playback validation. |
| MediaPlayer audio | MAIN `benchmark/2026-10-02-u12-upstream-audio/upstream/media_natives.c` | Exact upstream5ae6b754 snapshot, SHA `52c3658b…`, real OH AVPlayer data sources/callbacks. `_setVideoSurface` at770–772 explicitly no-op/audio-only. Ntfy/Astro Loop/Doors native-init walls moved; Doors still FD-source/error failure, not playback. |
| Historical MediaPlayer/AudioTrack | own `bms/src/adapter/framework/android-runtime/src/android_media_{MediaPlayer,AudioTrack}.cpp` | Legacy L12/ac59 registration/lifecycle stubs, not same as later real source-build implementations. MediaPlayer fromSurface handoff/prepare callback writes no video pixels. Full SHA/commit in JSON. |
| NDK media | MAIN `benchmark/2026-10-02-u12-mediandk/` | Candidate8fc0752d: real AMediaFormat int32/DataSource containers; codec/extractor operations return legal unsupported. Unity/Subway static/provider tests are not decoding. |
| CPU video producer | MAIN `benchmark/2026-10-01-n10-native/flutter/libandroid_webview_shim.c`, `2026-10-01-u11-native/window-lock/owner_wrappers.c` | Lock/post, fences/maps and YV12 conversion sources exist; libttmplayer is explicitly mentioned. Different private/root ownership profiles; no confirmed Toutiao playback result. |
| Surface/SurfaceTexture | local Westlake `framework/surface/jni/oh_graphic_buffer_producer.cpp`, `oh_surface_texture_jni.cpp` | Real RequestBuffer/FlushBuffer and updateTexImage code. Exact current RouteB TU->deployed-provider binding not found. Not evidence that the old ReliableSurface log is today's first wall. |
| SurfaceView geometry | MAIN `benchmark/2026-10-13-runtime-surfaceview-split/source/android_graphics_compat_shim.cpp` | Exact sourcec208788a, cold-built f28 lineage; Boat R6 input/LAP/popup visual controls are real but **not video**. Shared runtime and RouteB private runtime are separate. |

## Deployment identities must remain separate

The historical61b signed RouteB source index (`2026-10-12-v1-seal-execution/seal-final-20261013/route-b-source.json`) pins:

- RouteB bridge **d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b**; private runtime **8ab6742d58de5b9df94a2bfa80cebed46f136c0251083793fcbef8293cc23ab1**.
- Root-private libandroid **c9969638…**, webview-private libandroid **76512d97…**, libhwui **a11c9154…**, media_jni **f3943601…**.
- libttmplayer **b427614d…**, ByteVC1 **bed09890…**, byteVC2 **62f77bbf…**, vcn **ec5cdb76…**.

These are historical source-index pins, **not new2026-10-19 live readings**. In particular RouteB runtime8ab6742d is not shared bridge8ab85446, and f28 shared-runtime geometry is not automatically a RouteB media fix. DIGEST#46's mc46 bridge repair concerns fail-clean setup/getOwnCodecInfo binding and an88s video-related error, not proof of video rendering success. Exact provenance between the local later source-build shims and d4fa is unknown; do not fill it by filename similarity.

## APK/generation validation and remaining evidence

### Current parent namespace input — outer capture supplied 2026-10-19

Consumed `$HOME/.local/share/westlake/toutiao-resume-20261019/61b-runtime.txt` (SHA `c5de14c595aac3afaf36a5c1db79101a387906da37d8328f723e06830064b602`, 205203 bytes) and `61b-media-identity.txt` (SHA `c9422c316a0e74cc1881b785c6c68c33269a5f0b06f93633925c41840bae79a2`, 1867 bytes). Originals remain at that persistent input location; full maps are not duplicated in this public checkpoint.

- Boot `6944c37e-31a6-4846-8f1f-48088a917153`, OH `OpenHarmony-6.1.0.31`/aarch64. Parent `11444`, birth `107387`, PPID1, mount namespace `4026533005`; raw stat at identity lines2/18 is identical. This establishes captured parent continuity only.
- Seven fresh parent-namespace hashes pin APK `a1112a0c`, spawner `a7a358c6`, root-private libandroid `c9969638`, media_jni `f3943601`, hwui `a11c9154`, hwui shim `5e540812`, and run.sh `d3518cef`. Full hashes/paths/line numbers are in JSON. The three libandroid/media_jni/hwui hashes match the historical signed source index; this does not transfer other historical hashes.
- Parent maps contain private bridge/runtime, hwui/shim, libandroid and media_jni. Bridge/runtime **fresh hashes are not in these inputs**. Player/ffmpeg/videodec files have size/listing evidence, not current SHA or loading proof.
- Actual run.sh pins UID20011206/WID33, private root `/data/local/tmp/asx`, WebView paths and three preload entries. libttmplayer is not in its explicit native-target list; this is configuration evidence, **not proof that the player cannot load through another route**.
- **No live child was captured. Actual video consumer, decoder selection, child namespace resolution, Surface/audio owners and playback remain unknown.** No video success or root cause is inferred from parent maps.

If needed, the remaining bounded delegated read is SHA256 of private bridge/runtime and the listed player/codec files **in the same guarded parent mount namespace**, with stat/boot bookends. A child media observation would be separate from this parent-only static identity inventory.

Source comments describe Noice's intended MP3 path; the upstream ledger describes mousepounce's reported audio despite missing surface, MediaPlayer native-init unblocking and Ball2Box's OpenSLES symbol/queue fixes. None is current Toutiao video playback. U12 explicitly documents incomplete PLAY completion/current registration and non-admitted owner routing. r84's Fossify/Nounours MediaPlayer states progress only to drawing/view or safe MEDIA_ERROR. Existing gallery/full128 startup screenshots likewise do not certify playback.

For the future outer-authored contract, first pin the actual current APK/artifacts and selected codec/Surface/audio owners. Only a separately authorized real observation can establish advancement beyond a cover, decoded/queued/consumed frame progress and audio progression. The same-PID own media path/error and generation binding are prerequisites for using the old candidates. No new probe or implementation is introduced here. Random heap crashes and private user-data contents are deliberately outside this inventory.
