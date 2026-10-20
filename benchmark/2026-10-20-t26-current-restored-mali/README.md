# Current restored Mali driver: private artifact index

**Scope: CURRENT_RESTORED_DRIVER.** The read-only collection belongs to restored 5cd boot `bda1a809-fb3b-4ad8-8400-9c18f02b443a`. It does **not** independently establish the driver bytes present during the earlier T25 candidate window.

The exact current file is `/vendor/lib64/chipsetsdk/libGLES_mali.z.so`, **16,734,912 bytes**, SHA256 `e0cb108121981c6ad30c9e3f338c384172ef3be2dc790a457e0287a10efa2cfe`. Both boot-guarded read receipts completed, with matching SHA and `dev:inode:size:mtime` values before/after transfer; the received file matches. The original collection lock/holder/unlock receipts are preserved: unlock rc0, held-after rc1 with empty stdout, close marked unlocked. The collection recorded zero device writes; this publisher made no device calls.

The unchanged vendor binary and every original collection receipt are stored only in a private remote archive:

- Alias: `HW248_ARTIFACT_ROOT/t26-current-restored-mali-20261020-e0cb1081/driver.tar.gz`
- Archive SHA256: `d6316b2059d40582e13f8ad9d94932955a38f9cd2fb82f60b1785ce039c4b2f7`
- Archive size: **7,297,134 bytes**
- Members: **36**, comprising 35 original files and their manifest; all member hashes and sizes verified locally and remotely
- Remote directory/file modes: **700/600**; unique absent-only directory creation, three transfer commands rc0, no overwrite

The Git package contains only metadata, indexes, the archive verifier and sanitized command receipts. No vendor binary or vendor source is published here. Original argv/stdout/stderr/rc remain privately persistent; their hashes bind the sanitized versions to original evidence. The exact read-before/read-after equality is evidence for this collection, not a retrospective T25 deployment fingerprint or proof of runtime symbol selection.

This archive records a later restored-system artifact for bounded offline analysis. It adds no API implementation, runtime fix, EGL diagnosis or video pass.
