# Toutiao controlled-exit and player-load observations

P0 manual icon recovery failed after an identity-guarded **controlled SIGTERM**, not a natural crash. P1 subsequently reached a real player-library load and failed on `SL_IID_ANDROIDSIMPLEBUFFERQUEUE` in namespace 0. A visible video cover is not playback success. These are separate observations on separate boots.

## P0: controlled exit, parent preserved, reentry refused

Outer evidence uses the directory name `icon-manual-live-r2`; this report calls the observed candidate failure P0 r1 to match the handoff. On boot `f59c05dd-85b1-40f9-8ad5-baec804d642f`, child 7233/birth16206 first displayed a recommendation feed. Outer sent guarded SIGTERM. The guardian remained at sequence 1 and entered `OWNER_REFUSED child_identity_changed_no_signal`, rather than manual wait. The subsequent process observation found the child absent and the original parent 5430/birth14767 still sleeping. A recorded desktop icon click then displayed only Westlake IME host.

The static birth/ownership multi-read race is consistent with this event; the retained event does not identify the exact failed sub-read. This report does not relabel PID reuse or unreadable identity as exit and does not approve a guardian fix.

## P1: first observed blocker for this player load

After rollback and baseline boot `8f7f12bf-fc42-49c6-b398-2fea3ab4363c`, a video-card tap was recorded for child9290/birth17865, parent5287. Child stat identity matches before and after. The original stderr delta, line20741 (outer full-log grep reports line215889), explicitly records:

```text
[SOURCE-NATIVE-LOAD-FAIL] path=/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so namespace=0 error=Error relocating /data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so: SL_IID_ANDROIDSIMPLEBUFFERQUEUE: symbol not found
```

This confirms the player-load blocker for that attempt; it is not inferred from maps or a missing trace. It does not establish a repair, audio output, decoder success, or the actual native Surface consumer.

I directly inspected the private t20/t25 images before writing this report: both show the same video-detail cover and layout. Their original SHA256 is also identical. No playback progression is demonstrated; the two stills do not describe every intervening frame. Pre-exit feed and post-exit IMEhost images were also directly inspected. Original app content and screenshots are not published here. [facts.txt](facts.txt) reports captured flags extracted from the original records, not planned counts; [results.json](results.json) records the independent image judgments separately from the original pending-review fields.

## Rollback and evidence limits

Outer restored `/system/etc/init/01_westlake_u13_toutiao.cfg` to SHA256 `1589c9f20f7da7d141e6d91c612be622a04e021af0f50407217d2cb1e0396796`. The new boot above has the original U13 `state=READY`, `layers=56` receipt, and the corrected attempt-root read lists the original controls. The earlier baseline receipt contains a failed `ls` against a wrong root; it remains an acknowledged failed subcommand despite transport rc0. This report does not turn READY into UI success. The outer-reported four transaction `ICON_REMOTE_RC=0` markers are not independently attested here without their raw transaction receipts.

## Private provenance and public delivery

[source-pins.json](source-pins.json) binds each original file by full SHA256 and byte size under the portable private location `$HOME/.local/share/westlake/toutiao-resume-20261019`. Resolve HOME for the evidence custodian; these private originals are not assumed to exist in every checkout. Remote archival status is not asserted. [technical-excerpts.json](technical-excerpts.json) contains only selected verbatim technical lines with original line numbers. All other app content, complete stderr/hilog, network information, command archives, commercial APKs and decompilation bodies stay outside this delivery.

Only this new benchmark is changed. No HDC, installation, board command, shared README/DIGEST/API edit or push was performed by the reviewer. [landing-paths.txt](landing-paths.txt) is the exact outer landing whitelist; `SHA256SUMS` covers every listed file except itself. No execution framework or new acceptance gate is introduced.
