# First hour after the assigned board is flashed

> Superseded for this campaign by user decision #19: use OH6.1 R130+R155, no flash, no T006/OH7 deployment. This file is retained solely as the completed #15 reference audit.

This is an unexecuted operator run sheet, not a successful deployment record. Source inspection is **verified**; execution and screenshots are **unverified**. The windows below order the work; they do not guarantee completion within 60 minutes. `00.Workspace/...` citations are relative to that read-only source tree; `~/t006/...` citations identify the separately inspected local payload tooling. No device command or deployment script was run while preparing this file.

## 00–10: identity and read-only gates

Use the serial explicitly assigned by the outer reviewer. Acquire its board lock before step 2 (the first device write); never choose another board automatically. Set the following in the execution shell after that assignment:

```sh
export BMS_SERIAL='<assigned-full-serial>'
export BMS_HDC='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
export BMS_PAYLOAD="$HOME/t006/pack/t006-baseline-v3.tar.gz"
export BMS_WORK='/private/tmp/bms-oh7-first-hour'
export BMS_SCRIPT="$HOME/t006/pack/t006_baseline.py"
mkdir -p "$BMS_WORK"
shasum -a 256 "$BMS_PAYLOAD" "$BMS_SCRIPT"
"$BMS_HDC" list targets -v
"$BMS_HDC" -t "$BMS_SERIAL" shell param get const.ohos.fullname
"$BMS_HDC" -t "$BMS_SERIAL" shell param get const.ohos.releasetype
"$BMS_HDC" -t "$BMS_SERIAL" shell getenforce
"$BMS_HDC" -t "$BMS_SERIAL" shell cat /proc/sys/kernel/random/boot_id
python3 "$BMS_SCRIPT" doctor --hdc "$BMS_HDC" --serial "$BMS_SERIAL" --work "$BMS_WORK/doctor"
python3 "$BMS_SCRIPT" bringup --payload "$BMS_PAYLOAD" --work "$BMS_WORK/payload" \
  --hdc "$BMS_HDC" --serial "$BMS_SERIAL" --check-only
```

Before executing any deployment, require payload hash `e30a91993f06fc50ce401655837d9cfdec5a177aca65a311a5810ce14ae71145` and script hash `6693d60a7cf95db816d653032c4298561e57765132a1b1346a03a5937f79a6a8` (host-verified in `payload-member-diff.json`).

Pass: exact `OpenHarmony-7.0.0.38`, `Release`, `Enforcing`, read-only root, and all preflight checks pass. A stock board needs **more than 819200 KiB** root free space in this script; redeploy requires more than 61440 KiB. `--check-only` extracts locally and performs read-only device checks. Independently require every PAYLOAD.json member to exist and match its hash: the script's existing integrity comprehension checks mismatches only for files that exist, so a missing file can escape this particular check. Sources: `00.Workspace/CTS_QUICKSTART.md:11-18`, `~/t006/t006_baseline.py:479-512`, `~/t006/t006_baseline.py:741-772`.

Stop/fallback: a Beta or OH 6.1 identity stops deployment; return to the image selection/flash owner. Offline serial is a transport failure, not permission to use another board. Preserve the preflight report. Restarting the global HDC server is a documented transport remedy, but coordinate that shared-host interruption with the outer reviewer. Source: `00.Workspace/CTS_QUICKSTART.md:51-52`.

## 10–35: deploy the complete payload once

After the outer reviewer assigns the board and opens its deployment window, acquire the lock (exit 75 means stop with zero device writes):

```sh
"$HOME/orca/workspaces/westlake-inputs/tools/board_note.sh" lock \
  "$HOME/orca/workspaces/westlake-harness/.octos/boards/app-lighting.md" \
  "$BMS_SERIAL" cx-bms "assigned OH7 BMS deployment"
```


```sh
python3 "$BMS_SCRIPT" bringup --payload "$BMS_PAYLOAD" --work "$BMS_WORK/payload" \
  --hdc "$BMS_HDC" --serial "$BMS_SERIAL" --launch-strategy desktop \
  >"$BMS_WORK/bringup.stdout" 2>"$BMS_WORK/bringup.stderr"
```

