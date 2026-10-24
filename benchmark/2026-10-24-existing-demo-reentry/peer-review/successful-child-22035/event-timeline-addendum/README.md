# Same-boot event timeline: most waiting precedes recorded spawn

The previous44-second click-to-child estimate now has an intermediate boundary: **about42 seconds precede logged `spawn_started`; birth follows about2–3 seconds later and `reentry_spawn_ok` about4 seconds after that start marker.** This identifies an interval, not a root cause.

| Evidence | Same-boot time | Observation |
|---|---:|---|
| Prior command-bracket estimate |65309.07–65309.74| Ordinary click, approximate uptime |
| events.stdout:21–22 |42343| Old child6291 exit and retirement recorded |
| events.stdout:23 |65351| child_retirement_cleared spawn_started |
| Bound stat + measured CLK_TCK100 |65353.69| Child22035 birth |
| events.stdout:24–25 |65355| reentry_spawn_ok and BOOTSTRAP |
| events.stdout:28 |65374| Logged first_feed_observation |
| events.stdout:31 |65394| Logged READY |

Event labels have only integer-second precision. Nominal differences2.69/1.31 seconds are not precise event timings; no control implementation was read to establish rounding or clock source. Alignment uses the supplied same-boot uptime interpretation and the prior short-window clock assumptions. No Mac wall-clock subtraction. Outer had already seen feed in s60 before the65369.90 uptime sample, so65374/65394 are subsequent logged observations, not first visible-frame timestamps.

All HDC receipts in discovery/data return0; held is separately rc1. Both boot reads match. State6B/events5744B match the recorded sizes and hashes; pre/post stat bytes are equal. Current state is READY. Events21–22 record retirement, but no transition_target appears between22 and23. This is a missing transition record, not proof that the state file never changed or proof of why a delay occurred.

**One discriminating question remains:** does an already-recorded ordinary host foreground/request timestamp lie near the click (~65309) or near spawn_started (~65351)? Early would place most waiting after that host boundary; late would place it before. Current events cannot answer. No repeat launch, device call, implementation read, or new logging is proposed here. Private raw paths and exact pins are in results.json.
