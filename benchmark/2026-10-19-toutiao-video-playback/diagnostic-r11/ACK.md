# ACK video-2020-r11-call-observation

Offline implementation ready for independent outer review. 11 Python cases and
three Rust selectors pass; t6 lint 100%. No device connection or attach was made.
Exact pins, parent UID 0 / child UID 20011206, remote-ohos, phase-exact tracer,
new stop-ID and finally cleanup are enforced by runtime code.

Entry: `observe.py --admission FILE --port PORT --out NEWDIR [--execute]`.
Without `--execute`, validation is local only. The disabled sample deliberately
cannot pass admission. Actual hardware/attach and caller observations are unknown.

Outer must retain a recovery window. Incomplete/failed cleanup is never playback
success. No CC checker was used as admission. No unrelated dirty file was changed.
The manifest/landing list is the exact delivery boundary. Git index is outside
this lane's writable sandbox; outer may commit/land these exact files.
