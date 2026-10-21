# G34 post-close diagnostic plan: exit status is not a crash stack

**Observed:** at23:22:11.437 parent27555 reports child29761 exiting with signal11.
The original3797-line hilog hashes to
`4ab5cf4964011c89cfb90e35065f6d28c362add3eee4de50cf2a15903fff1da2`.
It contains no fault PC/stack. The actual command was
`hilog -x -P 29761,27555`, so it is not a complete view of independent diagnostic
processes. The corrected post-close `hilog -z 2000 -T DfxFaultLogger` finished
at23:36:46.128 with rc0 and zero stdout/stderr bytes. The older combined `-x -z`
query returned a CODE-31 body despite outer rc0; both originals are retained.
An empty later tag-filtered buffer does not prove no report was ever emitted.

## What the retained source explains

`appspawn_service.c:181–188` handles SIGCHLD with `waitpid(..., WNOHANG)`;
`HandleDiedPid:169–171` passes the wait status to `DumpStatus:110–119`, which logs
WTERMSIG or WEXITSTATUS. This normal parent reporting path has no faulting thread
context, register collection or stack unwinder. It therefore explains the format
of the parent line, **not why a separate normal crash report is missing**.

The next observed `Invalid signal fd[0]` matches `WriteSignalInfoToFd:124`.
That routine emits pid/uid/signal/bundleName JSON after the exit-status message.
It contains no PC/stack fields. Its failed notification must not be relabelled a
proven cause of missing DFX output.

The early, stat-bracketed child maps contain route `libsigchain.so`,
`/system/lib64/platformsdk/libdfx_signalhandler.z.so` and
`/system/lib64/chipset-sdk-sp/libfaultloggerd.z.so`. Thus “DFX was never mapped”
is unsupported. The snapshot precedes the terminal event and lacks mapped-file
process-root SHA binding; it proves neither the active final handler nor its
registration/execution. Earlier MUSL-SIGCHAIN lines concern signal4, not the final
signal11. They cannot identify the final faulting thread or explain its outcome.

## Build/source binding limits

The actual G26 host build receipt and ELF match the fixed rollout host
`ee5649f2778430e1c997f4bb2d4d4f42f53a46208b4a1b1bbaca185ddf401887`.
The recorded link consumes `candidate-service-1.o` and `appspawn_dfx_dump.o`;
their current bytes are indexed. The retained appspawn service source matches the
observed line114/124 format strings, but this review does not establish its exact
source-to-object equivalence for that prebuilt service object.

The local OH public mirror supplies DFX headers, not the full signal-handler and
musl-dispatch implementation or deployed build commands. `dfx_log_define.h`
defines the DfxFaultLogger tag; `dfx_log.h` has compile-time logging conditions,
including DFX_NO_PRINT_LOG. Those are possible build configurations, **not evidence
that this device uses one**. The repository also retains more than one sigchain
build configuration; none is newly bound here to the mapped DSO. No source label
or old app incident is promoted to a diagnosis of G34.

## Smallest next normal observations

These are proposals for the sole outer executor, not commands run by this task:

1. Save one `hilog -z 2000` result without PID/tag filters. Correlate on the host
   with boot a1d869b4, PID29761/birth2248607, parent27555 and23:22:11.437. Record
   actual covered timestamps. This may already be too late to retain the event;
   do not repeatedly run the same empty narrow query.
2. Read current listings of the already observed `/data/log/faultlog/temp` and
   `/data/log/faultlog/faultlogger`; compare names/time on the host, then `cat`
   only an actual matching filename. Existing `sc17_run.sh:64–66` demonstrates
   the ordinary fault-file/Reason/Fault-thread/#00-PC evidence route. Do not run
   that whole script. Reject permission/body errors as missing coverage; do not
   guess filenames or read a reused PID's `/proc` files.
3. Only if those records identify a concrete service/DSO gap, read its existing
   service declaration/state and exact artifact identity/build receipt. Do not
   restart services, change logging configuration or infer behavior from an
   unbound source snapshot.

If no normal archived report survives, stop with cause/TID/PC/stack unknown. A
future separately authorized ordinary launch window can capture bounded normal
logs and fault-file directory deltas promptly, with boot/PID/birth bookends.
This plan does not request another launch and does not alter code or the game.

`results.json`, `observations.json`, `source-evidence.json`, `build-binding.json`
and `next-observations.json` separate observations from conditional predictions.
`input-sha.json` pins44 original inputs using persistent sanitized aliases.
No device or VM command, compilation, runtime change or G14/T38 action was made.

Readiness token: **G34-DIAGNOSTIC-PLAN-READY**.
