# Binder calls on real Android 16: what an in-process `IXxx` adapter has to answer

The gap map knows which system services an APK *asks for*. It could not say which AIDL methods those
requests turn into on Android 16, nor which binders the framework calls on the app's behalf without any
app code naming them. Both are exactly the surface an in-process adapter (BridgeAOSPV16's L5 `IXxx`)
must answer. This run records it.

**Reference:** LineageOS 23, **Android 16, build `BP4A.251205.006`** (the same BUILD_ID as the AOSP 16 R4
baseline BridgeAOSPV16 is pinned to), arm64, no GMS, no telephony. It is the guest image of
[Husk](https://github.com/Leviidev/Husk), booted under QEMU TCG **inside an OpenHarmony 6.1 emulator app**,
so no phone is needed and the machine can be restored to an identical state between runs. Recording uses
only the platform: `am trace-ipc start|stop` makes every process log a stack for each Java
`BinderProxy.transact`. Shell user, no root, no Frida.

| | Editor 1.98 (F-Droid) | Tusky 32.2 (corpus key, APK `3e8fcc49…`) |
|---|---|---|
| scenario | cold start, 15 s | cold start to the login screen, 45 s |
| `am start -W` TotalTime (TCG, slow) | 12.7 s | 20.4 s |
| Java binder calls by the app process | 79 | 100 |
| distinct AIDL methods | 50 | 64 |
| services | 18 | 18 |
| services called **only by the framework** | 5 | 7 |

Tusky reached `LoginActivity` (`tusky/first-screen.png`; the dialog on top is a stale ANR of the Editor
process traced before it, not Tusky).

## What it settles

- **A 44-method cold-start floor.** A minimal text editor and a Mastodon client share 44 of their AIDL
  methods: the binder surface any app reaches before its first screen on Android 16, across 16 services
  (`results.json` → `cold_start_floor`). It is the first batch an `IXxx` adapter has to answer, whatever
  the app.
- **Six services Tusky used that its gap map has no row for:** `activity_task`
  (`IActivityClientController` — every lifecycle callback goes through it), `settings-provider`
  (`Settings.Global` / `DeviceConfig` reads through `ContentProviderProxy.call`), `mount`
  (`IStorageManager.getVolumeList`), `graphicsstats`, `voiceinteraction` and `protolog_configuration`.
  None of them is a service the app's DEX requests by name. Either the framework calls them itself
  (`ActivityClient` lifecycle reports, `HardwareRenderer$ProcessInitializer`, `PerfettoProtoLogImpl`), or
  app code reaches them through another API (`Activity.startActivity` and `setTaskDescription`, a
  `Settings.Global` read, external-storage directory setup). Either way the request scan has nothing to
  list, and the adapter still has to answer.
- **Tusky's static map against this run:** 13 of its 33 `svc:`/`pm:call:` rows reached, 16 not reached on
  this path (`alarm`, `audio`, `location`, `phone`, `wifi`, three `pm:call:query*` lookups …), 4 not
  observable by this method (binderless managers, and `sensor`, whose binder is spoken from native code).
  Where a row lists `app_calls`, the matching AIDL methods are recorded per row
  (`getHistoricalProcessExitReasons`, `JobScheduler.schedule`, `createNotificationChannels` …).

## Where this sits next to `trace-observe`

`trace-observe` (ART method trace on the OnePlus 6 reference) answers *which platform methods ran*; it
already marks gap-map rows on the observed path. This record is one layer lower and narrower: *which
binder methods crossed the process boundary*. Use it for the adapter's interface list and for the
framework-implied services; keep method tracing for everything that never leaves the process.

Limits, all visible in the data: only Java binder clients are recorded (native clients such as
SensorManager, libgui and SurfaceComposer are not); counts are aggregated per distinct stack, with no
order, arguments or return values; one scenario per app; the emulated device has virtio HALs and runs
under TCG, so timings are not representative and slow callbacks can raise ANRs.

## Rule

Before writing or reviewing an `IXxx` adapter for an Android 16 target, take its method list from a
recorded run (`ipc-observe`) rather than from the AIDL file or the app's requests alone, and treat
services listed under `observed_but_not_in_map` as required even though no gap-map row names them.

## Reproduce

```sh
# on any Android reference: a phone over adb, or a raw shell socket (Husk guest bridge forwarded to 25599)
python3 scripts/lab/capture_ipc.py --transport adb:<serial> --package com.keylesspalace.tusky --settle 45 --out run/
python3 scripts/lab/capture_ipc.py --transport tcp:127.0.0.1:25599 --package com.keylesspalace.tusky --settle 45 --out run/
# join with the gap map
PYTHONPATH=harness python3 -m westlake_gap.cli ipc-observe --dump run/ipc-trace.txt \
    --package com.keylesspalace.tusky \
    --gap-map benchmark/2026-09-23-corpus2-blind/maps/com.keylesspalace.tusky/gap-map.json --out run/
PYTHONPATH=harness:tests python3 -m unittest tests/test_ipctrace.py
```

## Files

| File | |
|---|---|
| `results.json` | both runs, the 44-method floor, Tusky's gap-map join |
| `*/capture.json` | device build, app version, `am start -W` output, sha256 of the full all-process dump |
| `*/ipc-trace.app.txt` | the app process's section of the `am trace-ipc` dump |
| `*/ipc-observed.json`, `*/IPC-OBSERVED.md` | `ipc-observe` output: per service and AIDL method, app frame or framework entry |
| `tusky/first-screen.png` | guest `screencap` at the end of the Tusky run |
