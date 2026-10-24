# T131 ordinary foreground record observation — incomplete

No Toutiao icon was clicked. No window-state sample was acquired. Foreground publication and persistence remain unknown; this run cannot assess app recovery or child read access.

Three sequential lock holds shared the original 01:31:03–01:41:03 budget; they were not one continuous observation. The first stopped on an unknown black screen, the second timed out awaiting visual review, and the third consumed the outer review of a desktop image but then correctly rejected the later black desktop-labelled image. All three released their own locks. Counts are generated in `facts.txt` from actual receipts and image files.

The third run set override 600000 before UITest, but omitted immediate and post-UITest effective-value readbacks required by main `.octos/OPS-RUNBOOK.md:301`. A reset by UITest is **not established**: the only final power read followed our explicit restore. The third run restored override 10000 at 01:37:20 +08, read base 30000 / override 10000, and released at 01:37:21 (final-held rc1, empty streams). This is a recorder limitation, not a Toutiao root cause.

`raw-index.json` pins private commands, timings, return codes, streams, layouts, images and visual-review receipts; bodies and screenshots remain under `.private/`. `results.json` contains sanitized identities and per-run outcomes. The three `observe*.py` files are historical executed sources, **not corrected reusable entrypoints**. Recompute metadata offline with `python3 benchmark/2026-10-25-toutiao-foreground-record/summarize.py`; it never executes recorded commands. No runtime payload was changed.
