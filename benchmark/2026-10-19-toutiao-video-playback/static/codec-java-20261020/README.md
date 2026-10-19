# video-2020-codec-java — deployed codec provider, end-to-end (t1)

Static-only, investigate. Extends `codec-read/` (native side) to the Java selector and the
**deployed** OH MediaCodec provider. Full raw REA/source Evidence + SHAs in `rea-raw-manifest.txt`
(persistent copies under `$HOME/.local/share/westlake/.../codec-java-20261020-rea-raw/`).

## The decisive conclusion — disassembly-confirmed on the deployed bridge
The on-board MediaCodecList provider exposes **exactly one codec — an MP3 audio decoder — and no
video decoder of any kind.** Confirmed by **disassembly** of the deployed `liboh_adapter_bridge.so`
d4fae8e5 (Ghidra 12.1.4; not strings-inference), evidence in `bridge-mediacodeclist-rea.json`:
ELF entry PCs (imagebase 0x100000; Ghidra addr = ELF + 0x100000; independently cross-checked by
LLVM disasm at `…/toutiao-resume-20261020/codec-enumeration-independent`):
- `mclCount` ELF **0xf2e88** `{ return 1; }` (LLVM: `mov w0,1; ret`) — one codec (ev_ce71bef3…).
- `mclGetName` ELF **0xf2e90** `→ NewStringUTF("OH.audio.mp3.decoder")` (its name-string load is
  at ELF 0xf2e94/0xf2e98 per independent LLVM asm; the 0xf2ef8 reference to that string belongs to
  `mclFindByName`, not `mclGetName`) (ev_6e0a4d16…).
- `mclSupportedTypes` ELF **0xf2f40** `→ String[1]; elem[0]=NewStringUTF("audio/mpeg")` (ev_6cff535a…).
- `register_MediaCodec_shim` ELF **0xf0778** (ev_b9c43a10…) `RegisterNatives(android/media/MediaCodecList,
  9 methods)` binding `native_getCodecCount→mclCount`, `getCodecName→mclGetName`,
  `getSupportedTypes→mclSupportedTypes`, `findCodecByName→mclFindByName`, `getCanonicalName`,
  `getCodecCapabilities`, `getAttributes`, `native_getGlobalSettings`, `native_init`.

So `AJMediaCodec.getBestCodecName("video/hevc")` (and `video/avc`) enumerates this single codec
whose only supportedType is `audio/mpeg` → no `video/*` match → returns null → `libttmplayer`
`FUN_003561e4` (`aj_media_codec_async.cpp:open:490`) logs "non hardware codecname match the codec
type" → `asyncInitCodec:189 open codec fail errReason:0` (3× in r8). This rests on the deployed
binary's instruction-level return values, independent of the Java filter details below.

Scope limit (not claimed): the *final* JNI RegisterNatives winner on r8 (libmedia_jni's JNI_OnLoad
vs runtime, both call the same single bridge `register_MediaCodec_shim`) is an order question that
needs the r8 register log; since only one `register_MediaCodec_shim` impl exists, order cannot
introduce a video codec.

### Provider chain (all statically confirmed)
- `libmedia_jni.so` deployed **f3943601** (`/data/local/tmp/asx/`, provenance in
  `media-provider-readonly-0227/`): thin registrar. `register_MediaCodec_shim` is **UND** (llvm-readelf
  dynsym idx 5, FUNC GLOBAL UND); `JNI_OnLoad@0x1adc` calls it; `DT_NEEDED liboh_adapter_bridge.so`.
  Logs `[SOURCE-MEDIA-JNI] OH MediaCodec natives registered`.
- runtime `liboh_android_runtime.so` **8ab6742d**: also `register_MediaCodec_shim` UND; logs
  `[WESTLAKE-494] register_MediaCodec_shim rc=%d`.
- **`liboh_adapter_bridge.so` deployed d4fae8e5** DEFINES `register_MediaCodec_shim` and the
  MediaCodecList natives. Its codec literals (deployed binary, `deployed-bridge.strings.txt`):
  `OH.audio.mp3.decoder`, `audio/mpeg`, `audio/raw`, `register MediaCodecList rc=%d (%d methods)`,
  `getCodecName`, `getSupportedTypes`, `android/media/MediaCodecList`, `OH_AudioCodec_RegisterCallback`.
  **No `video/*`, no HEVC, no OMX/c2 video.** Also `[WESTLAKE-HWACCEL] enableHardwareAcceleration not found`.
- r8 child log line 147: `[WESTLAKE-494] register_MediaCodec_shim rc=0` (once; registration succeeded).
  Only one `register_MediaCodec_shim` implementation exists (the bridge), so register order/repeat
  cannot change the MP3-only content.
- Source candidate `oh_mediacodec_shim.cpp` **6cf6caba** is MP3-only too. A source-file SHA
  necessarily differs from an ELF SHA, so this does **not** prove a different build — the
  source→product build mapping is unproven. The deployed binary d4fae8e5 is the authority above.

