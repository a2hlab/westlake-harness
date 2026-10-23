# T100 — launch timeline, with clock/coverage boundaries

Actual offline reconciliation rc0;34 input references pinned. T87 boot61aa5791…, seq2 child6291/birth142694/parent5129 are confirmed by the saved spawn receipt. T89 source binding is reused as accepted metadata; no supervisor or lifecycle source was reread. No T99 input or now conversion is used.

| Event | Evidence/time | What this does and does not establish |
|---|---|---|
|Icon click|click.start/end:17:21:34.691–17:21:35.137|Command bracket, not exact input-dispatch instant|
|Host foreground|trace245:1401.750138; host4958 spans in T89|Framework completion marker; not a child request timestamp|
|Java/runtime anchor|T95B22:17:22:00 PID6291|Already emitted before spawn-confirmation time; confirmation is not birth|
|Spawn confirmed|s30.stdout9:uptime1428, child6291/birth142694|Integer-second success receipt; no birth-tick conversion|
|Java verification|T95B345/432/435:17:22:03/04/05, TID6311|Reported288.259/226.991/137.893ms; not whole initialization durations|
|Main-thread later anchor|T95B5023:17:22:10, PID6291/TID6311|Class-verification message; not render timestamp|
|Activity posting / draw registration|T95B1419/1421/2036|Untimed file-order observations, no completed onCreate inference|
|Render flush / swap|T95B5868/6945/6965|Submission progress; explicit time/TID absent, not visible first frame|
|First WebView trace marker|trace2229:1461.881765; mapped~17:22:35.311|content::Start, NOT process birth or first UI|

Screenshot command brackets (main files hashed against private originals; t30/t60/t90 independently viewed):

| Sample | Wall UTC+8 command bracket | Image observation |
|---|---|---|
|t10|2026-10-23T17:21:44.544+08:00 → 2026-10-23T17:21:44.916+08:00|white; inherited accepted T87 visual review|
|t30|2026-10-23T17:22:04.409+08:00 → 2026-10-23T17:22:04.796+08:00|white; independently viewed for T100|
|t60|2026-10-23T17:22:34.393+08:00 → 2026-10-23T17:22:34.889+08:00|Toutiao navigation/interface and error text visible; independently viewed for T100|
|t90|2026-10-23T17:23:04.080+08:00 → 2026-10-23T17:23:04.658+08:00|feed list and video card visible; independently viewed for T100|

The realtime/trace sync is trace9580 (1490.657048, realtime1792747384086ms); conversion is an estimate from one pair, with no independently bounded host clock skew/drift. On that mapping, **t60's rendered UI capture ends0.421221s before the first WebView marker**. Thus missing PID6291 markers before content::Start cannot establish no execution/rendering. Host foreground→spawn confirmation is approximately26.25s; confirmation→first WebView marker approximately33.88s. Neither is attributed to a component. T92's1.446397s interval union is observed coverage, not total work.

White at t30, app UI/error text at t60 and feed at t90 are sampled states. They do not establish continuous white duration, first UI instant, first feed instant, or monotonic presentation. Native swap records do not substitute for screenshots; the error text does not prove a network cause.

**Most discriminating next normal observation:** in a separately authorized normal launch, use bounded passive screen recording or fixed screenshot brackets plus existing process identities to distinguish first visible app UI from first feed across the unsampled transitions. Second: only if already available, obtain same-identity ordinary request/acceptance/spawn completion receipts to resolve the~26s handoff gap. Neither is executed or authorizes stopped instrumentation/T91; no third broad investigation is proposed.

`reconcile.py --main <main tree> --output <new result>` reruns local evidence checks. Raw argv/start/end/rc/stdout/stderr are private and indexed. No device/REA/stopped-source/permission changes. Known shared Git-ref denial is not retried; author_commit=null, path-only handoff and no push.

## Outer independent review

The independent replay returned rc0 and reproduced the author result exactly. See `outer-review.json`; raw replay receipts remain under `$HOME/.local/share/westlake/t100-t102-outer-review-20261023/`. A separate parser confirmed the complete POLL pairs, Top10 endpoints and elapsed union. The calculated 0.421221-second screenshot/WebView ordering is conditional on a cross-host clock mapping whose skew is not bounded, so it is not an established subsecond chronology.
