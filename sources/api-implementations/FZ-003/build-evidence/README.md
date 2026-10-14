# Asset fd: one helper on the reproduced 9e14 baseline

The OH build used the layoutlib fallback that throws Implement me. Defining
__ANDROID__ would merely select another branch that closes the fd and returns
null. Westlake 532633da already implements the local ParcelFileDescriptor
constructor; no Binder transaction or Java change is needed.

The frozen 59 B91 objects first relinked to exactly 9e14bf20. Only
android_util_AssetManager_aosp.o was then replaced, yielding 53f00423. All other
58 objects retain their SHA. The 22 NEEDED entries/order and import/export sets
are unchanged; strict linker and package dry-run passed. Source and patch
provenance: ../2026-09-30-asset-fd-plan/. Baseline persistent inputs are recorded
in ../2026-09-29-native-abi-port/archive.json and the B91 report. build.sh and
runtime-recipe.sh keep compilation in an isolated asset-fd output directory;
the original source and B91 cache are untouched.

The single-file package is /Users/zhaoyue/orca/workspaces/westlake-runtime-asset-fd-53f00423.
Deployment uses scripts/lab/deploy_generation.sh SERIAL PACKAGE --replace
/system/android/lib64/liboh_android_runtime.so --lane cx-t0; append --rollback
for the same replacement. Expose package JAR only during deployment checks, then
restore the captured a0ed5c4f overlay. No installer, host, ART or ANL change.

61b validation: clean NewPipe/uhabits on 9e14 before replacement; clean all seven
requested apps on the candidate with the same JAR. ZigZag is manually uninstalled
and reinstalled from the unchanged control APK, then its five original
ledger-owned native bind mounts are restored before master batch launch-only.
The clean-install receipt is explicit; do not interpret launch-only as retained
app data for that control. Other apps use master batch --reinstall.

## Device result

compare-runs.txt reports exactly one differing file: runtime 9e14bf20 -> 53f00423. Same boot, JAR, installer and clean reinstall. NewPipe no longer throws Implement me and retains its red navigation UI at t20 (content empty). uhabits reaches IntroActivity, then libhwui aborts; its t20 remains desktop. The sampled child_hilog=0 does not mean no child launched: raw hilog includes the short-lived PID 1563. Both target logs no longer contain the former exception. HW, ZigZag, Aegis, Droid-ify and mpv show their own UI. Screenshots and per-run facts paths are indexed in results.json. No broad functional or fd-leak claim. This fix is NOT freeze-eligible yet: only one affected app has a successful t20, and controls do not prove this API was exercised.

61b released at 09:57:37 with candidate 53f00423 and original r17p a0ed5c4f resident; final-identity.txt records readback. 69 known-answer checks passed (2 skipped). Outer screenshot signoff pending. Board 90 has no assigned agent-spec; no lifecycle pass is claimed.
