# Bounded video-backend reuse search

No verified drop-in video decoder port was located in the inspected local sources. This does not assert that none exists on the inaccessible VM/remote host. The existing inventory was reused and source hashes rechecked; the d4fa MP3-only REA work was not repeated.

| Hit | Reuse value | Video gap / validated APK boundary |
|---|---|---|
| OH AudioCodec JNI | Actual callback queue and Android buffer lifecycle | Audio only; Noice source intent, no video receipt |
| OH AVPlayer media_natives | Real URL/FD/audio player implementation and delivered build_missing_natives.sh | Later691 source still discards video Surface; historical native-init successes are not playback |
| Legacy L12 MediaPlayer | Surface handoff and lifecycle registration | Explicit no decode/no pixels; HelloWorld lifecycle only |
| U12 mediandk | Correct types, real small containers, build.py | Codec construction/operations unsupported; Unity import compatibility only |
| U11/N10 CPU window producer | Lock/post and YV12 conversion; build_window_shim.py | Not a decoder; no proven Toutiao frame output |
| SurfaceTexture / graphic buffer producer | Real queue/fence/update pieces | No exact current RouteB video-consumer proof |

The Java MediaCodec shim is explicitly a stub. VLC evidence does not reach its engine. Bundled ByteVC decoders are binaries, not recovered source/build/validated reuse. Do not turn codec enumeration, library presence, Boat graphics or first-screen evidence into video playback.

All rows include source SHA/revision, actual build entry where found, and validation limits. In particular the U12 audio **stage.py** recipe builds OpenSLES; it is not presented as a MediaPlayer build recipe. Network remains a separate prerequisite. Proven immediate codec-wall removals from drop-in reuse: **0**.

The a2hlab bounded query timed out; hw248 was sandbox-denied. No bypass, build or device call followed. Exact private query receipts remain in `.artifacts/`; public access-receipts.json preserves return codes and receipt hashes without private addresses.
