# J10c — diagnose the real appcompat-actionbar wall (app's androidx windowActionBar)

**Lane:** cc-t3 · **Date:** 2026-10-01 · baseline **J10 `ea24291a`** → **J10c `c9d50c43`** (deterministic).
Source: feat/bms-walls `a354e3eb1`. Staged: `westlake-generation-j10c-staging/`.

## What J10b established + the correction
J10b proved the NoTitle **mechanism** works (`[J10b-NOTITLE] installed`/`applied` fire via the Application
pre-creation + onActivityPreCreated dispatch). But both knot and dice still died on the action-bar ISE,
and the diagnostic showed the **platform** `android:windowActionBar=false windowNoTitle=true` are already
resolved. So the J9 hypothesis was wrong. Outer-loop correction: the single-copy FAIL was the *counting
method* (bridge/runtime are 2 copies each on U8/J10/N10b too — `probe.expect_copies {bridge:2,runtime:2}`
now), **not** a J10b side-effect — so ③' (Application pre-creation) stays.

## The real wall (from knot's own AppCompatDelegateImpl.smali)
`createSubDecor` reads the **app's OWN androidx** `AppCompatTheme_windowActionBar`/`windowNoTitle` (NOT the
platform attrs): `if windowNoTitle → FEATURE_NO_TITLE; else if windowActionBar → FEATURE_SUPPORT_ACTION_BAR
→ initWindowDecorActionBar() → new WindowDecorActionBar → setSupportActionBar throws the ISE`. knot's
`windowActionBar` attr is `0x7f030350` (Theme.Knot.NoActionBar sets it false). See
`smali-evidence/knot-AppCompatDelegateImpl.createSubDecor.smali`.

## J10c change (diagnostic only)
The `[J10b-NOTITLE] applied` line now also logs the **app's** resolved attrs (via `getIdentifier` for the
package): `app windowActionBar=<bool>@0x<id> windowNoTitle=<bool>@0x<id>`.
- **true** → route-A did not inherit `windowActionBar=false` from `Theme.AppCompat.*.NoActionBar` → our
  theme/resource-resolution problem (the fix is to make the app attr resolve false, not the platform one).
- **false** but still thrown → the decor ActionBar came from elsewhere → investigate `setSupportActionBar`.

## Offline gate + window
`test_j10c.py` 12/12 (self-contained smali-evidence). Window plan `j10c-plan.json` carries the required
`offline_precheck` and `probe.expect_copies {bridge:2,runtime:2}`. Needs the J10c runtime_fp (differs from
J10b's `b188c87b65b2` since the jar changed) + outer-loop board scheduling.
