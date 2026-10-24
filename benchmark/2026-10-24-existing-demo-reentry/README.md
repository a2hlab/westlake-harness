# T123 existing 61b reentry observation — not yet executed

Two initial observation windows made **zero Home actions and zero app-icon clicks**. They do not establish whether the existing reentry behavior works. A current child was absent; the same host/appspawn identities and 21 historical control hashes were confirmed. The outer viewed the [unlocked blank app region](initial-white.jpeg).

The first window closed before a late outer approval could be recorded. The second received an outer review at T+66.388 seconds, but its local waiting loop never consumed the review file and cleaned up at T+120. A later continuation found the lock released. This is a local UI-recording handoff defect, not evidence that a desktop launch failed. Both windows restored base/override timeouts to 30000/10000 and released their locks.

Some same-named stage/held files were overwritten by the late second continuation. The preserved snapshot explicitly records this limitation and does not recover earlier bytes. Original restoration and unlock receipts remain available. See `outer-observations.json` for the persistent private archive and SHA pin. The next action is offline repair and testing of the actual single-worker entry before another board window. No runtime patch or white-screen repair has been delivered.