This single command performs, in order: 598-file bridge deployment; 26 gap files; four symlinks, modes, resident runtime jar and Android data root; ANCO parameter; reboot; socket/BMS checks; first APK installation; desktop launch; process/maps checks and screenshot. Do not separately rerun each embedded write below if this command already succeeded. Source: `~/t006/t006_baseline.py:515-541`, `~/t006/t006_baseline.py:544-625`, `~/t006/t006_baseline.py:774-803`.

Pass: `payload/evidence/bringup-report.json` records successful payload, bridge, gap, symlink, jar, parameter, reboot, socket and SELinux checks. Require the boot ID to differ from the saved preflight ID. A return code or `BASELINE UP` alone is not sufficient for the later BMS/UI gates. The script's `bms_alive` check only excludes `failed to execute` from a short `bm dump`; it does not establish patched library identity. Source: `~/t006/t006_baseline.py:583-591`, `~/t006/t006_baseline.py:781-799`.

Stop/fallback: on first failure, preserve reports/logs and stop app installation or CTS expansion. `bridge_deploy.py` has device-local rollback and does not reboot itself, but this must not be called a complete rollback of the later gap/extras/reboot stages. If the board cannot boot, return to the prepared flash recovery procedure. Sources: `~/t006/run-new/bridge_deploy.py:12-18`, `~/t006/t006_baseline.py:515-580`, `~/t006/t006_baseline.py:781-789`.

## 35–45: prove the running foundation sees the patched BMS

The one-key command has already attempted HelloWorld installation by this point. This additional gate is required before trusting its installation claim or proceeding to more APKs. Check both mapped paths and hashes through the actual foundation process root; shell-global file hashes are insufficient. A historical run returned APK path error 9568269 because foundation retained an old mount namespace although shell-side new libraries loaded successfully. Source: `00.Workspace/evidence/runs/cts-getpackageinfo-20260915.md:133-145`.

```sh
"$BMS_HDC" -t "$BMS_SERIAL" shell \
  'for p in /proc/[0-9]*; do [ "$(cat "$p/comm" 2>/dev/null)" = foundation ] && echo "${p##*/}"; done' \
  >"$BMS_WORK/foundation-pids.txt"
```

Read the result and require exactly one PID, then set `BMS_FOUNDATION_PID` to that decimal value. Record its `stat`, current `boot_id`, `mountinfo`, and `maps`; if PID/boot changes during capture, repeat the read-only capture.

```sh
export BMS_FOUNDATION_PID='<observed-decimal-pid>'
"$BMS_HDC" -t "$BMS_SERIAL" shell "cat /proc/$BMS_FOUNDATION_PID/stat" >"$BMS_WORK/foundation-stat.txt"
"$BMS_HDC" -t "$BMS_SERIAL" shell "cat /proc/$BMS_FOUNDATION_PID/maps" >"$BMS_WORK/foundation-maps.txt"
"$BMS_HDC" -t "$BMS_SERIAL" shell "cat /proc/$BMS_FOUNDATION_PID/mountinfo" >"$BMS_WORK/foundation-mountinfo.txt"
"$BMS_HDC" -t "$BMS_SERIAL" shell "sha256sum \
/proc/$BMS_FOUNDATION_PID/root/system/lib64/libbms.z.so \
/proc/$BMS_FOUNDATION_PID/root/system/lib64/libinstalls.z.so \
/proc/$BMS_FOUNDATION_PID/root/system/lib64/platformsdk/libappexecfwk_common.z.so \
/proc/$BMS_FOUNDATION_PID/root/system/lib64/libapk_installer.so \
/proc/$BMS_FOUNDATION_PID/root/system/lib64/libappms.z.so" >"$BMS_WORK/foundation-library-sha256.txt"
```

Compare with the same members from the hash-verified `payload/gap.tar`, extracted by bringup under `payload/gapfiles`; do not compare against a similarly named old `.t001b-retained-*` library. These five active paths occur in `~/t006/run-new/gap-attrs.txt:14-25`. Require expected BMS mappings and matching process-root hashes. If a library is loaded only transiently during install, retain the installation logs/positive APK readback as additional evidence; do not claim that an absent mapping was observed loaded.

