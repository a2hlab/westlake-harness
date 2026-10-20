# T14: existing child UI observation, playback unverified

This 292.89-second window used the existing child1601/b7706984 and parent19163/b7265322 on boot0525bb05. Six original screenshot receipts and JPEG hashes are verified; all images were independently read. The first is the lock screen, followed by a news feed, video-tab cards and the post-play card. UI/control changes are visible, but the final two full JPEGs are byte-identical 39.63 seconds apart. This does not establish moving video or audible playback. A visible pause/mute control is not a playback verdict.

The saved frame is complete only for its selected65536 bytes. It covers the first64KiB of a30863473-byte log interval, not the complete interaction. Exact framing, host rc, payload SHA and post marker were checked using the original decoder. The first fatal event remains unknown; absence in this prefix cannot exclude later errors. Media-bearing selected bytes remain private.

The producer writes screenshot.json rather than record.json. The original run_facts output therefore reports zero recognized records; it is retained unchanged. Actual six-image evidence comes from the six original screenshot receipts. No synthetic record or alive counter is created. Original profile/process guards are separate evidence.

Restore returned rc0, original power Timeout/OverrideTimeout10000/10000 was read back, and unlock returned rc0. No runtime build/replacement, app signal, reboot or debugger attach occurred. This packet contains only this completed window, its exact historical wrappers and source references. Later native supplements are separate and are not claimed here. Complete raw command/output material is in the persistent private archive; no media URL/token is published.
