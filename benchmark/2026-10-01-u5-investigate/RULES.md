# Five candidate families, not five forced diagnoses

All predicates operate on a verified application PID and its TIDs, inside the
selected first-attempt capture. They never scan compositor output. A `candidate`
is a triage lead, not a claim that repairing it makes the UI visible.

| Family | U5 selected keys | Required evidence / implementable rule | Repair or next probe |
|---|---|---|---|
| Waiting for network | 0 | Explicit outstanding request/callback wait; associate start/completion and app state. A timeout, OkHttp class name or advertised online network alone is insufficient. | Instrument network callback registration/completion; if a real missing callback is proved, repair the service callback contract rather than merely return online. |
| Waiting for permission or dialog | 0 | Actual request/dialog + pending response tied to Activity token; class linking a DialogInterface/permission method or startup diagnostic-fd EACCES is insufficient. | Preserve permission/result callback and dialog window/token ownership; require a concrete denied/pending request before adding a permission shim. |
| Window created, no frame submitted | 0 | App-owned window plus explicit first-buffer/draw wait, no later swap/submit witness; missing log instrumentation alone is unknown. | Add per-surface frame sequence, swap return, OH flush result and presentation receipt; correlate with the foreground token. Reuse existing typed APP_CONTENT machinery only after binding its deployed version. |
| Caught exception | fd-noice, noice | Executed SubscriptionRepository cancellation wrapping NoClassDefFoundError SSLSockets, process still alive; class-linker diagnostics never match. | T7d SSLSockets fallback class is the existing candidate. Require repository completion, then independent t20 review; not the dropped MediaServiceManager stub. |
| Other / insufficient evidence | fd-AppManager, fd-organicmaps, termux | Positive lifecycle finish/relay/service-start evidence without a proved network/permission/frame wait. | Trace result delivery for AppManager; process/launchMode relay for Organic Maps; Android Service/bootstrap lifecycle for Termux. See results.json. |

## Rules implemented now

First subtract `knowledge/gates/benign-log-signatures.json` through `benign.partition`
using the exact U5 context. Seventeen reviewed signatures are supported by at
least three distinct lit packages; keep raw matched lines and signature IDs.
Fatal terminal markers bypass subtraction. A different runtime/boot/generation
gets no suppression. The CoroutineStart probe/stack requires the explicit
COROUTINE-FIX caught header, not a bare ClassNotFoundException.

`classify.py` parses date, time, PID and TID explicitly. `scoped` rejects a
timestamp/string masquerading as PID. `summarize` identifies Java main from
`CM-BIGSTACK ActivityThread on dedicated pthread`, not `pid == tid`.
The latter is the launcher, which detaches before joining the dedicated thread.

The classifier excludes JNI registrations (`-> fn=`, OH_RegHook) and ART
`class_linker.cc` metadata from execution predicates. It records window creation,
swap entry, explicit submit return, lifecycle callback and caught exception as
**different fields**. Category rules are evidence candidates, not static APK
proof: a transport failure alone stays `other` unless an explicit wait is logged.

The actual U5 logs have no matching explicit successful-submit receipt even for
lit aegis/anki controls. Therefore zero such receipts **cannot** identify a
frame-submission regression. The pre-clear swap probe runs before the real swap;
`gl_err=0` is not the swap return (source-review.json `swap-order`, lines 898-937).
Termux has an ability `first-frame` callback but an already finished Activity with
no decor: the label is not a rendered-frame or own-UI witness.

## Not implemented as a static wall

An APK API/UND scan cannot see a swallowed runtime exception, incomplete Activity
result or pending callback. The deliverable is a PID-filtered runtime-log rule
and repair shortlist, not a new claim that B10 can statically predict all blank
screens. Static prerequisites may enrich these candidates later; ordering still
requires runtime evidence. Do not retrofit this retrospective cohort into U6/U7
accuracy or frozen CSVs.
