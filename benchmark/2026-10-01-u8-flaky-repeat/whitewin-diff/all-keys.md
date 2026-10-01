# Fallback-target verification: which session the last-session fallback rescues (148 rows, offline)

Dispatch (ACK(80) 2026-10-01T17:55:23): verify the new claim "the difference is which session the last-session fallback rescues" on the same 148 rows (runtime e953c0921536, unknown_session>0). Evidence from hilog; verdict joined per run (sweep → outer-signoff.json; flaky-repeat → per-round sign-off; no sign-off → unknown).

## Numbers first

From run_index (runtime e953c0921536, unknown_session>0): **148 rows**.

By signed t20 result, with `rescued_activity` = the last-session fallback returned the Activity session's OHNativeWindow, `rescued_icon` = it returned the icon session's:

| t20 result | rows | rescued_activity | rescued_icon |
|---|---|---|---|
| lit | 106 | **99.1%** | **88.7%** |
| alive-white-window | 11 | **100.0%** | **36.4%** |
| dead | 8 | 87.5% | 87.5% |
| unknown (no sign-off) | 19 | 100.0% | 73.7% |

## Conclusion

The new claim **partially holds**. In white rows, the fallback rescues the Activity session **100% of the time** but rescues the icon session only **36.4%** of the time — the icon's window is abandoned. In lit rows, the fallback rescues the Activity session **99.1%** of the time *and* the icon session **88.7%** of the time — both windows get content. So the discriminator is not "how many times the Activity session is queried" (the old rule, disproven) but **whether the fallback rescues the icon session too**: white rows abandon the icon's window, lit rows rescue both.

The single lit row with query_count==0 (fd-uhabits) is a single-Activity app with no icon session — no Activity session queries at all, so it is outside this rule.

## Method

- `timeline.py` (whitewin-diff) per key: extract createSession / getOhNativeWindow / BBQ.update / unknown sessionId lines; Activity session = last createSession (highest sessionId); icon session = first createSession; rescued_sessions = sessions with BBQ.update OHNativeWindow=non-null; rescued_activity = Activity session in rescued_sessions; rescued_icon = icon session in rescued_sessions.
- Join with outer sign-off `benchmark/2026-10-01-u8-sweep/outer-signoff.json` for sweep keys; flaky-repeat keys (wikipedia/fd-noice/fd-uhabits) use per-round sign-off (lit r1/r2b/r3 for wikipedia, lit r1/r3/r4 for fd-noice, lit r1/r4 for fd-uhabits; white r2/r4/r5 / r2/r2b/r5 / r2/r5 respectively). Keys with no sign-off are marked unknown.
- No board writes; all files in t4 worktree.

## Outer-loop reading of fallback-target.csv (2026-10-01 18:02)

The lane's headline (lit rows rescue the icon session 88.7%, white 36.4%) counts single-session apps, where the icon
session *is* the Activity session (e.g. helloworld 110/110), so "icon rescued" is trivially true there. On the 44 rows
whose icon and Activity sessions differ:

| t20 (per run) | rows | icon session rescued |
|---|---|---|
| lit | 28 (23 keys) | 16 (57.1%) |
| alive-white-window | 8 (5 keys) | 1 (12.5%) |

Rows where the icon was not rescued: 12 lit, 7 white -> P(white | not rescued) = 7/19 = 37%; P(white | rescued) =
1/17 = 6%. A risk factor, not a discriminant: almost every white run skips the icon session, but most runs that skip
it still light. The cure stays the single bridge owner (N11c): with one WMClient table there is no unknown sessionId
and no fallback to win or lose.
