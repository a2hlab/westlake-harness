# README addendum — decoder-selection chain (candidate; separate from the baseline MP3 enumeration)

Addendum to the enumeration packet (already landed). **Address convention:** hex below are **Ghidra virtual addresses** at image_base **0x100000**
(confirmed, ev_6677486f) — NOT ELF offsets. For the selection function the ELF/file offset is
independently pinned (LLVM, BASE20/decoder-select-independent): Ghidra VA 0x28d0fc = **ELF/file
0x18d0fc** (end-exclusive 0x18e534). In general ELF vaddr = Ghidra VA − 0x100000 and file offset is
segment-dependent; this specific `.text` function happens to map by the same −0x100000.

## Scope of the audited object (precise)
The disassembly-confirmed MP3 result is: the deployed OH MediaCodecList enumeration **as implemented
in the baseline bridge ELF d4fae8e5** returns 1 codec (`OH.audio.mp3.decoder` / `[audio/mpeg]`).
This is a **baseline-ELF** fact; the **final JNI `RegisterNatives` winner at runtime is not proven**,
so it is NOT a whole-runtime MediaCodecList claim. Unchanged by this addendum.

## Decoder selection (static, libttmplayer 5fba8050; Ghidra VA, imagebase 0x100000)
`ff_vcodecer.cpp:open` (`FUN_0028d0fc`, Ghidra VA 0x28d0fc–0x28e533 = ELF/file 0x18d0fc–0x18e534; src line 0x5e=94). This function body is **byte-identical across r4 5fba, r8/r9 deployed 0b4d** — range SHA256 `31901285ef2164e9b7c555caf1969202d810ea5ae576220afa8d1db5565777ca` (independent LLVM) — so the logic read on r4 applies verbatim to the deployed player. It reads an internal
`codecId` from the track object and calls **`avcodec_find_decoder_by_name`** with a literal name:
`0x41000→"libbytevc2dec"`, `0xc5→"libvvcdec"`, **`0xae→"libbytevc1dec"`**, else/null→
`avcodec_find_decoder(codecId)` → error if still null.

**What this proves / does not prove:** it proves the code performs a **by-name registry lookup** of
`"libbytevc1dec"` for codecId 0xae. It does **NOT** prove a decoder named `libbytevc1dec` is actually
**registered** (an AVCodec entry) or that the lookup returns non-null. `bytevc1_*` decoder symbols
and strings (`ByteVC1_dec_decode_inner`@VA 0x4ca95d, `ffmpeg/libbytevc1.c`, error
`ByteVC1_dec_decode error`@VA 0x49bc51) are **present** in libttmplayer, but they have not been tied
to a registered `"libbytevc1dec"` AVCodec entry or body in this pass — that registry/body proof is
outstanding.

## Status: CANDIDATE, not decided
NOT confirmed: the r9 stream's actual codecId (`start.codecId` absent from r9 256-mirror /
r8-play1) → which branch r9 took; that `video/hevc == 0xae`; that a `libbytevc1dec` decoder is
registered and returns non-null; and any frame/decode success (`dec_start` = thread-start log point
only). So **object B (MediaCodec non-hardware fail) terminality is UNDECIDED.** Resolves via the r10
4096-mirror `start.codecId`, plus (for the registry) an AVCodec-table read.

## Withdrawn draft (do not publish)
`internal-bytevc1-rea.json` (asserted "internal ByteVC1 IS the path") was **not accepted** and has
been **deleted**; superseded by `decoder-select-rea.json`.
