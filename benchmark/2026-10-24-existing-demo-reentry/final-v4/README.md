# T123 observed existing-version feed recovery

**One ordinary desktop click recovered content on the existing 61b version.** Outer visual review identified Chinese text feed and bottom navigation at s60, then loaded images/video covers at s90. This is not proof of video playback, cold startup, a white-screen fix, or seal. No runtime modification or API freeze was performed.

Earlier windows stopped before a click; they are not failed-reopening experiments. Their raw receipts remain private and unchanged. The accepted v4 recorder keeps one owner, consumes the final-image review, reserves one icon click, and preserves an accepted feed while restoring power and releasing its lock. Layout lock-node flags alone cannot establish the visible screen; even the earlier white screenshot had a lock node marked visible/focused.

Evidence: [host white](screenshots/host-white.jpeg), [s60 text feed](screenshots/s60.jpeg), [s90 loaded images/covers](screenshots/s90.jpeg), [facts](facts.txt), [machine-readable receipts/index](results.json). Visual verdicts are attributed to the outer reviewer; image bytes match the private originals.

- Run: `run-20261024-110541-e2b1c729`; boot `61aa5791-fd69-4bbb-a7b5-333b5d913c81`.
- T0: **11:05:41.342327 +08:00**. Preflight passed all 21 control hashes and fresh host 4958/appspawn 5129 identity, with no article child.
- Outer approved the post-unlock white screen before T+120. The unique page-0 icon was clicked once at **11:06:42.788100**, T+61.445s. Capture offsets below use the recorded click reservation, 1.657ms before dispatch.

| Nominal sample | Actual image-ready offset | Article child in associated ps |
|---|---|---|
| 10 | 10.519s | none observed |
| 30 | 30.472s | none observed |
| 60 | 60.582s | 22035 |
| 90 | 90.519s | 22035 |

PID **22035**, PPID **5129**, UID **20011206** is absent at s10/s30 and present at s60/s90. This brackets first observation between the 30/60-second samples; it is not an exact spawn/birth timestamp. The process-table file and line for each observation are retained in `results.json`.

The s60 feed review was published at **11:08:25.915858** and consumed at T+164.752s. s90 had already been captured before this review; s120 was not captured. No failure Home occurred. Cleanup finished at **11:08:26.565560**, T+165.223s: power readback `Timeout=30000ms / OverrideTimeout=10000ms` exactly matched its preimage; final held rc1 with empty stdout/stderr confirmed release. Raw command outputs remain under `$HOME/.local/share/westlake/existing-demo-reentry-20261024/<run>/`.

Reproduce this read-only evidence check (no device calls):

```sh
python3 benchmark/2026-10-24-existing-demo-reentry/final-v4/check_evidence.py
```

The final executable package is [v4](../launch-package-v4/README.md), pinned by [ready](../launch-package-v4-ready.json). The v3 full-entry 12-case tests and the v4 residual-lock replay are retained separately. Remaining latency analysis is a separate task; this observation does not establish its cause.
