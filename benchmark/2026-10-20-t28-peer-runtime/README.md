# T28 independent runtime review

Whole-screen hash changes can misclassify a paused video because clocks and controls change. This review instead checks the captured video content visually and compares a fixed inner-video RGB region. Two playback/pause/resume cycles are supported; a separate 20-second black-video interval after a UI transition remains a failure. This is not a seal approval or evidence that the newly added RGBX2 branch ran.

## Evidence and scope

The outer-owned T28 window used shim `89b9a8b9868bb35d3cd70108e9114714c7f525cbed7006974b4f095912ff0b33` (97,464 bytes), child 7636/birth 11486, boot `5a71b747-b38b-4e27-b9a1-0e096b31d91c`. This peer only read local receipts, images and logs: no device calls, deployment, new REA calls or changes to main.

Each row has four receipt-verified captures at scheduled 0/5/10/20 seconds. Actual elapsed times are recorded rather than assumed. The RGB region is `(178,335)-(1020,880)`, excluding the header and playback controls. Visual inspection established person/scene/subtitle changes, not merely different hashes.

| Group | Actual span (s) | Distinct ROI hashes | Last-vs-first mean absolute channel difference | Finding |
|---|---:|---:|---:|---|
| First debt clip: play | 20.019 | 4 | 19.46484 | Moving person and subtitles |
| First debt clip: pause | 19.708 | 1 | 0 | Same content, play triangle |
| First debt clip: resume | 20.095 | 4 | 22.98767 | Content resumes |
| Later UI transition | 20.045 | 1 | 0 | Every sampled ROI channel is zero: black |
| Story clip: play | 20.035 | 4 | 58.98825 | Scene changes within the same story |
| Story clip: pause | 20.129 | 1 | 0 | Same content, play triangle |
| Story clip: resume | 20.138 | 4 | 45.45074 | Indoor person changes to hillside scene |

The user's corresponding-audio confirmation applies to the first debt clip only. Story audio is **unknown**. Earlier `cycle-observation-02` changes clips and is not counted as a same-clip 20-second cycle; the later complete `story-cycle-*` series is used. The preliminary `cycle02-pause` remains in the replay output as historical evidence.

## What the logs establish

- The final fixed prefix is 72,502,755 bytes / 877,415 lines, SHA256 `2620684cad6c88e859ecc928ec36e48bd958b7ddb23b14d271f19a554df00a2d`.
- Nine recorded geometry calls use Android YV12 `842094169`, at 476×360 or 360×360. Acquire, unwrap, geometry, format and release report success. No actual RGBX2 geometry call is present.
- The earlier video prefix has three actual Mali create records at module-relative `0x33e814`, target `0x34e1`, all nonnull; native-buffer observations report OH format 12. The same exact deployed shim path records geometry/lock/unlock offsets `0xe3b0/0x6ec0/0x6ed4`.
- T27 logging reached its cap early (256 records plus cap marker); R20 logging also capped. Their absence later cannot exclude a later import, buffer or format failure.
- Literal `InvalidGrBackendTexture`, `create failed`, `Fatal signal`, and `FATAL EXCEPTION` counts are zero in the final selected prefix. This does **not** establish the first fatal point or explain the black interval.

The first-video prefix records window/wrapper changes and successful image creation/destruction around the transition. Those bounded identities and source line references are in [video-analysis.json](video-analysis.json), with later geometry and R23 excerpts in [final-delta.json](final-delta.json). They are investigation leads, not a proven stale-window or ownership root cause. The post-trigger system-log slice reviewed for that transition starts afterward and does not close the timing gap.

## Reproduce and locate originals

[results.json](results.json) contains the bounded verdict. The three `reproducible-*.json` files pin every screenshot by window-relative capture path and SHA256, decoded ROI hash, actual capture time, ffmpeg hash and decoder result. [private-index.json](private-index.json) pins the large private originals and the bounded handoff; remote publication belongs to the outer archive lane and is not asserted by this review.

Restore the outer window archive under any directory and run:

```sh
python3 benchmark/2026-10-20-t28-peer-runtime/review_roi.py \
  --window "$T28_WINDOW" \
  --group cycle-observation-01 --group cycle01-pause --group cycle01-resume \
  --group post-unmute-observation \
  --group story-cycle-play --group story-cycle-pause --group story-cycle-resume \
  --out "$T28_REVIEW_OUTPUT"
```

`ffmpeg` must be on `PATH`; the output must not already exist. Conversion to RGB precedes cropping so chroma-subsampling alignment does not silently round the 545-pixel height. The tool verifies capture hashes and decoded byte counts, reads existing files only, and deliberately requires separate visual review. Large original logs and images stay in the outer window archive.
