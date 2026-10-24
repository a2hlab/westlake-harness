# Post-Home WMS query appendix

`rc=0` does not establish a valid per-window response. This independent appendix preserves two existing read-only collections; no device action or source/causal analysis was performed by this review. The parent report and historical image-review attribution remain unchanged.

| Existing collection (+08:00, 2026-10-24) | Observation |
| --- | --- |
| Help, 12:44:58.594060–12:44:58.914180 including identity brackets | Actual help says `-w {window id} [ArkUI Option]`. |
| Per-window, 12:45:12.029797–12:45:12.454634 including identity brackets | `-w 53`, then `-w 32`: body says arguments are illegal despite rc0. `-w 62`: structured window response, PID10486, ParentWindowId0. |

Both collections are bracketed by boot `61aa5791-fd69-4bbb-a7b5-333b5d913c81`, host10486/birth7039472 and child22035/birth6535369. [results.json](results.json) preserves every actual argv, rc, command start/end and extracted identity. [raw-manifest.json](raw-manifest.json) pins all 24 private receipt/stdout/stderr files by exact path, bytes and SHA256. [wms-body.txt](wms-body.txt) retains the WMS bodies without blank/decorative headers; no personal log or raw process-stat body is copied.

These queries occurred **after Home at 12:33:37–38**, not at t90. `IsVisible=false`, `isRSVisible=false`, `FirstFrameCallbackCalled=1` and `ParentWindowId=0` describe the later query response only. Neither the illegal response nor the historical filename `old-session53` proves a session missing. No rendering success, attachment or white-screen cause is inferred. Exact public delivery: [landing-paths.txt](landing-paths.txt).
