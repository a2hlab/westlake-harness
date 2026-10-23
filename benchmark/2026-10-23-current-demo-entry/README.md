# T107 — 61b current-instance demo entry: icon tap resumes the existing video page

At 20:40:09 the existing instance was still in place:
- Child 6291 was alive, with birth 142694 (the same as in T106).
- The guardian state was READY.
- Power was SLEEP.

The lock was held from 20:40:20 to 20:41:54.

## What happened under the lock
1. **After wake and unlock** (`u0-after-unlock.jpeg`): the screen showed the existing Toutiao UI on a **video detail page** (东莞无人驾驶), not the recommend feed. That page was already open before this card.
2. **Home, then one icon tap** at 20:41:02, at WorkSpace_1 (189,234) from a fresh layout.
3. **At t5, t20 and t30** the app came back to the same video detail page with the video playing. It was the same child 6291 with an unchanged birth, no new child appeared, and the guardian stayed READY (last event 1496, historical).

## What was not done
- No back key.
- No article or video tap.
- No reboot, kill, deploy or network change.

## Screenshot count
From `run/facts.txt`: `shots 4/4`.

## Restore
Power was restored and read back as 30000/10000. The board was unlocked. The screen was left on the video page. 5cd was not touched.

## Scope
This is a desktop return to the current instance, **not** a cold-launch signoff. The current demo state is a video page, not the feed homepage.

## Outer review

The outer reviewer viewed s30 as a Toutiao video detail page. Facts were regenerated and matched; held returned rc1 after release. A changing video image is not a new audio confirmation. Raw files are SHA-indexed in `raw-manifest.json` and retained in the persistent private archive.
