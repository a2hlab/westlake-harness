# #45 morning integration (2026-09-26)

Board61b0657200000000000000000324012c only. Independent worktree/branch
westlake-harness-operator45 / deploy/operator-toutiao-45. Commits only, no push.
The existing ability38-v7 framework's307 files were rehashed and unchanged.
Runtime remains the feed-capable #14/out-sp20 base with sscronet native and
network targets, single-process WebView and AndroidSurfaceControl disabled.
No compilation or system-partition change.

## Installed payload

Backups are in `/data/local/tmp/operator45-crashes/morning46-upgrade/`, with
original SHA256 in each filename. Actual executed runtime:
`/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d`.

| Runtime file | Installed SHA256 |
|---|---|
| webview-t-lib/libwebview_bionic_shim.so | ecc7b12c3591c979f3d9aece5bb1d414acc04d01d2c500a88364525082f9df9f |
| liboh_adapter_bridge.so | d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b |
| lib/arm64-v8a/libnpth.so | 8b8d559c50130a997b5fbf3383e8ebf6291ebe54ab2b5ed5fbc8e1ac73fe36af |
| run.sh | 17781b81e25db11125883474d932a63743dd56f59ebba3e53eb39c80582b0548 |

The requested helper adds ttcrypto/ttboringssl/delta; lynxsecurity was already
present. Window parent remains40 for this board, explaining why run.sh differs
from the 5ea34a45 copy. No new15-library closure was mixed in. The supplied apply_ld_preload.py also
prepends `/data/local/tmp/asx/lib/arm64-v8a/libttcrypto.so` to LD_PRELOAD.
A second application was byte-identical; the live child environment confirms
crypto is first. This changes default-namespace HMAC binding, as requested.

max_map_count was65530 and is now1048576. The resident guardian sets and checks
it on guard startup and before every app respawn, records startup-settings.log,
and refuses to spawn if that write fails. It also applies24h display timeout
and wakeup on recovery. The setting survives app/guardian restart by reapplication;
this is not a system boot service and does not promise automatic recovery after
a board reboot. Clock was set, wlan0 had192.168.0.41, public IP ping2/2 succeeded.

## Setup and recovery observations

The original warm data reached feed but child6204 exited(1) after97s and8881
exited(1) after89s, both with X.DEv creating Handler(null Looper). These are
retained failures, not successful stability windows. Controlled SIGKILL8450
was archived separately as signal9. All were automatically restarted by the
board-resident guard; startup-settings.log records the sysctl before each spawn.
An attempted article tap from an obsolete screenshot is invalid and excluded.
The input helper now refuses a stale bound PID before physical injection.

Original app-data/data/webview-t-data were renamed, not deleted, into runtime
`profile-backups/morning46`. One fresh launch initially failed before socket
creation because the new mount directories were missing; the launch helper
now creates them with the same ownership/context as the proven #38 launcher.
Fresh child16089 showed the consent dialog. A real physical uinput tap at
(600,1273), uptime92117.38, accepted it; the subsequent screenshot shows feed.
After sync at92171.90 a controlled restart preserved consent: subsequent warm
children reached feed without that dialog, but several failed before becoming
usable or exited within about 1–2 minutes. No repeated consent automation is
built into the guardian. Before the final fresh session, this profile was also
renamed into `profile-backups/morning46-fivepatch`; no profile was deleted.

Final fresh child4047 accepted consent physically at uptime92873.63. Its first
article input was uptime93112.96; NewDetailActivity RESUMED was93125.901
(12.941s). The article1-later screenshot shows the CCTV tea-meeting article,
real image and multiple readable paragraphs. This is a body success, **not a
<2s latency pass**. Further observations are recorded below.

## Guardian behavior and handoff

Checks PID/starttime every3s; while the instance is alive it sends no focus
requests or touch input. On exit it archives stderr/parent/faultlog/cppcrash
and timestamp first, then removes other Toutiao processes (including PPID1
orphans), reapplies sysctl/power and warm-starts the same stage. INDEX records
sequence/time/lifetime/signal/PID/cleaned/ppid1; late fault/reap data is retained.
The prior <10s feed-recovery target remains unproven; PID creation is not UI
readiness. Recovery INDEX rows6–17 retain12 exits: five exited(1) with the main-thread
Handler(null Looper) exception, five signal11 (exact crashing DSO not proven by
the captured stderr), and two intentional SIGKILL tests. Seven archived logs
contain a separate work_thread SIGABRT; this is not equated to the app exit.
Row12 records one PPID1 orphan removed. Row15
wrongly recorded92486s because the child had already died when the old guardian
attached; treat that lifetime as unknown. Commit55d07d8 fixes future instances,
and the original INDEX remains untouched as evidence.

Stage: `/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d`.
Current pointers are `/data/local/tmp/operator45/{child.pid,parent.pid,guard.pid,child.stderr.path}`.
Archive: `/data/local/tmp/operator45-crashes/`.

To stop only the guardian, in this board's shell:

```sh
touch /data/local/tmp/operator45/stop
kill $(cat /data/local/tmp/operator45/guard.pid)
```

