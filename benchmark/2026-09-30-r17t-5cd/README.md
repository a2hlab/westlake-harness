# r17t ec583a26 single-variable audit on 5cd — variables: 1, no regression (2026-09-30)

**One line:** r17t (= r17s `3b523289` + the AudioProductStrategy stub) on 5cd against the unified r17r
baseline is a **clean single-variable increment** (`compare_runs: variables: 1`, the JAR only) with **no
regression** (9/9 must-not-regress lit). The audio stub is active but **generation-specific**: on 5cd's
9e14 runtime noice/opencamera die at the native **EGL** wall (present in the r17r baseline too), not the
audio wall — the stub's lit payoff is on the 32df generation (5ea, cc-wiki).

## compare_runs (the outer loop's target)

```
$ compare_runs.py .../unified-r17r-5cd .../r17t-5cd
variables: 1
  /system/android/framework/oh-adapter-runtime.jar dd4f0eae -> ec583a26
verdict: single-variable comparison; a difference may be attributed to it
```
Same board 5cd, no reboot, only the JAR differs. (`runtime-fingerprint.txt` for my run was reproduced
on-board by `sha256sum` over the baseline's 117 paths while r17t was mounted — bms_batch does not emit one.)

## No regression

The 9 must-not-regress apps (aegis, antennapod, fd-android, fd-k9, fd-tusky, markor, fd-etar,
fd-com-amaze-filemanager, fd-auxio) all have **fatal_lines=0** (no `J_invokeStaticMain_main_threw` / FATAL);
tusky/markor/k9/antennapod screenshot-verified in prior sessions. No regression from the audio+TLS+dlopen JAR.

## The audio stub — active, but not the 5cd blocker

`[B8-AUDIO] AudioProductStrategy.sAudioProductStrategies pre-seeded empty` fires every bind. But on 5cd
(9e14) noice/fd-noice/opencamera reach `eglCreateWindowSurface / libhwui / abort` (EGL BAD_ALLOC, native) —
**the r17r baseline does the same, with no `[B8-AUDIO]` and no audio crash**. So on 9e14 the AudioProductStrategy
exit is not their wall; the stub is a correct no-op here. Its lit payoff is on the **32df** generation (5ea),
where Noice dies at the audio wall — cc-wiki verifies there.

> **grep trap (recorded):** searching hilog for `native_list_audio_product_strategies` matches the
> `[B8-AUDIO]` **log string** ("… bypasses native_list_audio_product_strategies"), not an actual native
> call. Confirm the stub worked by the *absence* of an AudioProductStrategy crash chain, not the presence
> of the method name.

## Targets not lit (all native/boot, not regressions)

| key | wall | owner |
|---|---|---|
| noice / fd-noice | EGL BAD_ALLOC (past the audio wall) | cx-t0 |
| opencamera | EGL + `UnsatisfiedLinkError: system library is absent from the adapter manifest` | cx-t0 |
| vlc | `AudioSystem.native_get` (different native, stub doesn't cover) + ConstraintLayout theme-attr | cx-t0 / boot |
| fd-gallery | `NoSuchFieldError MediaStore$Images$Media.EXTERNAL_CONTENT_URI` — **t20 = desktop** (FLAW-007; facts alive t20=yes is a background-installer false-positive); r17r baseline crashes identically → not a regression | oc-t4 boot |
| fd-meet | RestrictionsManager built, null-Collection behind | (app-internal) |

## Files
- `results.json` — the compare_runs output, per-app verdicts, the generation-specific audio finding.
- `runs/r17t-5cd/.../` — 15-key `--reinstall` batch + `runtime-fingerprint.txt` (reproduced). `deploy-receipt/`.
