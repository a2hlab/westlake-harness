# Flutter r5: use the existing default-owner callbacks

r4 incorrectly invoked dlns operations from the sealed ANL DSO. The unchanged
app-native-loader.h already documents that only the stock-host callbacks own
these operations. This revision keeps all namespace creation and every preload/
engine open behind namespace_host_ops. Namespace names follow the host's exact
westlake.anl.app.PID.ID / westlake.anl.bridge.PID.ID grammar.

Only the six existing Flutter package guards select this path. Private canonical
filenames and the three r3 libraries are unchanged. The host's validated bridge
configuration inherits default and shares only the listed direct dependencies
with the private app namespace; pthread bootstrap uses the original paths and
host ops. No host/provider/policy/ART/JAR change. Device behavior remains unverified.
One ANL build is authorized; a failure stops this attempt.

## Build and host gates

One ANL-only dockbuild attempt succeeded: 90320ecb. No direct dlns/dlopen_ns imports remain, exported symbols match r4, source gate rejects r4 as a negative. Canonical private files are the exact original three r3 SHAs; direct NEEDED ownership names and six-package scope are checked by check_domain.py. The prior six-engine physical symbol/version closure is unchanged, but those static checks did not prove live namespace resolution in r4 and do not prove it here. Package dry-run and frozen API checks pass. The build was preceded by a host check_frozen --source-root invocation; build.sh now also enforces that prerequisite on future invocations (no second native build).

This package derives from the actual resident asset-fd package 53f00423, not old v3c. It changes two ANL aliases and adds three private canonical libraries atomically. Host, child, provider, installer, runtime53 and JAR a0ed remain identical. Comparisons against the older r4 experiment must disclose the intervening runtime change; this run alone cannot attribute every app difference to ANL.

## Device outcome: stopped after one candidate

Both control t20 screenshots show their own UI. LocalSend and Immich clean reinstall both return to desktop at t20, with no engine mapping captured. The former sealed-caller permission message is absent. Immich fails private libandroid preload because libsurface.z.so cannot resolve in the configured bridge namespace; LocalSend fails at the same preload with liboh_android_runtime.so unresolved. See first-fatals.json and each fatal-extract.txt for exact raw lines. These are dependency visibility failures after namespace creation. A listed shared name and physical symbol closure do not prove a library has a live reachable owner. No fourth rebuild, wider domain, host edit, or remaining-four batch is authorized by this result.

compare-r4-r5.txt reports three changed files (ANL two aliases plus the intervening asset-fd runtime). The loader log movement is observed, but this is not a strict single-variable A/B against r4. facts.txt is retained verbatim; child_hilog=0 means no sampled surviving PID and does not mean the raw log lacks the short-lived child.

Rollback completed through the deployment tool, active_verified. Original asset-fd package, ANL a9c9187d and r17p JAR a0ed5c4f restored; HW/ZZ t20 own UI. final-identity.txt records hashes. 61b released to oc-t4 after the run, within the 30-minute window. No further r5 attempts.
