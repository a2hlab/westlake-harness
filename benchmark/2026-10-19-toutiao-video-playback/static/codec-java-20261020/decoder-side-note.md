# decoder-side note — HEVC software/plugin decode (t1, OPEN; multiple self-corrections)

Separate from the audited MP3-enumeration packet. The HEVC *decode* path on this runtime is
**unknown**. This note records candidates and, importantly, retracts two earlier over-claims of my
own. Nothing here is a finalized playback conclusion.

## Accepted facts (bounded)
1. **MediaCodec (hardware) = MP3-only**, disassembly-confirmed on the deployed bridge d4fae8e5
   (`mclCount=1`, `mclGetName="OH.audio.mp3.decoder"`, `mclSupportedTypes=["audio/mpeg"]`; ELF
   0xf2e88/0xf2e90/0xf2f40; independent LLVM + 12/12 complete REA). So `getBestCodecName(video/hevc)`
   returns null → the OH hardware MediaCodec path is not used for this video. (This is the only
   fully-audited object.)
2. `libmffmpeg.so` d2882303 embedded FFmpeg `./configure` enables video decoders
   h264/h263/mpeg*/rv30/rv40/vp8/vp9 and **not** hevc/bytevc2. **Strong signal only** — a configure
   record is not the complete runtime decoder registry.

## Candidates (NOT proven capability, NOT proven used)
The APK ships external video-decoder `.so`:
- `libByteVC1_dec.so` bed09890 — exports `ByteVC1_send_packet`/`ByteVC1_frame_got_frame`/… ; strings
  "Bytedance bytevc1 ByteVC1 decoder (V%s) is created", "ByteVC1 decoder not support vps_extension"
  (`vps` = HEVC Video Parameter Set). These make ByteVC1 a **candidate H.265/HEVC-class decoder** —
  exported API + identity strings do **not** prove it can decode the stream or that it is wired in.
- `libbyteVC2dec.so` 62f77bbf — `byteVC2dec_create`/`decode`/`get_frame`/`destroy` (candidate).

## RETRACTION 1 — `libvideodec.so` is NOT the ByteVC loader
Earlier I inferred `libvideodec.so` (loaded in r8) fronts/loads the ByteVC decoders. **Wrong.** REA
on `libvideodec.so` e2221d12 (imagebase 0x100000; 64 procs, 9952-byte .text):
- Exports: **only `JNI_OnLoad`**.
- UND imports: **libc-only** — `malloc`, `free`, `memcpy`, `memset`, `strlen`, `__memcpy_chk`,
  `__strlen_chk`, `__stack_chk_fail`, `__cxa_atexit`, `__cxa_finalize`. **No `dlopen`, no `dlsym`,
  no ByteVC symbols** (`find_xrefs_to_name dlopen`/`dlsym` → name_not_found).
- `_getDecodedStr` is a **string** (JNI native-method name `getDecodedStr` for class
  `com/ss/ttm/ttvideodecode/Native`), **not** a function — my "runtime string-decoder" claim was
  unfounded.
So `libvideodec.so` is a tiny JNI string helper. It does not `dlopen`, does not call ByteVC, and
does not decode video. Its r8 load says **nothing** about a ByteVC decode path.

## RETRACTION 2 — "no static edge ⇒ must be dynamic dlopen" was an over-inference
Absence of a checked DT_NEEDED/UND edge does not prove the ByteVC decoders are reached by dynamic
`dlopen`; I simply have not found their loader/caller.

## r8 runtime: ByteVC decoders NOT observed loaded
Video `.so` seen via `[SOURCE-NATIVE-LOAD]` in the r8 child log: `libmffmpeg.so`,
`libttheif_dec.so`, `libttmplayer.so`, `libvcbasekit.so`, `libvideodec.so`, `libzstd-jni-decompress.so`.
**`libByteVC1_dec.so` / `libbyteVC2dec.so` do NOT appear.** (Caveat: this logs shim-routed loads;
a load via another path might not be recorded — so this is "not observed", not "proven not loaded".)

## Where this leaves object B (precise, downgraded)
Static read of the selection function `FUN_0028d0fc` = `ff_vcodecer.cpp:open` (complete raw REA in
`decoder-select-rea.json` / archived `rea.procedure_pseudo_code.libttmplayer.FUN_0028d0fc.json`):
the player selects the video decoder by **internal codecId** via `avcodec_find_decoder_by_name` —
`0x41000`→`libbytevc2dec`, `0xc5`→`libvvcdec`, **`0xae`→`libbytevc1dec`** (internal ByteVC1,
HEVC-class), else/`null`→`avcodec_find_decoder(codecId)` fallback, and an error path if still null.
libttmplayer has the internal ByteVC1 decoder compiled in (registered as `libbytevc1dec`).

Confirmed: the selection LOGIC and the codecId→name map (above). **NOT confirmed** (downgraded):
- the r9 video/hevc stream's actual internal codecId — the `start.codecId` log line is **not** in
  the available r9 256-mirror or r8-play1 logs, so which branch r9 took is **unknown**;
- that `video/hevc` maps to codecId `0xae` (ByteDance FFmpeg enum not verified);
- that decode produced frames / rendered (`dec_start` = a thread-start log point only).

So: the internal ByteVC1 decoder is a **candidate** video/hevc path (selected iff codecId==0xae);
object B (MediaCodec "non hardware codecname match") is a fallback away from OH hardware MediaCodec,
but whether it is terminal is **still not decided** — it hinges on the unread codecId/selection and
the undemonstrated decode outcome. The only fully-audited object remains the MediaCodec MP3
enumeration. Next locatable nodes (for a full r9 log or dynamic read): `start.codecId` value →
branch; `mCodec` non-null; `ByteVC1_dec_decode error:(%x) %d`@0x49bc51 vs frame output.
