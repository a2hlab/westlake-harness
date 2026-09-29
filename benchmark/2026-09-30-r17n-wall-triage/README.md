# r17n → r17r: six runtime-JAR increments, six apps lit (2026-09-30)

**One line:** starting from the v3c+r17j 5ea sweep, six `oh-adapter-runtime.jar` increments
(r17n…r17r, cumulative, base b5 `250958dc`) each cleared one wall and lit one more app, verified by
on-board t20 screenshots (FLAW-007). The unified candidate is **r17r `dd4f0eae`**.

## What the earlier draft of this file got wrong (superseded — the rule this sets)

The first version of this README concluded that the **conscrypt "Sun provider not found"** wall and the
**EGL reverse-push** wall were *not* runtime-JAR-fixable (route them to cx-t0 boot/native). **Both were
then fixed from the runtime JAR** (r17o and r17p). The lesson, now the rule:

> A wall that lives in a boot/framework method is still JAR-fixable when the data that method reads is
> reflectively reachable and writable from the runtime JAR. Don't stop at "the method is in the BCP" —
> ask what it *reads*. `getSunProvider` reads a `static final String[]` (writable elements); the EGL
> delegate reverse-pushes on the IWindow we hand it (interceptable by wrapping that arg). Both were
> reachable.

## The six increments (each: wall → fix → verified lit)

| rev | sha256 (8) | wall | fix | lit (t20, self-read) |
|---|---|---|---|---|
| r17n | (folded) | `getSystemService(JobScheduler.class)` → null → NPE | register `SYSTEM_SERVICE_NAMES[JobScheduler.class]="jobscheduler"` (route-A only wrote the by-name fetcher) | **fossify calendar** (month grid) |
| r17o | (folded) | conscrypt `getSunProvider` "Sun provider not found" (9 apps, biggest regression) | rewrite `sun.security.jca.Providers.jarVerificationProviders[0]` conscrypt→BC (final locks the ref, elements are writable; B7BindFixes, before any JAR verification) | **Droid-ify** (main UI); +newpipe/catima/antennapod/amaze clear the wall |
| r17p | (folded) | EGL: delegate reverse-pushes redundant `IWindow.resized` → HWUI rebuilds surface → BAD_ALLOC / firstCreate white | wrap the relayout IWindow (Proxy) and drop the delegate's `resized()`; keep the r17j 0x0 recovery on the real window | **fd-AppManager** (verify splash) |
| r17q | `94424d60` | `PowerManager.isIgnoringBatteryOptimizations` → `getSystemService(PowerExemptionManager.class)` null → NPE | `power_exemption` fetcher (stub PEM, isAllowListed→false) + Class→name | **Etar** (week calendar) |
| r17r | `dd4f0eae` | markor `addToDisplay` FLAG_KEEP_SCREEN_ON(0x80) → ADD_INVALID_TYPE(-10) → InvalidDisplayException | mask retry now strips power/lock flags with *device-standard literals* (our `SUPPORTED_LAYOUT_FLAGS` runtime value `0x81e90580` already carried 0x80, so the old mask was a no-op) | **Markor** (`¯\_(ツ)_/¯` doc browser) |

Cumulative lit / restored across the session: **calendar, Droid-ify, AppManager, Etar, Markor**, plus
the conscrypt wall reopened for **9 apps**. Regression controls (auxio, droidify, helloworld,
antennapod, amaze, etar) stayed lit at each step; ZigZag/termux/tusky white or cppcrash proven
gen-specific (see below), not JAR regressions.

## Decisive on-board debugging (r17r, the non-obvious one)

markor's retry silently never fired. Two debug JARs (`a60ad048`, `d7cf8576`) printed the runtime values:
`flags=0x81810180 SUPPORTED=0x81e90580 masked=0x81810180` → `masked==original` → early return. The
compile `android.jar` on this generation bakes quirky flag constant values, so `& SUPPORTED_LAYOUT_FLAGS`
left 0x80 in. Fix uses literal device bits. **Rule:** never trust a compile-time flag constant's value
on this generation — mask with device-standard literals, or read the delegate's own field.

## Boundary — what is NOT the runtime JAR (routed to cx-t0)

- **Wikipedia B11 onboarding double-create** and **AppManager/k9/tusky BLAST `TransactionHangCallback`**
  white: v3c-native surface lifecycle / BLAST hang (cc-wiki 5ea diff). r17p's wrapper drops the
  reverse-push on both boards (WSP-dropped confirmed) but the extra firstCreate SURFACE_CHANGED is
  native. B11 welcome page NOT achieved on either board.
- **ZigZag cppcrash** is gen-specific: on 61b and 5cd it cppcrashes on **r17m baseline (no wrapper) 3/3
  identically to r17q 3/3** (definitive `--launch-only` experiment) — not the wrapper. cc-wiki saw it
  alive on 5ea. Same for tusky white (61b gen BLAST).

## DI-null getClass (breezyweather/catima/feeder) — NOT a common fix (open)

All three NPE on `Object.getClass()` on a null app-internal object (Kotlin `checkNotNull` of
`viewModel`/`binding`/`repository`), NOT a missing system service. The shared `No service published
for: game` is framework-internal (apps don't reference GameManager). Roots differ per app:
breezyweather **ObjectBox** (native DB), feeder **`NetworkSpecifier.getNetworkSpecifier()`
NoSuchMethodError** (route-A framework gap), catima **ACRA StartupProcessor + SQLCipher**. The shared
`kotlinx.coroutines.CoroutineStart` CNF is our own `AppSchedulerBridge.primeCoroutineStart` warm-up
(non-fatal, pre-bind), a red herring. Needs per-app root-cause tracing.

## Files

- `results.json` — SHAs, per-increment wall/fix, verified-lit list.
- `evidence/conscrypt-getSunProvider-amaze.txt`, `evidence/egl-size-gate-source-line846.txt` — raw stacks/source.
- `61b-r17{o,p,r}-batch/`, `5cd-r17q-batch/`, `5cd-zz-experiment/` — run dirs with t20 screenshots + facts.txt.
