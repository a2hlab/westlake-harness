# 5cd installer interaction experiment and final convergence

User explicitly authorized installer replacement on the hub, including black-screen recovery. Reuse the accepted 61b service transaction, unchanged binaries; change only serial and transaction directory. Original lock-time native package and r17q overlay are in `original.json`. This task changes only 5cd.

1. Back up and replace libbms 6f94d4f4 → 6aadb8b4 and libapk_installer eb6824b4 → 7048c7c5, including both system/platformsdk copies. Mac direct HDC for foundation restart, verify through foundation root/maps.
2. If black, reboot only 5cd and replay the original graphics package with no `--upgrade` on the new boot; restore r17q 94424d60. This introduces a reboot covariate.
3. Master batch six keys: HW, AntennaPod, Thunderbird, K9, Tusky, FileManager. Reinstall, 16M/private-off preflight, t5/t20, 20s hilog, focus checks. Compare against the actual same-board r17q/32df old-installer sweep via master compare_runs.py. A new NPE supports an interaction hypothesis; it does not prove causality if reboot also differs.
4. Expose package r8b, replace only runtime 32df → original 9e14 using the reverse replacement package, then pin r17r dd4f0eae. HW smoke and release for oc-t4. The installer remains accepted, no native rebuild.

Mac transaction package: `/Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4-5cd`.

```sh
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4-5cd/swap_services.py rollback
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4-5cd/swap_services.py restart
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4-5cd/swap_services.py verify
```

This restores the saved four service files, not already granted per-package ATM tokens. New installations must be repeated for reverse A/B. The accepted native reverse package is `/Users/zhaoyue/orca/workspaces/westlake-runtime-return-9e14-5cd`; apply with deploy_generation `--replace /system/android/lib64/liboh_android_runtime.so` only after retiring the JAR overlay. No foundation restart for this runtime operation.

Flutter queue retained separately in `flutter-deferred-precheck.json`: both r17p boards fail identically, three apps on libandroid.so and three on libGLESv2.so, before Flutter rendering. No Flutter board experiment performed in this task.