## Java selector — verified against instruction-level (fallback), not restructured Java
`com.ss.ttm.player.AJMediaCodec.getBestCodecName(String):String` (JADX engine 0.7.1, jar
`6e5eacf5`, Evidence `ev_1f71ced0…`). The default restructured Java (`getBestCodecName.java`) has
**control-flow recovery errors** (e.g. `if (supportedTypes == null) { … supportedTypes.length }`;
an `equalsIgnoreCase`-negation branch reading as include-candidate). Per outer, conditions were
re-checked against the **`jadx --fallback` instruction-level form** (explicit `if (rX == 0) goto Lnn`),
saved as `getBestCodecName.fallback.java` (+ full class `AJMediaCodec.fallback.java` in the
persistent raw dir). baksmali was not available locally; the fallback form is instruction-level and
free of the restructuring artifact.

Confirmed (correct polarity) return-null path for HEVC:
```
r0 = r10.equals("video/hevc");   if (r0 == 0) goto L5e     // only when codecType == video/hevc
r0 = mIsByteVC1Blocklist;         if (r0 == 0) goto L5e
r0 = mIsByteVC1BlocklistEnable;   if (r0 <= 0) goto L5e
... AVLogger.Warn("the device is hw decoder blocklist," + Util.HARDWARE); return null
```
i.e. **codecType=="video/hevc" && mIsByteVC1Blocklist && mIsByteVC1BlocklistEnable>0 → return null**
(a device hardware-decoder blocklist for HEVC). The other null anchor is the empty-rank-list return
after the enumeration.

The inner `getSupportedTypes`/`equalsIgnoreCase`/prefix/`setupRank` loop polarity (the part JADX
mangled) is **not load-bearing for this report's conclusion**: the deployed MediaCodecList exposes
**no video codec at all** (bridge binary above), so the enumeration never yields a `video/hevc`
supportedType regardless of the loop's exact conditions → empty rank list → null. Any eventual fix
must still be derived from the fallback/smali conditions, never from the restructured pseudo-Java.

## Software fallback — status: strong signal only, NOT a proven wall (see `decoder-side-note.md`)
`libmffmpeg.so` is present and loaded in the r8 run (`[SOURCE-NATIVE-LOAD] …/libmffmpeg.so`,
line 218227); loading ≠ decode executed. The embedded FFmpeg `./configure` string (REA ev_6a5dc014,
`libmffmpeg-decoders.txt`) enables video decoders **h264/h263/mpeg\*/rv30/rv40/vp8/vp9** and **not**
`hevc`/`bytevc2`. **This is a strong signal, not proof**: a `configure` record is not the complete
runtime decoder registry, and the player may register HEVC/ByteVC via **external decoder plugins**
(e.g. `libbytevc*`). The HEVC-side conclusion is therefore **not** finalized in this packet — it is
tracked separately in `decoder-side-note.md` (real `avcodec_find_decoder`/decoder-array + external
plugin investigation, with an explicit search boundary). The MediaCodec (hardware) MP3-only result
above stands on its own; the HEVC software-decode question remains **open**.

## Network interaction (object A → cx)
The r8 full log `[WESTLAKE-WEBVIEW-NET]` shows **AF_INET6 works on this platform** (connect #9/#16
to IPv6 DNS `rc=0`; #10–15 to :443 `errno=115` EINPROGRESS). So the player's `ff_listen_connect2
-97` is **player-socket-specific, not platform IPv6 absence** — this refutes the earlier
"platform has no IPv6" reading and is handed to cx with object A. If the media stream never
arrives (player -97), decode never runs — so A and B may interact; neither is proven terminal.

## Minimal fix candidates (hypotheses; NOT applied; none derived from the suspect pseudo-Java)
- B1 (real video backend): add a genuine OH video decoder (OH native AVCodec HEVC/AVC) behind the
  bridge's MediaCodec/MediaCodecList natives so the enumeration exposes a real `video/*` decoder.
  **Not** a fake enumeration name — a reported name with no decode backend would fake-succeed then
  fail downstream (the trap outer flagged).
- B2 (software path): drive the player's `mDowngradeSw`/`libmffmpeg` path **iff** `libmffmpeg` can
  actually decode the stream (verify full HEVC/bytevc2 decoder first). CPU HEVC may be slow.
- Open question: is the blocker decode (B) or the player's stream fetch (A, `-97`) or both? Not
  settled.

## Single-variable verifications (static; no board logging)
1. Raw **smali/dex** of `getBestCodecName` — confirm the real `if-eqz`/`if-nez` return-null points
   and the filter, with raw blocks attached. (Required before any fix.)
2. `libmffmpeg.so` decoder table — does it register a **full** `hevc`/`bytevc2` decoder (not just a
   parser)? Determines whether SW fallback can carry playback with no MediaCodec video.

## r4/r8 identity (required diff evidence)
`libttmplayer.so` r4 = `5fba8050`, r8 = `0b4d95c5` differ only in the **17 log-import name bytes**
(prior task, llvm-readelf: dynsym 227 `__android_log_print`→`__wl_ttlog_00000659`, JUMP_SLOT
`0x471f88` r_info sym idx 0xe3=227 unchanged). `FUN_003561e4` codec logic is byte-identical across
r4/r8 — the codec analysis holds for both.

## Not claimed
No root cause; no playback fix; no claim that the Java filter polarity is as JADX rendered; no
claim the codec gap is terminal (SW fallback loads). APK is commercial — kept on hw248/private
only, never committed; public report carries no URL/token/content.
