# T102 — same-thread POLL elapsed intervals, not a defect finding

Rechecked T99's five saved rc0 receipts, their raw-manifest hashes, target identity8ab6742d… and exact ordinary timing excerpt lines. `tracePoll` enter/exit use fresh `clock_gettime(1)` calls and `tv_sec*1000 + tv_nsec/1000000`; integer milliseconds are supported statically. The runtime provider and relation to trace/wall clocks remain unproven. No REA was invoked. T95B input SHA2ee3a988… and T100 timeline are pinned.

Actual parser/checks rc0:3,405 complete enter/exit pairs, all TID6311;6,821 WAKE records never used as endpoints. One partial final line excluded. No other actual nested, malformed, orphan, negative/out-of-order or pointer-mismatch pair occurred. Eight synthetic checks cover valid pairing, WAKE, nesting, wrong-thread ends, missing ends/begins, backward/negative values and truncation. Top10 raw endpoints were independently re-read for kind/TID/internal pointer equality and numeric subtraction; public evidence omits pointers.

| Rank | Original enter / exit lines | Integer-ms counter endpoints | Elapsed ms | Raw timeout |
|---|---|---|---|---|
|1|23188 / 23881|1445815 → 1446203|388|388|
|2|24406 / 24958|1446414 → 1446777|363|362|
|3|27005 / 27459|1447585 → 1447911|326|622|
|4|19612 / 20313|1444292 → 1444591|299|706|
|5|27480 / 27829|1447912 → 1448208|296|295|
|6|21719 / 22270|1445130 → 1445377|247|247|
|7|22294 / 22766|1445386 → 1445624|238|817|
|8|20345 / 20697|1444593 → 1444825|232|405|
|9|22769 / 23072|1445625 → 1445790|165|578|
|10|25629 / 26000|1447076 → 1447221|145|1131|

The union covers **17,830ms** across1,566 merged segments. This is elapsed coverage of logged POLL regions, not CPU time, continuous blockage, a component's startup duration or a critical path. Neither a long interval nor timeout=-1 alone establishes a defect. Missing records are not waits, and integer-ms equality does not prove zero work.

Results include original main-thread counters adjacent in file order to Activity/WebView/render stage lines1419,2036,5023,5868,6945,6965. These neighbors are not stage timestamps or valid time bounds across interleaved/buffered logs. No trace/wall subtraction or birth-tick conversion is performed.

Reproduce `analyze.py --input <T95B private head.stdout> --t99 <fixed T99 directory> --t100 <fixed timeline results.json> --output <new results path>`. It reads evidence only and runs its eight local parser cases. Raw invocation/receipts and the initial verbose union result are retained in `.private/`; final public output is compact. Original logs remain private. No device, stopped-source, deployment or Git retry; author_commit=null.

## Outer independent review

The independent replay returned rc0 and reproduced the author result exactly. See `outer-review.json`; raw replay receipts remain under `$HOME/.local/share/westlake/t100-t102-outer-review-20261023/`. A separate parser confirmed the complete POLL pairs, Top10 endpoints and elapsed union. The calculated 0.421221-second screenshot/WebView ordering is conditional on a cross-host clock mapping whose skew is not bounded, so it is not an established subsecond chronology.
