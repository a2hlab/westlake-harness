# T17 checkpoint 02 — window not closed

The three captures named `continuous` show the news feed after guardian relaunches. They do not demonstrate continuous video playback by child 7906. Their original bytes and capture metadata are retained. No record-derived liveness count is asserted here.

The actual getaddrinfo/freeaddrinfo read bytes match both expected netcompat addresses. The reader returned rc 0; its source profile SHA and before/after file identities agree. The selected private log interval is exactly [9297968,40929709), 31,631,741 bytes, SHA256 `4c4893c463f2074619ef580c7b1179afbcaade65b9d3f03d8f8a1e7884c289eb`. The 26 technical excerpts remain pinned to MAIN commit 15171a8271. This interval includes 254 mirrored rows under a 256-row budget, so absence of a network-error literal is not global error absence. AudioTrack JNI error groups and ANW CPU-path diagnostics are observations, not proof of one exclusive playback cause.

The observer stage rejected the old PID before mkdir: transport rc 0 carried explicit remote rc 1. No stage, attach, forwarding or observer samples followed that guard. The later guardian seq2 exit and seq3 READY records remain distinct from the first candidate child.

Rollback returned rc 0. The first baseline ready wait recorded disconnected/false results; the later retry recorded true on boot 04564c50. Final identities, snapshot closure, feed restoration and unlock remain pending in this checkpoint. No whole-window archive is created before final close. Checkpoint 01 is unchanged.

`prepare.py` defaults to read-only and requires `--write` into a fresh packet directory. It only reads local evidence. Public paths use aliases; the complete log remains private. `landing-paths.txt` is the exact public whitelist.
