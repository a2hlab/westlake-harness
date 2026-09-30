# Frozen public-API fixes

Rule (AGENTS.md 做事方式 3, set by the user 2026-09-30, tiered the same day): once a fix for a
public-API wall found by the scanners gets **at least two different apps past the wall** — at least
one lit at t20 by screenshot, the others shown by log to lose that API's failure with the first fatal
moved elsewhere (this verifies the API, not the app) — it is frozen (user, 2026-09-30). A frozen file never changes silently.

- The outer loop may register a new version for three reasons only: **defect** (a single-variable
  `compare_runs.py` run shows the frozen item itself fails), **platform** (an OH/ART/ABI change forces a
  rebuild), **extension** (new behaviour added to the same artifact, old behaviour kept). The new version
  must bring every app of the previous version's evidence back to the same level (lit stays lit,
  past-the-wall stays past) and a unified full sweep must not
  regress. Register first (`version`, `change`, previous version in `history`), deploy second, and report
  it to the user in the morning summary.
- Removing or weakening a frozen behaviour (status `removed`) needs the user.

The machine-readable registry is `frozen.json`; this page is the readable view. Keep both in step.

## How it is enforced

- `python3 scripts/lab/check_frozen.py --package <generation dir>` before `deploy_generation.sh`,
  `--source-root <worktree>` before building a JAR or native library, `--fingerprint <run>/runtime-fingerprint.txt`
  to audit a board. Exit 1 on any change to a frozen file; exit 2 if the registry itself breaks the
  rules above (a version change without its reason/evidence, a removal not approved by the user).
- Every `bms_batch.py` run writes a `FROZEN checked=N violations=M` line under `RUNTIME fingerprint` in
  `facts.txt`; violations are listed below it.

## What gets frozen, and at what granularity

- A single-purpose artifact (the installer pair, a standalone shim library): freeze the artifact SHA.
- A fix inside a multi-purpose artifact (the runtime JAR, `liboh_android_runtime.so`): freeze the
  source files that implement it (git blob id), not the whole artifact, so other fixes can still land.
  If the fix sits inside a shared file, move it into its own file first, verify again, then freeze.
- New fixes go into new files. Nothing is added to a frozen file.

## Entries

| id | API | frozen | evidence (≥2 apps, t20) |
|---|---|---|---|
| FZ-001 | START_ABILITIES_FROM_BACKGROUND for BMS-installed bundles (installer grant + own launcher) | libbms.z.so `6aadb8b4…`, libapk_installer.so `7048c7c5…` (source: feat/bms-route-deploy b5a67c62, `benchmark/2026-09-30-installer-background-launcher/`) | Tusky, K-9, Thunderbird, File Manager go from white to their own pages with only the installer changed, on 61b and again on 5cd; same trace goes from WMS denial to `canStartAbilityFromBackground:1` |
| FZ-002 | Android child ActivityThread on an explicit 8 MiB pthread (big-stack runtime provider) | libwestlake_android_runtime_provider.so `0509fe23…` (Android alias + route-a 74d1 alias; source westlake-harness-bms-deploy `benchmark/2026-09-30-child-stack-default/`) | Tusky, AntennaPod, Markor, K-9, Auxio show their own UI at t20 in the 5cd unified sweep, each hilog has `[CM-BIGSTACK] ActivityThread on dedicated pthread stack=8390896`; HW/ZZ controls on 61b |
| FZ-003 | `AssetManager.nativeOpenAssetFd` returns a real ParcelFileDescriptor (was 'Implement me') | source blob `e47ede07` of `benchmark/2026-09-30-asset-fd-runtime/src/android_util_AssetManager_aosp.cpp` (feat/bms-route-deploy 8560fd68; copied from Westlake 532633da) | NewPipe lit at t20 on 61b (single variable, runtime only); uhabits passed the wall by log ('Implement me' gone, first fatal moved to hwui no-surface) |
| FZ-004 | `sun.security.jca.Providers.jarVerificationProviders[0]` rewritten conscrypt → BouncyCastle so JAR signature verification stops throwing "Sun provider not found" (JarVerificationProviderFix, called from B7BindFixes at bind) | source blob `c7b15f75` of `bms/src/adapter/framework/activity/java/JarVerificationProviderFix.java` (feat/bms-walls cdb82fe5, split out; unchanged through J1-final/J2/J3) | Droid-ify (61b), Amaze and AntennaPod (5ea) own UI at t20 in the J3 sweep; each hilog shows the helper rewrite and no Sun-provider failure (audit: westlake-harness-bms benchmark/2026-09-30-freeze-audit-u4, 82b3d42b) |

## Candidates awaiting an evidence check

- AlarmVibratorFetcher (K-9, Thunderbird lit): held — one file replaces both the alarm and the vibrator_manager service; split the alarm-only part into its own file, re-verify, then freeze (cx-bms audit 82b3d42b).

Listed so they are not forgotten; each needs the ≥2-app t20 evidence and the file-level split before
it is frozen.

- JAR: `getSystemService(Class)` name mapping
  (r17n), SoftwareAndroidKeyStore (r17l), SelfUidPackages, real TLS SSLContext registration (r17s),
  PowerExemptionManager stub (r17q), addToDisplay flag filter (r17r), receiver guard (r17a).
- Native: appspawn-x AID_INET group (d977bd15),
  VelocityTracker registration, bionic libc/GLESv2/stdc++/OpenSLES shims, TLS boundary (39c2cfe9),
  JNI gap-fill (d1a1961d).
