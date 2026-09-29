# cc-wiki: one-file AID_INET experiment

Ready package (Mac and VM share this path):

```
/Users/zhaoyue/orca/workspaces/westlake-generation-b80-inet-d977bd15
```

Only `payload/runtime/appspawn-x` differs from v3a/r8b. Deployment target:
`/system/bin/appspawn-x`.

| Artifact | SHA256 |
| --- | --- |
| Before / rollback | `b87fdb77b1b20e979e1c59c24bf8df28467e080413892844510abe9e22b72839` |
| Candidate | `d977bd15da1ad193990a7aeb841c93940c28462e66dce1ec5b6bd7b31d3a02e8` |

Use the updated deployer in **westlake-harness-bms-deploy**, not the package's older copied tool. It now admits exactly `/system/bin/appspawn-x` in single-file mode and stages it mode 0755. Native library mode remains 0644. Arbitrary executable targets remain rejected. All existing package/SHA/mount/single-ART checks remain enabled.

```
DEPLOY=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh
PKG=/Users/zhaoyue/orca/workspaces/westlake-generation-b80-inet-d977bd15
SERIAL=5ea34a4500000000000000001123012c
"$DEPLOY" "$SERIAL" "$PKG" --lane cc-wiki --replace /system/bin/appspawn-x --dry-run
"$DEPLOY" "$SERIAL" "$PKG" --lane cc-wiki --replace /system/bin/appspawn-x
```

**Current independent Java overlay matters:** the saved generation state expects r8b `d5000c4e`, while cc-wiki's v4 receipt records effective JAR `2fbfd8bc`. Before the deploy command, use cc-wiki's own receipt to roll back its latest JAR overlay to r8b and verify both shell and parent-root SHA. The deployer intentionally refuses an unrecorded live JAR mismatch. After host replacement and its HelloWorld SHA/maps smoke, reapply the exact current Wikipedia JAR through cc-wiki's normal JAR deployment script, retaining the new receipt. If cc-wiki has advanced past v4, use that latest receipt/JAR instead. Do not edit the saved generation state or skip its hash checks.

No full generation reactivation, installer update, framework change or device reboot is needed. The deployer cold-stops its test apps, refuses unrelated live Android children, restarts only appspawn-x, fixes its socket ownership, and verifies the parent executable and HelloWorld child maps/SHA. 5ea remains exclusively cc-wiki's; cx-t0 made no device writes.

## Observe

Run the **master** batch tool with its 16M/private-off/time preflight and Wikipedia `--launch-only --hilog 20 --shots 5,20 --focus-check`. Capture the child `/proc/PID/status` early because the known tagsoup error may terminate it before t5.

Expected request log:

```
WLNET: uid=20010099 add_gid=3003 groups=... internet_set=... allow=...
```

The actual child supplementary groups must contain both the retained BMS groups and `3003`; the parent groups need not change. Compare app DNS errors before/after. A missing EPERM message alone is insufficient if the app never attempts DNS. Retain positive resolver/network evidence or explicitly mark that outcome unknown. Paste `facts.txt` unchanged; screenshots still need outer review.

This is the explicitly authorized **unconditional BMS supplemental-group experiment**. It does not alter `TLV_INTERNET_INFO`, OH `DisallowInternet`, AccessToken, UID, primary GID, seccomp or SELinux policy. Thus `internet_set=1 allow=0` can still block networking even when 3003 is present. Do not infer that adding 3004/net_raw or 1015/storage will fix that. Neither extra group is added.

## Roll back host

First undo only cc-wiki's current Java overlay to r8b using its receipt. Then:

```
"$DEPLOY" "$SERIAL" "$PKG" --lane cc-wiki --replace /system/bin/appspawn-x --rollback
```

The saved previous package is
`/Users/zhaoyue/orca/workspaces/westlake-generation-v3a-74d1d6d4-r8b`.
The deployer removes only its top host bind mount, restarts the original host, verifies SHA **b87fdb77...**, and runs the existing maps/SHA smoke. Reapply cc-wiki's current Java overlay if continuing that experiment. If the board rebooted or the mount was changed by another owner, the deployer refuses a stale rollback; reassess the live state instead of forcing unmounts.