This leaves the current app running. The guardian itself needs no VM connection.
All VM access in this task uses `orb -m a2hlab bash -lc '<command>'` with explicit61b target.

## Physical article and stability evidence

All article selection and back/favorite navigation used `uinput -T -d x y -u x y`.
No i/c injection counts toward these results. Same app PID4047, birth9275899
jiffies, parent4014, guardian6272; monitor checks guardian child pointer, process
birth/state and archive sequence at every sample, so automatic recovery cannot
masquerade as survival.

| Article | Input uptime(s) | Detail RESUMED(s) | Input→RESUMED | Separate no-input observation | Screenshot |
|---|---:|---:|---:|---:|---|
| CCTV tea meeting, video cover + body | 93112.96 | 93125.901 | 12.941s | 127.44s, same PID, 41 samples | [body](evidence/morning46-article1/stable-125s.jpeg) |
| CCTV international reaction, video cover + body | 93373.91 | 93376.261 | 2.351s | 127.41s, same PID, 41 samples | [body](evidence/morning46-article2/stable-125s.jpeg) |
| Xinhua Mid-Autumn, video cover + body | 93559.30 | 93562.059 | 2.759s | 190.74s, same PID, 61 samples | [body](evidence/morning46-article3/stable-190s.jpeg) |

All three measured launches exceed the historical <2s target. This handoff
checks readable bodies and survival; it does not close #38 latency or prove
video playback. First two windows span uptime93174.15–93301.59 and
93398.52–93525.93 respectively. Maps ranges9724–9856 and10568–12463;
RSS936.63–1005.14MiB and1074.92–1135.63MiB. The old65530 ceiling was not crossed,
so this does not establish the max_map_count change as the cause of survival.
Third window93570.69–93761.43 lasted190.74s with no input or restart;
maps12607–13044, RSS1001.92–1144.32MiB. It meets the requested continuous
≥3min observation. All three observed windows kept archive sequence17.

During the third article a10.16s stat/wchan sample found npth-dumper-thr6309
used0ms CPU and waited on futex; npth-worker used0ms, profiler10ms. Both sampled
RenderThreads and Chrome_InProcRe used0ms and waited on epoll/futex. This is a
bounded sample, not a claim that every npth path is repaired.

## SQLite-related smoke check

Physical favorite tap in the first article opened the login sheet. Closing it
returned to the same article with a yellow star and count100→101. No credentials
were entered. This demonstrates in-session UI response; durable collection was not verified. Physical “我的” opened a full login page;
closing it returned to feed. History/offline UI was not exercised past the login
gate. No SQLiteException or SQLiteDatabaseCorruptException appeared in the
collected app log, but this is not a comprehensive SQLite/HMAC regression pass.
[Favorite response](evidence/morning46-fivefresh/after-close.jpeg),
[login gate](evidence/morning46-fivefresh/mine.jpeg).

## Final result and remaining limits

The five-fix deployment and current-instance three-article / ≥3min smoke test
are complete. **R2=partially**: deployment and the bounded observed results are
verified, while warm-start reliability, <2s interaction, overnight stability,
video playback and full SQLite regression remain unproven or blocked.

Final health check at04:02:36: child4047, parent4014, guardian6272, uptime93961.74.
Same child had lived1202.75s (20.05min) from its recorded start, without guard
replacement. It is left at the information-feed homepage, not the login screen.
[Handoff feed](evidence/morning46-handoff/feed-final.jpeg).
Final runtime SHA256 values match the table, wlan0 remains192.168.0.41 and
public-IP ping succeeded2/2. The board has no `ip` binary; interface data was
retrieved with `ifconfig wlan0` and retained in handoff/actions.jsonl.
Authoritative live pointers are listed above; static PID values can become stale
if the guardian later recovers a crash.

`child.stderr` is
`/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/private-tmp/adapter_child_4047.stderr`.

Collected live log: GLES translation to platformsdk/libGLESv3.so=1;
GrGLInterface creation failed=0, InitializeGL failure=0, codec “No implementation”=0,
Fatal signal5/11=0, TicketGuardNetw=0. From the first lifecycle-level detail ENTRY
through final collection, Fatal signal=0 and UnsatisfiedLinkError=0. Across the
**entire startup log**, work_thread6598 SIGABRT=1 and platform-back-handler
metasec UnsatisfiedLinkError(errno13)=1 occurred before the first article. The
Chrome_ProcessLauncherThread also reported missing child-service metadata.
These are retained limitations, not hidden by the article-window zero counts.

Earlier five-patch warm child28339 entered NewDetailActivity but exited(1) before
body rendering; it is excluded from successes. The final4047 profile was freshly
consented after preserving earlier data; this exact fresh profile was not
restarted after its successful article run. Repeated reliable warm recovery is
therefore **still blocked**, despite persisted consent having been observed in
prior warm attempts. The current working instance is intentionally left live
for outer-loop review and operator use.

The502-file evidence manifest was checked against both stored and decompressed
SHA256 values. Source/target backup hashes are in
[deployment.json](evidence/morning46/deployment.json) and
[preload deployment.json](evidence/morning46-preload/deployment.json).