Stop/fallback: wrong process-root hash, `(deleted)` mappings, no foundation, or mismatched boot identity means the patched service is unverified. Preserve evidence and return to the package/deployment owner; do not use a shell dlopen success as a substitute. Source: `00.Workspace/evidence/runs/cts-getpackageinfo-20260915.md:135-145`.

## 45–50: first APK installation readback

The one-key command's first APK is the pinned HelloWorld, SHA-256 `2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd`. Its exact install operation is:

```sh
# Reference only: already executed inside a successful bringup.
"$BMS_HDC" -t "$BMS_SERIAL" file send "$BMS_WORK/payload/HelloWorld.apk" /data/local/tmp/HelloWorld.apk
"$BMS_HDC" -t "$BMS_SERIAL" shell bm install -p /data/local/tmp/HelloWorld.apk -u 100
```

Then collect readback (read-only):

```sh
"$BMS_HDC" -t "$BMS_SERIAL" shell bm dump -n com.example.helloworld >"$BMS_WORK/hello-bundle.txt"
"$BMS_HDC" -t "$BMS_SERIAL" shell \
  'sha256sum /data/app/el1/bundle/public/com.example.helloworld/android/base.apk' \
  >"$BMS_WORK/hello-installed-sha256.txt"
```

Pass: installer output says success, the named BMS record exists, installed APK hash matches the pin, the projected activity is `com.example.helloworld.MainActivity`, and the observed UID agrees with the script's expected `20010052`. The script also creates a hard link at `<bundle>/com.example.helloworld.apk` (link count 2) and app sandbox `code_cache/art-data` directories. These are real prerequisites, not optional cleanup. Sources: `~/t006/t006_baseline.py:51-57`, `~/t006/t006_baseline.py:126-130`, `~/t006/t006_baseline.py:594-625`.

Stop/fallback: UID drift, missing record/hash mismatch, missing hard link or directories prevents acceptance. Preserve `bringup-report.json` and hilog; resolve the actual installed identity before any retry. The present script hardcodes the HelloWorld UID, so do not silently generalize its directory recipe to another APK. Source: `~/t006/t006_baseline.py:56-57`, `~/t006/t006_baseline.py:619-624`.

## 50–60: desktop launch and screenshot review

Use the desktop launch already executed by `--launch-strategy desktop`. Inspect `payload/evidence/launch-gate-*/launch.json`, screen preparation records, and `payload/evidence/hello-gate.jpeg`. The path must show SceneBoard icon selection and tap. Do not replace it with `aa start`: the inspected code documents shell-caller rejection for Android-projected bundles. Sources: `~/t006/t006_baseline.py:645-701`, `00.Workspace/CTS_QUICKSTART.md:248-258`.

If a fresh capture is required after a successful tap:

```sh
"$BMS_HDC" -t "$BMS_SERIAL" shell snapshot_display -f /data/local/tmp/bms-first-hour.jpeg
"$BMS_HDC" -t "$BMS_SERIAL" file recv /data/local/tmp/bms-first-hour.jpeg "$BMS_WORK/hello-reviewed.jpeg"
```

Pass: a human sees HelloWorld content in the actual captured screen; the correct child remains alive and maps `liboh_adapter_bridge.so`. Record visual result separately from script checks. The existing gate records process/maps and saves a screenshot but does not interpret its pixels, nor does it hash the mapped bridge itself despite its docstring calling it pinned. Sources: `~/t006/t006_baseline.py:716-738`; harness `.octos/KNOWLEDGE-DIGEST.md:284-285`.

Stop/fallback: launcher, lock screen, blank/black content or wrong app is **not lit**, even if the script passes. Capture child error/actual screenshot and return the first observed blocker. Do not begin CTS as a substitute for the missing UI evidence. If CTS is the next assigned task, take this board's BCP snapshot and run class reachability first; missing API 35/36 types can produce 0 executed methods on the Android 14 runtime. Sources: `00.Workspace/CTS_QUICKSTART.md:20-22`, `00.Workspace/CTS_QUICKSTART.md:54-60`, `00.Workspace/CTS_QUICKSTART.md:93-113`.

At the end or on a stop path, release the same board lock with `board_note.sh unlock <board-path> "$BMS_SERIAL" cx-bms`; record the assigned execution task number and evidence directory. This preparation task #15 acquires no lock and executes none of the above device commands.
