# r7 exact logging observations and restored baseline

A default no-op logger implementation did not describe the active callback in the actual child. Missing log lines did not establish a playback failure stage. The earlier draft also mislabeled the deployed runtime format as `%{public}s`; exact ELF bytes at `0x43a5c` are `[%s:%u] %s` (see `runtime-format-proof.json`).

The candidate used the previously reviewed four files and the single temporary log parameter. In boot `904a55b5-1821-4f23-aa50-b08b731c0234`, parent 4979/b6990 and child 6951/b8704, a real feed-card tap entered a video page. The t20 and t25 screenshots were byte-identical static cover images. Playback did not pass; audio is unknown.

Eight guarded reads found verbose=1, callback_enabled=0, the player's log-print GOT pointing to exact liblog `d8ad176b` +0x7548, the property GOT pointing into the mapped webview shim, and the liblog logger pointing into libbase. Supplemental guarded reads found the loggability GOT bound to the same liblog +0x9ce8 and the libbase function object targeting runtime `8ab6742d` +0x1b2fa4. These are point-in-time observations, not proof that every producer call traversed that chain. The runtime HiLogPrint GOT remains unread. Two complete libhilog mapping groups exist; another caller's C00f00 output cannot substitute for this caller's binding.

At 22:39:03 +0800 the board was unlocked after restoring the exact original files from this window's apply plan, a fresh boot, original parameter absence (errNum106), private/source hashes and inodes, absent compat library, unchanged init config, and a real icon-open feed screenshot. The same 62-target state plan completed before and after with equal collection hashes. See `results.json`; approval covers restoration only.

`window-archive.json` records a remotely hash-verified 7,452,482-byte archive containing original commands, captures, logs, memory-read receipts, and static LLVM output. Its parameterized location uses the configured private artifact root. Large raw artifacts and private data are not embedded in this public repository.
