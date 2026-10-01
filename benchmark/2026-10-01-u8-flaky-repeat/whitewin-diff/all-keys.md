# White-window diagnostic rule generalization (all keys, offline)

Dispatch (ACK(80) 2026-10-01T17:45:53): generalize the white-window diagnostic rule from wikipedia/fd-noice to all run_index rows with unknown_session>0 (runtime e953c0921536). Compare query counts vs signed t20 results; lit keys as control group.

## Numbers first

From run_index (runtime e953c0921536, unknown_session>0): **148 rows**.

By signed t20 result (outer sign-off `benchmark/2026-10-01-u8-sweep/outer-signoff.json`):

| t20 result | rows | query_count>=2 | query_count==1 | query_count==0 |
|---|---|---|---|---|
| lit | 105 | **95 (90.5%)** | 10 | 0 |
| alive-white-window | 17 | 12 (70.6%) | 5 | 0 |
| dead | 8 | 4 (50.0%) | 3 | 1 |
| unknown (not in sign-off) | 14 | 14 | 0 | 0 |

## Conclusion

**The diagnostic rule does NOT hold.** In the lit control group, 90.5% of rows have Activity session queried twice or more (query_count>=2) — nearly as common as in white rows (70.6%). The difference between lit and white is not the number of queries but which session is rescued by the last-session fallback (the Activity in lit, the icon in white). The rule「white = Activity session queried twice」is wrong; the real discriminator is which session's window ends up in the foreground slot (per the double-load analysis in `double-load/REPORT.md`).

The single row with query_count==0 is `fd-uhabits` (61b r1, lit) — a single-Activity app with no icon session, so no Activity session queries at all.

## Method

- `timeline.py` (whitewin-diff) per key: extract createSession / getOhNativeWindow / unknown sessionId lines; Activity session = last createSession (highest sessionId); query_count = unknown sessionId lines for that session; first_query_interval_ms = from icon session create to first Activity query.
- Join with outer sign-off `benchmark/2026-10-01-u8-sweep/outer-signoff.json` for t20 verdict.
- No board writes; all files in t4 worktree.
