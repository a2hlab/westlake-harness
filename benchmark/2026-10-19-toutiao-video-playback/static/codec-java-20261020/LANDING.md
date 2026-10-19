# Landing — video-2020-codec-java checkpoint (t1 static; no board, no build, no push)

Branch: analysis/toutiao-video-20261019. Committed, NOT pushed (push awaits user).

## In-repo deliverables (this checkpoint)
- static/codec-java-20261020/README.md — object B end-to-end, disassembly-confirmed.
- static/codec-java-20261020/bridge-mediacodeclist-rea.json — bridge d4fae8e5 REA: ELF PCs (imagebase 0x100000), evidence IDs, MP3-only enumeration.
- static/codec-java-20261020/getBestCodecName.java + .fallback.java — JADX restructured + instruction-level.
- static/codec-java-20261020/deployed-{bridge,libmedia_jni,runtime}.strings.txt — deployed string evidence.
- static/codec-java-20261020/oh_mediacodec_shim.mcl-excerpt.cpp — source candidate (6cf6caba, NOT deployed build).
- static/codec-java-20261020/rea-raw-manifest.txt — full SHAs, history→current.
- static/network97-20261019/ (+ codec-read/) — prior objects A/B first-pass (corrections applied in place).

## Persistent raw (outside git; commercial APK + big JSON)
$HOME/.local/share/westlake/toutiao-resume-20261019/codec-java-20261020-rea-raw/
  - toutiao.apk (a1112a0c), getBestCodecName*.java, AJMediaCodec.fallback.java
  - rea-tool-json/ : COMPLETE REA tool JSON (analyze_function libttmplayer FUN_003561e4; inspect_android_class/method; bridge ops + evidence IDs)
Deployed binaries: $HOME/.local/share/westlake/toutiao-resume-20261020/media-provider-readonly-0227/ (bridge d4fae8e5, libmedia_jni f3943601, runtime 8ab6742d + before/after provenance)
Independent LLVM disasm: $HOME/.local/share/westlake/toutiao-resume-20261020/codec-enumeration-independent/

## Confirmed / open
- CONFIRMED (disasm, baseline d4fae8e5): deployed MediaCodecList = 1 codec (OH.audio.mp3.decoder / [audio/mpeg]); no video. getBestCodecName(video/hevc)=null -> native "non hardware codecname match".
- OPEN: r8/r9 final RegisterNatives winner (order); whether libmffmpeg registers a FULL HEVC/bytevc2 decoder (fix fork); object A (-97) -> cx.

## Persistent out-of-git paths (NOT for the repo-relative landing list; recorded here)
- $HOME/.local/share/westlake/toutiao-resume-20261019/codec-java-20261020-rea-raw/outer-extracted-bridge-results/  # 12/12 COMPLETE REA tool_result (authoritative)
- $HOME/.local/share/westlake/toutiao-resume-20261019/codec-java-20261020-rea-raw/rea-tool-json/                   # big Evidence JSON (analyze_function, class, method) + hand summary (marked summary)
- $HOME/.local/share/westlake/toutiao-resume-20261019/codec-java-20261020-rea-raw/libmffmpeg-ffmpeg-configure.txt  # full embedded ./configure (internal build paths kept out of public report)
- $HOME/.local/share/westlake/toutiao-resume-20261019/codec-java-20261020-rea-raw/toutiao.apk                      # commercial APK a1112a0c (never committed)
- $HOME/.local/share/westlake/toutiao-resume-20261020/media-provider-readonly-0227/                                # deployed bridge/libmedia_jni/runtime + provenance
- $HOME/.local/share/westlake/toutiao-resume-20261020/codec-enumeration-independent/                               # independent LLVM disasm cross-check
