# T86 — read existing launch output for child 7049 (boot 61aa5791)

Outer review update: the initial directory-only inventory below is superseded by the supplemental `raw2/` collection. The ordinary file `/data/service/el1/public/appspawnx/adapter_child_7049.stderr` was found and its last 200 lines collected; it is outside the guardian directory. Its mtime is 17:00:29, with several lines explicitly identifying PID 7049 and that time. Missing optional archive entries and class-loader warnings do not establish a fatal dependency error. Exit cause remains unknown. A zero-byte readiness log does not prove when sampling started.

The read was read-only and stayed within budget: 180 s monotonic deadline, at most 20 s per command. It used 0.7 s, made no retries, and wrote nothing to the device. The boot matched and no other holder was present.

**Result: no ordinary stdout/stderr from child 7049 exists in the known guardian boot directory.** None of the files read references any stdout/stderr log path. No explicit application error was found. The conclusion stays **unknown**, and T85 stays FAIL.

| File | Content |
|---|---|
| `state` | `AWAITING_REENTRY` |
| `events.log` | The same 6 events as T85 (uptime 110–137) |
| `spawn.txt` | `[JIT50-PREPARE]` art-volatile directory check OK; `HOST_SPAWN result=0 pid=7049` |
| `parent-start.txt` | `5129` |
| `readiness-reentry-7049-12973.jsonl` | 0 bytes |
| `classifier.log` | 0 bytes (from directory metadata; not read) |

Raw receipts are in `raw/` (argv/start/end/rc/stdout/stderr per command; `$HOME` redacted). The private originals are at `$HOME/.local/share/westlake/existing-launch-output-20261023/raw/`.
