# Accepted host-page update on the 61b demo device

Previously 61b still displayed the development Westlake title and input while Android started. The exact T32 same-signature HAP is now retained on **61b**: one normal desktop icon tap after a normal reboot automatically reached the real Toutiao recommendation feed. Root reviewed three early empty backgrounds without the development controls and two later feed images; an independent peer checked the final image and all seven signed evidence references.

The fresh installed original was byte-identical to T32's rollback HAP (`df385638…`). The retained candidate is `b18978b8…`; only `ets/pages/Index.abc` changes inside the nine-member package. Source, exact Linux compiler replay, signing recipe and raw build receipts are in [the source/build package](../../2026-10-20-toutiao-launcher-page/README.md). The [61b executor and reference](../static/README.md) use this board's actual UID/token, guardian and runtime, rather than 5cd parameters.

## Actual acceptance

- UID20011206 / accessTokenId537243994, five data-directory identities and labels, 18 guardian files and the installed package list were preserved. The original guardian derived WID33→30; the rest of run.sh is byte-identical. Four recorded runtime libraries and init configuration remain unchanged; OpenSLES compat remains absent.
- New boot3394710e-965c-47cc-a9f5-2b06f3d6c3f1; host4859/b6415/WID30, parent5066/b6658; child7039 is independently recorded. Physical/private runtime hashes and inodes were checked against the same parent.
- Retain signed at325.997 seconds; window closed and unlocked at326.466 seconds. Original power30000/86400000 and debug-parameter absence were restored. No uninstall or data clear occurred.
- First sampled feed was74.339 seconds after the single icon click. This is a sampling bound, not exact launch latency or a speedup claim. Cold-start waiting remains.

[Early background](early-background.jpeg) · [first real feed](first-feed.jpeg) · [final real feed](final-feed.jpeg) · [results](results.json) · [actual retain decision](retain-decision.json) · [close](closed.json) · [peer check](peer-closure.json) · [unaltered facts](facts.txt).

## Scope and provenance

This is a host-page update only. The 5cd video runtime was **not** transferred, no new 61b playback pass or random-crash fix is claimed, and the original V2 seal remains historical evidence. Two boards running the same app do not satisfy the two-different-app public API freeze gate. Directory metadata preservation does not prove mutable data bytes unchanged.

Original command records, before/after identities, all five images, exact new/rollback HAPs and the source/build package are retained in a private durable archive. [Archive receipt](archive.json) and [member hashes](archive-members.json) describe actual remote verification once present; they do not imply Git publication. The initial read-only probe used unavailable tr and two incorrect library paths; those original results are preserved, and exact od/real library paths were used for acceptance. Recovery prechecks intentionally reject foreign or drifted identity; automatic rollback is not claimed for every identity/data/runtime failure.
