# R11: debugger handshake failed; baseline restored

The assumption that the installed SDK debugger could supply native-window call
observations was not verified on this kernel. The actual SDK15 server attached to
the requested child but asserted in `DataExtractor::GetMaxU64` and exited during
connection. No stop reply reached the client, and **zero fromSurface or lock
calls** were recorded. The specific caller/register and whether the invalid size
was zero or greater than eight remain unknown. This does not diagnose Toutiao's
random exits or prove a window-object layout.

The 61b window ran from 04:17:06 to 04:30:24 (+08:00), 798 seconds. It reused the
exact R10 runtime tuple and the [R11 observer](../README.md), with no runtime
rebuild. Fresh GOT reads again mapped six window imports to libandroid76512d97
and lock/unlock to shim85c789f4. The third normal icon attempt reached a real feed;
the video page image is a single capture, not evidence of moving playback.

The observer refused before breakpoint installation. Its cleanup was unverified
because connection never established a usable stopped process; external identity
checks independently showed the original child sleeping with TracerPid=0 and the
parent unchanged. Outer still restored the original files using this window's
[original apply plan](original-apply-plan.json) and cold-booted before unlocking.

Restored boot8423f320, parent5035/birth7509, child7583/birth9034 reached the
[actual feed](restored-feed.jpeg) after one normal icon and one network-retry tap.
Source/private hashes and inode identity, absent compatibility DSO, parameter106,
and the same64target/351label snapshot invariants all matched the original baseline.
[Results](results.json) sign only the diagnostic and restoration, **not video**.

The literal fact totals are in [candidate facts](candidate-facts.txt) and
[restoration facts](restoration-facts.txt). Their keys are capture groups of one
APK, not distinct apps. Missing scheduled process tables stay unknown; exact
process identities are separately recorded. Video NOT_PASSED, sound UNKNOWN.

All raw commands, receipts, scripts and snapshots are in the remotely SHA-verified
[persistent archive](archive-receipt.json). Public excerpts normalize home/producer
build paths; [original hashes](private-source-index.json) bind their unmodified
private originals. `r11_outer.py`'s first command-line check failed because HDC
text truncated NUL bytes; `r11_finalize.py` checked `od` bytes and owned socket
inode before execution. Forward removal first failed while quoted; reboot removed
the forward, and the final listing was empty. Neither failed command is called a
successful cleanup.

Next rule: prove attach, two hardware hits, continuation and detach on a dedicated
owned probe on an idle board before any successor window touches Toutiao. A
successful isolated probe will still not establish application playback.
