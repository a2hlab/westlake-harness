# Read-only 61b preinstallation inventory

The Boat provider cannot assume that an installed APK or its BMS UID exists merely because two native libraries remain in the package directory. This capture found the original Unity and IL2CPP libraries, but no Boat BMS registration, no base APK, and no signal-box target. A missing-package path must preserve those existing libraries and collect the actual new UID after installation.

`summary.json` records the result. The 497 requested file targets were read on boot `9f5af7c8-d359-4c25-99c6-63206b50cf0a`. All 319 baseline hashes matched; all 487 Route B files and the host HAP matched their v1 identities. Exactly two requested paths were absent. Device writes: **0**.

The capture is deliberately **incomplete for deployment**: `complete=false`, `boat_uid=null`. It must never be promoted to a complete capture by filling guessed values. Installation, fresh identity collection, independent review, and protected-board authorization remain separate steps.

The first collection attempt incorrectly normalized the local cfg text. Its hash check rejected it. `first-attempt.py`, `collector.log`, and `current-recover.normalized-bad.cfg` retain that failure. `capture.py` preserves the exact raw stdout prefix before the remote status marker. The corrected local cfg matches the independently read device hash `7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1`. Existing raw receipts were reused only after exact command matching; subsequent reads and the ending boot receipt are retained in `raw/`.

`capture.json` includes source receipt pins. New-directory metadata is a declared future recipe, not an observation that those directories exist. Route B user directories were checked for metadata only; no user contents were read or copied.
