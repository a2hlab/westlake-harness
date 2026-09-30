# Task90: r15c-informed successor to v4-r2

The previous five-family/r13 ranking could not represent the current r15c startup failures. This revision preserves that frozen scan, joins all 66 recorded APK identities (32 exact static matches, 34 outside its scan), and ranks target-PID startup exceptions separately from tolerated warnings. It is an outcome-informed prediction for the next run, not a backtest scored on its own training observations.

Run from repository root:

    python3 benchmark/2026-09-29-static-wall-prediction/update90.py --out /tmp/task90-reproduce
    cargo test --manifest-path tools/spec-checks/Cargo.toml b90_

Inputs default to the local r15c full run and oc-t4 triage. No device access occurs. The input manifest hashes originals and identifies partial log excerpts. Each excerpt retains original line numbers and target PIDs. CSV nested values are JSON; unknown values are null or explicitly labeled unknown.

- predictions.csv / predictions.json: all 66 keys, recorded APK SHA, prior scan coverage, captures, UID-matched t5 process rows, external visual adjudication, candidate wall sequence and residual uncertainties.
- walls-stub_ok.csv / walls-needs_real.csv: independent descending rankings by startup-affected keys. Full prior static callsite counts remain separate; null means no comparable static count, not zero. These are overlapping candidate sets, not additive expected lighting gains.
- walls-unknown.csv: warnings and downstream symptoms without proven causal attribution.
- network-candidates.csv / network-contract.json: per-key network evidence and required deployment/install conditions.
- prediction-delta.csv: changes from frozen v4-r2, whose source generation remains explicit.
- observed-wall-hits.csv: line-cited startup evidence and tolerated-on-accepted-UI exclusions.

Raw records yield **124/124 captured, 13 t5 survivors, four keys without t5 measurements, six externally accepted own-UI keys**. t20 is **unknown** (no snapshots). Automatic focus acceptance remains unconfirmed; outer screenshot adjudication is stored separately, not written into original records. VLC is alive at t5 despite the triage commentary calling it dead. No new screenshot or survival claim is made here.

The stub ranking is JobScheduler startup (14 keys), then ShortcutManager (one: fd-auxio). Native/runtime priorities are app-native-loader (12), CommonEvent JNI (10), guest-thread-ready (six), then the smaller groups listed in CSV. r16 reportedly includes OnlineJobScheduler/OnlineConnectivityManager/ShortcutManager; those are planned or deployed mitigations, **not confirmed absent walls in a completed r16 full run**.

Known-answer corrections:

- fd-fitness: JobSchedulerExtKt.getWmJobScheduler provider initialization NPE, not ShortcutManager (evidence/logs/fd-fitness.json, original hilog lines 39796–39799).
- fd-auxio: actual ShortcutManager NPE occurs before missing VelocityTracker JNI; repairing the first does not guarantee first screen.
- anki: its target process reports librsdroid.so missing liblog.so during provider initialization (evidence/logs/anki.json, line 32144). Black-screen causality remains a candidate, not a proven render diagnosis.
- CommonEvent failures also occur on accepted Aegis/Droidify/Noice; those tolerated observations are excluded from blocking impact counts.
- CoroutineStart/IConnectivityManager warnings are not automatically white-screen root causes. The former also appears on accepted STK. fd-binaryeye/fd-filemanager/fd-notes retain unknown current visual causes.
- A view visibility diagnostic alone does not establish transparency or screen content; retain outer black/blank adjudications rather than overriding them with view-tree dimensions.

**Networking-only recovery candidates: noice and fd-noice** (two input keys, one package). Both already have accepted own UI and target-process INTERNET/EPERM failures. The prediction is possible online-content recovery, **not two newly lit apps**. Require both child supplementary gid 3003 and installed synthesized HAP ohos.permission.INTERNET, using the corrected installer with reinstall; actual HTTP success remains unknown. Runtime replacement or an APK permission declaration alone is insufficient. GET_NETWORK_INFO is the additional mapping when ACCESS_NETWORK_STATE is requested. 5ea components were reported patched; 5cd/61b rollout and each app's installed permission/process groups require confirmation. Wikipedia is excluded from direct recovery because initialization and later 5ea stack/PNG faults remain in the evidence.

Validation: three Rust-dispatched Python checks pass; old task85 freeze verified. Prospective hit rate is unknown until a subsequent completed run with exact APK/profile identities. R2: offline evidence-backed candidate ranking; no device execution, no causal repair proof, no git commit from this sandbox.
