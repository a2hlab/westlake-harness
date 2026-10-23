# T92 successful launch latency: unknown, no optimization candidate

The trace does not justify charging the entire post-spawn delay to a slow UI operation. Input is T87 SHA `f9a2fe0a…`; boot/seq2/PID6291/birth142694 bind via `raw/02/s30.stdout:9`. Birth ticks are retained as ticks; the integer spawn-confirmation uptime1428 is the timing anchor, not a precise birth timestamp.

**Integrity.** Thread ID comes from the line header; recorded process ID comes from B/E. Only same-thread, same-PID LIFO pairs with matching named ends enter the ranking. Bare E is excluded and taints enclosing spans; named/PID mismatches reset that thread's stack. No duration is assigned to incomplete pairs. There are2925 accepted intervals and399 excluded target intervals (144 bare ends,144 discarded on name mismatch,111 tainted). Full trace has530 orphan explicit ends,43 name mismatches and4 unparsed fragments; all retained in JSON. No async/counter markers observed. Ten parser fixtures pass; independent cx-env review remains pending.

| Operation | TID | ms inclusive | Trace lines B/E |
|---|---:|---:|---|
| WorkerThread active | 7872 | 317.291 | 5549/6332 |
| WorkerThread active | 7880 | 309.420 | 6461/9336 |
| WorkerThread active | 7880 | 291.544 | 4005/4972 |
| gl::init::CreateGLContext | 8626 | 131.671 | 4327/4869 |
| SetScreenAndroid | 6311 | 106.030 | 2469/2763 |
| gpu_info_collector::CollectGraphicsInfoGL | 8626 | 93.207 | 3940/4226 |
| HTMLDocumentParser::NotifyScriptLoaded | 8628 | 71.263 | 4958/4996 |
| HTMLParserScriptRunner::executeScriptsWaitingForLoad | 8628 | 71.173 | 4959/4987 |
| HTMLParserScriptRunner ExecuteScript | 8628 | 71.092 | 4960/4986 |
| PendingScript::ExecuteScriptBlock | 8628 | 71.067 | 4961/4985 |

Do not sum this nested ranking. Global wall-time union of accepted spans is **1.446397s**, not CPU time or critical-path latency.

**Coverage.** Spawn confirmation1428 → first6291 marker1461.881765 (`content::Start`, trace2229) leaves approximately33.882s without a child marker. This is not evidence of no execution or the first window. A recorded clock-sync pair (9580/9581) maps the network-error capture to about1460.965–1461.461 and feed capture to1490.651–1491.230. The trace ends1490.657, before the feed capture bracket ends; last6291 marker is1490.256223. These are capture brackets, not exact transition onsets. Internal gaps are enumerated in `intervals.json`; absence of a complete span is not an inferred wait or network cause.

**One gap.** Existing instrumentation leaves the early~33.9s and much of subsequent activity unaccounted for, and no deployed source binding exists here for the ranked child WebView/worker operations. T89's HAP EntryAbility binding does not supply that binding. Optimization remains **unknown**; no patch or new collection was initiated.

Reproduce: `python3 benchmark/2026-10-23-successful-launch-ui-latency/parse_trace.py --output "$HOME/.local/share/westlake/successful-launch-ui-latency-20261023/outer/intervals.json"`; tests: `python3 -m unittest discover -s benchmark/2026-10-23-successful-launch-ui-latency -p test_parser.py`. Full results and original-line excerpts accompany this note. No device, deployment or T91 action.

Outer addendum: the original pending-peer statement above is superseded by `review/outer-rerun.json`: six reviewer fixtures and all Top10 original-line checks independently passed; ten owner tests also passed. Full derived intervals remain at the persistent private locator in `outer-review.json`; public summaries and the exact parser are retained. This accepts evidence only, not a fix or seal.
