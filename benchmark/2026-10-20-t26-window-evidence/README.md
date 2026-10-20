# T26/T27 closed window: two visible playback cycles, first start still fails

The first child (7603) still failed on RGBX2 → OH11: its actual Mali image creation returned NULL, followed by Invalid GrBackendTexture and a fatal signal. A normal desktop icon reentry created child 13338 and reached the feed. In that child, two independently reviewed cycles show video scene/subtitle changes, a stable paused frame with the play triangle, and resumed scene changes. The second desktop icon reentry foregrounded the same child/birth; it was not a cold restart. **The scoped playback observation passed; the seal did not pass because first start failed.**

The paused pairs are byte-identical within each cycle over 8.292654 and 11.624460 seconds. Sixteen selected candidate images and a restored image are indexed. The user confirmed “能听到对应声音” for the current Husai video, recorded in the current window close receipt. This confirmation replaces the earlier pending-audio state without treating screenshots as audio evidence.

The 41,644,686-byte child-13338 selection has SHA256 `c1a519a981d15c60f6cc31f93a5f180f7f52e4f9fa94d162073f98040134d537`. Seven geometry records returned zero; three T27 imports report format 12 and are correlated with three non-NULL actual Mali creates at relative address `0x33e814`. The 256-record diagnostic cap produced a drop marker. Missing subsequent records do not establish missing calls. The retained failed-child selection is 486,077 bytes, SHA256 `c55c8ee75d062332d583aedf4d227f6263cfcdb3fb7e019c225cf06a6eddb7de`. Technical excerpts include original byte offsets, lengths and hashes; neither full log is copied into the public repository. Transfer verification does not prove source in-place immutability.

The window closed after **1067.603461 seconds**, with original physical/private six-state restoration, five original file SHA pairs and compat absence. Independent replay compared all eight snapshot fields over 518 targets/812 labels and the 26-target supplement (boot header excluded): EQUAL. Original power 10000/10000 and debug absence/106 were restored. Unlock returned 0; held-after returned 1 with empty stdout. The independently viewed restored screenshot is IME host only: runtime restoration did not recover the feed UI.

`final/facts.txt` is the unmodified output of the original `scripts/lab/run_facts.py`: four record-schema screenshots, all four liveness states unknown. Its schema count excludes separate capture-directory frames; the selected-image index is a separate evidence list, not a substitute count or survival claim. `final/source-index.json` binds 81 copied local receipts/images to original and public hashes. Historical pending visual/audio statements remain as original receipts; current close and final review state the final bounded verdict.

The local publisher and checker reuse the main T25 implementation and byte-identical restoration comparator. They make zero device/network calls. Remote archive verification is pending a separate receipt; this package does not claim remote publication. Source/build/deployment provenance remains in the existing T26/T27 and T26 deployment packages. No frozen API promotion or general reliability claim is made.

```sh
python3 benchmark/2026-10-20-t26-window-evidence/check.py --base "$HOME/.local/share/westlake/toutiao-resume-20261020"
```
