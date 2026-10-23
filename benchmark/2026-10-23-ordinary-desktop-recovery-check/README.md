# T72 — ordinary desktop Toutiao tap on the current boot (61b, 33f35797)

One ordinary desktop tap, no reboot, no network change, no diagnosis.

## Evidence
- Pre: board free, network connected (IPv4/RUNNING/route), guardian AWAITING_REENTRY with no child.
- Tap 13:09:18 on the layout-located icon (WorkSpace_1, 189,234). t30 screenshot white, no child yet.
- Guardian events (`evidence/guardian-events-t120.txt`): reentry spawn started ~+31 s, child 10877 born, `first_feed_observation` and `READY feed_confirmed` at ~+57/+63 s, then `process_exit` / `child_retired` at ~+70 s.
- t120 screenshot white, child gone; state file still says READY (stale relative to the last event).

## Result
FAIL for the card: the feed was not on screen in our t30/t120 screenshots, so no article/return step was taken. The guardian's own classifier briefly saw the feed between t30 and t120, which is reported as a fact, not as a pass. Stopped without retry; no cause analysis. This is not a boot first-launch result.

## Addendum: guardian feed capture (read-only receive)
The recorded t120 boot-dir listing named `feed-2.jpeg`. That one file was received read-only (sha256 69994601…, mtime 13:10:21.51, ~+63 s after the tap, matching the guardian READY event) and is published unmodified as `04-guardian-feed-2-1310.jpeg` (logged-out feed, no account data). It shows the Toutiao recommendation feed rendered between our t30 and t120. Our own t30/t120 frames remain white, so the card result stays FAIL; the feed did not persist to t120.

Outer review: [outer-review.json](outer-review.json). All 395 private manifest entries, eight cited raw receipts and four public image hashes verified. Independent image review confirms a feed at 13:10:21.51, but the later 120-second image is blank; these are different observations, not contradictory verdicts. The three new card screenshots and one received guardian screenshot are counted separately. Private originals remain at `$HOME/.local/share/westlake/ordinary-desktop-recovery-check-20261023/`.
