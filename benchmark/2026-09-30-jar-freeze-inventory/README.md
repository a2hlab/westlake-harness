# JAR public-API freeze inventory — DRAFT for outer-loop review (2026-09-30)

> **2026-09-30 13:5x (outer-loop ACK 93): `registrable-entries.json` is the outer-loop-ready output.**
> `FZ-002` (conscrypt, 3 apps) and `FZ-003` (alarm, 2 apps) are in the EXACT frozen.json schema and
> **pass `check_frozen.validate()` (no problems) + `check_sources` against feat/bms-walls (0 blob
> violations)** — paste into `knowledge/frozen/frozen.json` entries[] as-is (renumber / set frozen_at).
> binaryeye stays HOLD (1 distinct app; needs a 2nd). `frozen-entries-draft.json` is the fuller working
> draft with per-entry `split_reverify_j1final` evidence.


Per AGENTS.md 做事方式 3 (tiered freeze, user 2026-09-30): a public-API fix verified on **≥2 different
apps by t20 screenshots** is frozen; frozen source files never change (only the user unfreezes; the outer
loop may register a new version only for defect|platform|extension with a single-variable compare_runs +
every earlier-evidence app re-lit + a non-regressing full sweep).

This is the **inventory + split plan**, not the freeze itself. The outer loop reviews, then splits +
re-verifies + registers each entry into `knowledge/frozen/frozen.json`. `verified_apps` (≥2, with t20 +
facts) are gathered separately (see `frozen-entries-draft.json`).

## The hard part: most JAR fixes live in SHARED files → must be split first

The rule: "冻结前先把实现拆成只含这一项的独立文件再验". Today several fixes share one file, so freezing one
would lock the others' file. Split plan (each `→` is a new single-fix file that `B7BindFixes.apply()` /
the installer still calls):

| shared file | fixes inside it | split into |
|---|---|---|
| `B7BindFixes.java` | orchestrator `apply()` + fixJarVerificationProvider (r17o conscrypt) + loadWestlakeNativeLibs/createNativeNamespace (r17c) + stubAudioProductStrategies (r17t) + applyImpellerFallback (r17/#70) + installTolerantUncaughtHandler (r15) + fixNativeLibraryDir + extendAppNativeLibrarySearchPath (r17s dlopen probe, no-op) | keep `B7BindFixes` as the orchestrator (not frozen); extract each fix: `JarVerificationProviderFix`, `WestlakeNativeLibLoader`, `AudioProductStrategyStub`, `ImpellerFallback`, `TolerantUncaughtHandler`. The dlopen probe is a no-op → do not freeze. |
| `SystemServiceFetcherStubs.java` | power_exemption (r17q) + restrictions (r17s) + alarm/vibrator (r17e) | `PowerExemptionFetcher`, `RestrictionsFetcher`, `AlarmVibratorFetcher` |
| `WindowSessionProxy.java` | reverse-push/DropResizedHandler (r17p EGL) + retryAddOnInvalidType/addToDisplay flag (r17r) | `WindowReversePush`, `AddToDisplayFlagFilter` |
| `SelfComponentFallback.java` | self getProviderInfo/resolveContentProvider (r17) + getServiceInfo (r17u binaryeye) | `SelfProviderFallback`, `SelfServiceFallback` |
| `OnlineConnectivityManager.java` (cc-wiki) | online connectivity + `getSystemService(JobScheduler.class)` name map (r17n) | coordinate with cc-wiki; extract the NAMES-map fix if frozen separately |

Fixes already in their own file (freeze in place, no split): `SoftwareAndroidKeyStore` (r17l),
`SelfUidPackages` (r17), `WlMediaSession` (r17d), the Westlake TLS chain (`WestlakeTlsInstall` +
`WestlakeSSLContextSpi/SSLSocket/SSLSocketFactory/SSLSession` + `OhTrustBridge` …, r17s — a cohesive
multi-file unit; freeze the set).

## Candidate fixes and freeze-readiness

| fix (rev) | file(s) | ≥2-app evidence status |
|---|---|---|
| conscrypt→BC jarVerificationProviders (r17o) | B7BindFixes → JarVerificationProviderFix | strong: the 9-app "Sun provider not found" wall (droidify/newpipe/catima/antennapod/amaze …) — **ready** once split |
| getSystemService(JobScheduler.class) name map (r17n) | OnlineConnectivityManager | fossify calendar confirmed; **need a 2nd app** |
| PowerExemptionManager stub (r17q) | SystemServiceFetcherStubs → PowerExemptionFetcher | etar confirmed; **need a 2nd app** (any isIgnoringBatteryOptimizations caller) |
| addToDisplay flag filter (r17r) | WindowSessionProxy → AddToDisplayFlagFilter | markor confirmed; **need a 2nd app** |
| ALARM_SERVICE + vibrator fetcher (r17e) | SystemServiceFetcherStubs → AlarmVibratorFetcher | k9/fd-android (alarm) + fossify-reader (vibrator) — likely **ready** |
| MediaSessionManager stub (r17d) | WlMediaSession | noice / musicplayer — evidence TBD |
| SelfUidPackages getPackagesForUid (r17) | SelfUidPackages | amaze confirmed; **need a 2nd app** |
| SoftwareAndroidKeyStore (r17l) | SoftwareAndroidKeyStore | fd-tasks + a 2nd crypto app — evidence TBD |
| self-provider getProviderInfo (r17) | SelfComponentFallback → SelfProviderFallback | androidx.startup/FileProvider apps — evidence TBD |
| binaryeye self getServiceInfo (r17u) | SelfComponentFallback → SelfServiceFallback | **built, not yet verified** (cc-wiki 5ea) — not freeze-ready |
| audio AudioProductStrategy stub (r17t) | B7BindFixes → AudioProductStrategyStub | noice's audio wall is 32df-only; **cc-wiki 5ea t20 pending** — not yet ready |
| real TLS SSLContext (r17s) | WestlakeTlsInstall chain | wiring accepted (2 boards) but **no app LIT by it** (real handshake blocked) — not freeze-ready as a *lit* fix |

## What I will do next (pending outer-loop go-ahead)
1. Take the **ready** fixes (conscrypt, alarm/vibrator) first: split into single-fix files, rebuild, re-run
   the ≥2 evidence apps at t20 to confirm the split didn't regress, then hand the frozen.json entry.
2. For fixes with only 1 confirmed app, find the 2nd from the sweeps before splitting.
3. Not-yet-verified (binaryeye r17u, audio r17t) wait for cc-wiki's 5ea t20.
4. `check_frozen.py` guard added to `build.py` (tolerant until `knowledge/frozen/` + `scripts/lab/check_frozen.py`
   are merged into the `feat/bms-walls` build worktree — flag for the outer loop).

## Files
- `frozen-entries-draft.json` — draft `frozen.json` entries (id/api/sources[repo_path+blob]/verified_apps),
  filled as evidence + splits land.
