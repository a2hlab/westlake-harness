# T37 reentry launch entry: the real imehost0 host entry, and why source has no per-tap tap-signal

Read-only static source audit for a reliable desktop-icon → host launch signal the reentry state machine
could consume, distinguishing a genuine user icon tap from recovery / notification / autostart. No REA,
device, source edit, deploy or orchestration. This is a static source audit, not an on-device root cause.

> Correction history: earlier passes wrote "host not located / host layer unaudited", then over-claimed
> `onNewWant` as a reliable per-tap human signal, then wrote "deployed host source equivalence unproven
> (KNOWLEDGE-DIGEST #91 :973)". All withdrawn. DIGEST #91 predates the T32/T33 closure; the exact
> source→ABC→deployed-member binding is proven below. This file is the single final conclusion.

## The reentry guardian signal (unchanged)

The reentry guardian shell scripts observe only a 1-second poll of a `hidumper -s WindowManagerService`
focus/window **snapshot** (29 call sites); a spawn fires on a verified SceneBoard-desktop → imehost0-host
**focus transition** (`benchmark/2026-10-19-toutiao-icon-reentry/src/reentry-common.sh:31-36,43-98`). A
desktop focus between two samples is missed (T37 gap; `OUTER-ADAPTER-READY.json:66`). Host `WinId` drifts
only on host **restart** (`real-start-parent.sh:3-4`), not per tap; the watchdog `sequence` is the guardian's
own spawn counter (`watchdog.sh:369-371`). None of these is a per-tap launch event.

## The `activity` adapter layer is the Android child bridge, not the host

`bms/src/adapter/framework/activity` translates OH AMS `ScheduleAbilityTransaction` (`isNewWant` + `wantJson`)
into the bridged **Android child's** `Activity.onResume`/`onCreate`
(`java/AbilitySchedulerBridge.java:81-120`, `jni/ability_scheduler_adapter.cpp:403-502`). That `isNewWant`
and Want belong to the launched child, consumed inside the child runtime after spawn — not a pre-spawn host
tap signal, and not read by the reentry guardian.

## The real host entry (source fact)

The desktop host is **`org.westlake.imehost` `EntryAbility`** (JS stage-mode `UIAbility`). `module.json` carries
the `action.system.home` / `entity.system.home` skill (desktop icon) and sets no `launchType` → OH default
**singleton** (one persistent instance). Source, read in this repo:

| file | sha256 | git blob | role |
|---|---|---|---|
| `benchmark/2026-10-20-toutiao-launcher-page/sources/baseline/EntryAbility.js` | `9dc302d9…` | `3ed2f34b…` | **the deployed host source** (proven below) |
| `sources/api-implementations/source-build-host/westlake-java/apps/imehost/EntryAbility.js` | `922a13a5…` | `90b430ed…` | generic template, different window background — **NOT the deployed source, not interchangeable** |

The two are **not interchangeable**: the deployed host is `9dc302d9`; `922a13a5` is a generic variant with a
different background and must not be substituted for it.

Its overrides are `onCreate`, `onWindowStageCreate` (registers a `windowStageEvent` handler, loads
`pages/Index`, black background), `onForeground`, `onBackground`, `onWindowStageDestroy`, `onDestroy`. **Each
only `record()`s a hilog `WL_IME_HOST` line and TRUNC-overwrites `files/window-state.json`** with
`{event,time,details}` (the event type). **The host reads no `Want` and implements no `onNewWant`.** The outer
loop accepts this source fact.

## Why source cannot distinguish a tap from a non-tap

- `onCreate()` fires once on cold create; not per tap, no `want` parameter.
- `onForeground()` in this source takes no argument and records `{}`; it carries **no launch reason**. Per OH
  platform semantics it is invoked on **every** transition to foreground — cold create, user re-tap, recovery,
  auto-startup — and the source neither does nor can label which. So `onForeground` is **not** a human-tap
  discriminator.
- `windowStageEvent` emits FOREGROUND/BACKGROUND/ACTIVE/INACTIVE stage events (focus-like); same ambiguity.

So in the located host **source**, there is **no per-tap, cause-labelled launch signal**, and a genuine user
icon tap is **not** distinguishable from a recovery / notification / autostart foregrounding.

## `onNewWant` is a candidate, not a ready tap-proof

`onNewWant(want, launchParam)` is the OH callback for a **new start request** delivered to an already-created
ability (e.g. a singleton re-entry). It is a new-launch-request callback — **not, by itself, proof of a
physical user tap**. It is **not implemented** in the located source. To label a launch cause it would read
`AbilityConstant.LaunchParam.launchReason` (e.g. `APP_RECOVERY`, `AUTO_STARTUP`) and, on newer APIs,
`launchReasonMessage` (API 18+) / a `DESKTOP_SHORTCUT`-style `ReasonMessage` (API 20+). A desktop **shortcut**
reason is **not** equivalent to every desktop-icon launch, and none of this is read in the current source.
Treating `want.parameters` as a ready, reliable human-tap marker is **not** justified without real captured
`Want` + `LaunchParam` values on this board/API.

## The deployed EntryAbility source is proven (T32/T33 closure)

DIGEST #91 (`:973`) predates this closure and is superseded here. The exact source→ABC→deployed-member
binding:

- The deployed/installed host HAP is `df385638…` (53,303 B), identical to the historical 5cd installed+signed
  HAP (`closure.json` `history_matches_intake=true`).
- Its member `ets/entryability/EntryAbility.abc` = `bb1eccd3…` (`inputs.lock.json`).
- The exact Linux compiler `d20db2d4…` compiled `sources/baseline/EntryAbility.js` (`9dc302d9…`) and reproduced
  `baseline/EntryAbility.abc` = `bb1eccd3…` **byte-for-byte** (`compile-linux-01.json`; `closure.json`
  `baseline_abc_exact=true`).
- The signed candidate `b18978b8…` changes only `ets/pages/Index.abc`; **EntryAbility is not changed**
  (`production-01.json` before=after=`bb1eccd3…`).
- `benchmark/2026-10-20-t32-host-page-accepted` accepted this same-signature HAP on 5cd: one desktop icon tap →
  Toutiao feed.

So the deployed host EntryAbility source is **proven to be `9dc302d9`**, which implements **no `onNewWant`** and
reads **no `Want`**. Therefore the deployed host has no `onNewWant` / no Want read — this is now **proven at the
source→ABC level, not 待实测**.

## Conclusion (actionable)

- **Entry (proven):** `org.westlake.imehost` `EntryAbility.js` `9dc302d9` → `EntryAbility.abc` `bb1eccd3` in HAP
  `df385638` (T32-accepted). Desktop-icon singleton host.
- **Want-readable fields:** none — the deployed host reads no `Want` and no `LaunchParam`.
- **Per-tap / cause signal:** none; `onForeground`/stage events fire on taps and non-taps alike and carry no
  reason.
- **`onNewWant` is a candidate, not a tap-proof:** it is a new-start-request callback, absent in the deployed
  source. A reliable per-launch-cause signal would require implementing `onNewWant` and reading
  `AbilityConstant.LaunchParam.launchReason` / `launchReasonMessage` (API 18+/20+; a `DESKTOP_SHORTCUT` reason
  is not equivalent to every desktop-icon launch), verified with **real captured `Want`/`launchParam`** — a
  code + measurement task, out of scope. `want.parameters` is not a ready reliable human marker without that
  evidence.
- **Fresh device check (narrow):** only the **current device runtime state** (live WID/parent, that this exact
  HAP is the one installed on the target board right now) needs a fresh read — not the EntryAbility source
  identity or `onNewWant` presence, which are proven. `closure.json` marks `visual_activation NOT_EXECUTED`
  for this offline package; T32 is the accepted on-device run.
- The generic `922a13a5` template is **not** the deployed source and must not be used as a substitute.

Any future wiring must preserve the identity, window-ownership and single-instance (`HOST_CONSUMED`) gates and
keep "no event → no autostart". This audit proposes no code change and made no REA, device, edit, deploy or
orchestration.
