# T17 R9-derived network reuse window — closed, playback not passed

The `continuous` captures were relaunched news feed, not continuous video by the original child. The earlier restored screenshot `7de4a7f8` was an empty loading shell; only the later `6d14aca2` screenshot is accepted as the restored news feed. Both originals remain in this packet/archive.

The window closed after 1722.409 seconds. Actual paired media getaddrinfo/freeaddrinfo bindings matched netcompat. The selected private log interval [9297968,40929709) contains 31,631,741 bytes, SHA256 `4c4893c463f2074619ef580c7b1179afbcaade65b9d3f03d8f8a1e7884c289eb`. Its 254 mirrored rows are limited by the 256-row budget. Packet read/decoder setup, repeated AudioTrack JNI errors and ANW CPU-path diagnostics do not establish video or audio success, a unique root cause, or global disappearance of network errors. Technical excerpts are pinned to MAIN commit 15171a8271.

The first candidate child exited; the retry candidate's original child 7906 later exited and guardian seq2/seq3 records identify relaunches. No random-exit cause is assigned. The observer's old-PID guard failed before stage mkdir: transport rc 0 contained explicit remote rc 1. There was no server stage, attach, forwarding or observer sample. These failures and the initial false baseline-ready wait are retained unchanged.

The original apply-plan rollback returned rc 0. On restored boot `04564c50-0d6e-4420-8db4-b9581b3658f7`, parent 10470/b26828 and child 12232/b28159 were observed. Original run/media/player SHA values matched in physical and private views; compat was absent in both. Power was restored to 10000/10000; ready was true and the log parameter was absent (106). All eight comparison domains of the 518-target/812-label snapshot matched, and the 26 supplemental targets matched byte-for-byte except the boot line. This is the 5cd 544=518+26 scope, not the 61b 64-target scope. Unlock rc 0 and held-after rc 1/empty were checked.

Independent image review confirms the final news feed. Outcome: **video NOT_PASSED; audio UNKNOWN; paired binding MATCH; baseline restoration and window closure verified**. No lasting runtime change or playback promotion is claimed.

The original `run_facts.py` output is in `final/facts.txt`:

```text
TOTAL keys=3 screenshots_captured=3/3 alive_t5=0 alive_last=0 alive_unknown=3
```

These record-based counts do not include all screenshot.json captures. Separate image hashes do not manufacture liveness counts.

`checkpoint-01` and `checkpoint-02` retain their earlier pending states and frozen bytes. `final/` appends actual closure. The complete raw archive includes every file in this window (failures, retries, audio-source read, observer guard, snapshots and close), T17 helper originals/preparation, exact reused binary inputs, and pinned producer-source copies. Large stderr, media URLs and raw payloads remain private. Public receipts use portable aliases. `final/archive/receipt.json` records local verification only; outer must execute the three argv in `.private/archive-01/remote-commands.private.json` before remote success can be appended.

No device or network commands were executed by this evidence lane. `build_final.py` requires explicit `--write`; `finalize_packet.py` defaults to read-only verification. No historical outcomes, frozen program bytes or API rows were changed.
