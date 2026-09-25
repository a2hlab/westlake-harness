# #45 operator instance and resident recovery

R2: **partially**. Deployment, persisted consent, physical tab switching, crash archives,
and stale-process cleanup are verified. **Recovery to a usable feed within 10 seconds
is blocked.** A live PID alone and a retained old window are not UI recovery.

Board: `61b0657200000000000000000324012c`. Independent branch
`deploy/operator-toutiao-45`; commits only, no push. c40 PID 1460613 had exited
before deployment. No system partition changes.

The framework is `/data/local/tmp/a2hlab-framework-operator45-v7`: all 307 payload
hashes match ability38-v7 (bridge `e4ab5de64d20b8da6c7f388a7d5f5efd536f2962bb3913975e89ce824300c45a`).
The app stage is `/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d`.
Its runtime is `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d`.
All #38 native/net targets and WebView settings are retained; the only run.sh
change is parent window ID 31 to 40. This uses the feed-capable #14/out-sp20
candidate, not out-all0925. Clock, 24-hour display timeout/wakeup and WiFi were
configured; wlan0 was 192.168.0.41 and the connectivity probe succeeded.

One setup consent was entered by real `uinput -T -d 600 1273 -u 600 1273`.
A second launch preserved application data and did not need consent again.
The optional login screen was dismissed. The early tab attempt while that login
screen was present is invalid, retained as raw evidence. The subsequent physical
military-tab touch changed titles and displayed real images (warm/tab-loaded.jpeg).
A later live-instance physical touch changed to the small-video category and showed
real pictures (live/physical-tab-loaded.jpeg). These are hardware-path uinput
results; mailbox `v` requests only inspect the view tree, with no i/c injection.
Tab animations/reordering mean the final selected category, not an earlier screen
coordinate's label, is authoritative. The small-video return to recommendation
produced a blank content area; it is retained, not counted as a healthy homepage.
A final data-preserving restart was performed for handoff.

The board-resident `/data/local/tmp/operator45/watchdog.sh` checks the recorded
PID and process start time every 3 seconds. While it lives, the loop sends no
focus requests or touch input. On exit it archives child.stderr, parent.log,
exit time and matching faultlog/cppcrash files **before** restarting the same
stage, preserving data, and foregrounding the host. Late reap/fault files are
collected for up to 120 seconds. INDEX contains sequence, time, lifetime, signal
or exit status, PID, `cleaned` and `ppid1`. The latter distinguishes true PPID=1
orphans from other extra Toutiao processes.

Before every spawn, `pidof com.ss.android.article.news` is scanned. Every live
match except the recorded current app PID is killed after a start-time recheck;
no unrelated process names are targeted. Each killed PID/stat is archived.
Manual cleanup at 00:21:52 removed 6367 (PPID 5617), preserving 5617. PID 29135
was already absent. A later natural exit left 15047 with PPID=1: the guardian
removed it automatically, recording `cleaned=1, ppid1=1`. Another handoff cleanup
removed 16820, preserving 16012. These are observations, not an npth ABI fix.

Recovery evidence:

| Event | Result |
|---|---|
| Controlled SIGKILL 28505 at uptime 80279.93 | New PID 5617 by +3s; MainActivity RESUMED at 80312066ms, +32.136s. +10s image retained old window; +80s shows a real feed. |
| Controlled SIGKILL 5617 at uptime 80750.16 | New PID 14155 by +3s; MainActivity RESUMED at 80789172ms, +39.012s. +10/+40s show the host, not feed. |
| Natural exit 14155 after 61s | Parent reports exit(1); stderr contains Handler/Looper null pointer in X.DEv, with ActivityThread event loop returning. A cppcrash file is also preserved; do not conflate these records. Orphan cleanup=1; restarted PID16012 reached feed. |
| Final reset of 16012 | Guardian restarted 20992; it died with signal11 after16s and was archived. Guardian then restarted again. See handoff-reset and final live evidence. |

The first INDEX row says `unknown`: that original guardian had not yet captured
the late signal9 reap. The late parent record is retained in guard-test/parent-reap-late.txt.
Other rows contain actual parent reap records. SIGKILL did not necessarily produce
a cppcrash. Fault-path lists preserve absence rather than inventing a dump.

Final observation at 2026-09-26 00:29:22 CST: app PID **21556**, parent **28483**, guardian **13542**; WMS focus window **351** belongs to PID21556. `pidof` returned only21556 after final cleanup. [Final recommended feed with real images](evidence/live/final-home.jpeg) and [physical tab result](evidence/live/physical-tab-loaded.jpeg) are preserved. The instance and guardian remain running.

Current PID is deliberately a pointer, since crashes replace it:

- `/data/local/tmp/operator45/child.pid`
- `/data/local/tmp/operator45/parent.pid`
- `/data/local/tmp/operator45/guard.pid`
- `/data/local/tmp/operator45/child.stderr.path`
- `/data/local/tmp/operator45-crashes/INDEX`

Stop the guardian only (leave the app alive), in a board shell:

```sh
touch /data/local/tmp/operator45/stop
kill $(cat /data/local/tmp/operator45/guard.pid)
```

Use the authorized target explicitly when accessing from the VM; all VM commands
are invoked with `orb -m a2hlab bash -lc '<command>'`. The resident guardian does
not require the VM to remain online. Crash archives are available to #46 at
`/data/local/tmp/operator45-crashes/` and copied into `evidence/crash-archives/`.
There is no claim that article latency, WebView crashes, ICU crashes or overall
stability are fixed. The preloaded parent is reused and old windows can persist.

Run `python3 benchmark/2026-09-26-operator-toutiao-45/verify.py --git` to verify
stored/compressed/raw hashes against committed HEAD blobs. Scripts were syntax
checked; recovery and cleanup were exercised on the real board. Evidence is
collected under the VM's `~/a2hlab/board/<serial>/operator45/` then exported here.
