# REJECTED: next4 is evidence, not a signed runtime

Package SHA 72a4bf19892e1d0b6455b4c07da80c2c3ef41828b4e59b212c7904150547863d.
Built from signed v3c with host 124e2341, ANL df97f918 and runtime 356386a1.
Do not use inherited README metadata as next4 acceptance.

The 5cd/r17m test eliminated the old musl slot-3 fatal in this run but ZigZag
crashed in ANativeWindow_getFormat through Mali/EGL. HW/Auxio/NetGuard retained
UI. VLC advanced from missing newAudioSessionId to missing
__pthread_cleanup_push in libvlc.so and returned to desktop. Candidate rejected
and rollback to v3c requested by the recorded control rule.

Authoritative report and rollback receipt:
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/benchmark/2026-09-30-v3c-next4-namespace/
No deployment authorization is implied by the presence of this package.
