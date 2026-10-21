# G01: guardian retained; video not sealed

Earlier gray-screen retries did not prove that the guardian could create a new child. G01 changed only the guardian control generation and its init cfg entry. A normal reboot and normal icon produced a new child and a populated Toutiao feed. The outer signed **guardian-only retention**; this does not complete video delivery.

| Link | Actual evidence |
|---|---|
| Source | r3 watchdog `8bf74a08…`, strict exited-instance retirement; original r2 remains preserved |
| Generation | Armed r3 payload,20 deployed files; full member/entry/startup chain and original generation/test stdout/stderr/rc in the private archive |
| Transaction | Reviewed guardian deployment `b6a79dd6…`; apply returned `PLACED_REQUIRES_NEW_BOOT`; cfg `7b9f2c0e…` |
| Runtime | New boot `40dcce48…`; guardian3996/b3997, parent5762/b16535, child7762/b18314; original video runtime retained |
| Visual | [Normal-icon feed t90](feed-t90.jpeg) and [final feed](final-feed.jpeg); final image independently viewed |
| Closure | Signed retain `5295106c…`; actual board UNLOCK at09:41:00,731s after09:28:49 start; power30000/86400000 and debug absent106 after UI |

The original signed receipt is preserved in the archive. `retain.sanitized.json` substitutes HOME aliases and records the original hash; it is not substituted for the signed bytes. No original close.json existed: `closure-index.json` indexes the actual UNLOCK/ACK, signed retain and final raw identity/power receipts. It does not invent a held-after probe or silently rewrite the window.

Natural child exit followed by manual reentry was **NOT_OBSERVED**. No forced exit or new audio confirmation occurred. The retained guardian relies on explicitly scoped offline retirement tests plus this fresh startup/feed observation. Video remains **NOT_SEALED** and requires a separate window with the new guardian hashes. The invalid private `/data/app` compat lookup is retained as history but is superseded by the actual parent-private `/data/local/tmp/asx` evidence in y07.

`source-index.json` pins27 exact source/generation/transaction/runtime/image references. The complete immutable window, source generation and tests are in [the verified archive](../guardian-archive-01/README.md). W05 is excluded. No API table was edited by this report.
