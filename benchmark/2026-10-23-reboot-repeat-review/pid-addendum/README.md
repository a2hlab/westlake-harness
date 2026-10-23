# T110 addendum — sampled child PID changes

The first slice remains unchanged. The completed p90/p120 receipts now rule out summarizing T109 as one child observed through the endpoint. They do not establish who initiated a subsequent launch or why an earlier process ceased to appear.

| Sample | T108 child / PPID | T109 child / PPID | T109 focus window |
|---|---|---|---|
| p10 | not listed | not listed | 29 |
| p30 | 7111 / 5305 | 7011 / 5201 | 31 |
| p60 | 7111 / 5305 | 9860 / 5201 | 29 |
| p90 | 7111 / 5305 | not listed | 29 |
| p120 | 7111 / 5305 | not listed | 29 |

All ten ordinary process-sample receipts have rc0. T109 host5074 and parent5201 are listed in all five samples. T108 host5171 and parent5305 are listed in all five. Numeric PID recurrence is not birth-identity or continuous-liveness proof. Absence means not listed by the supplied filtered ps invocation, not a measured exit instant.

T109 process receipt host intervals:

- p30: 1792766543.931842–1792766544.169667; stdout line5 child7011/PPID5201.
- p60: 1792766573.992396–1792766574.214452; stdout line5 child9860/PPID5201.
- p90: 1792766603.948423–1792766604.100113; no matching child row.
- p120: 1792766633.790601–1792766633.963765; no matching child row.

Device wall-time labels and uptime are preserved separately in results, without subtracting them from host time. Each run has one recorded reboot and one ordinary UI click in the pinned argv inventory. T109 click body is `No Error`, rc0. This command-count statement is bounded to retained receipts.

T109 s60 SHA is in results alongside its screenshot/receive rc. The outer message explicitly reports s60 white. T108's existing outer/sentry review reports t60 feed. This is a sampled visual difference between two software reboots, not a root-cause or triggering-mechanism conclusion. Other T109 visual labels await the outer review. Final T109 record/facts and restoration have not been reviewed here; the private ordinary child prefixes and state events are not analyzed by this addendum.

## Reproduce

```sh
python3 benchmark/2026-10-23-reboot-repeat-review/pid-addendum/check.py > /tmp/t110-pids.json
cmp /tmp/t110-pids.json benchmark/2026-10-23-reboot-repeat-review/pid-addendum/results.json
```

`--root` selects the retained private Westlake evidence root. Input membership and SHA are frozen in input-index.json. Do not recapture over this addendum. Both original local executions, stdout/stderr/rc and times remain in `.private/`. No captured command is executed; no device, REA, stopped-object analysis, git commit or push occurred.
