#!/usr/bin/env bash
set -u

HDC="${HDC:-hdc -t 5583f5be00000000000000000323012c}"
OUT="${OUT:?set OUT}"
mkdir -p "$OUT/raw" "$OUT/screens"

apps=(
  "opencalc|var/evidence/fixtures/github-apks/OpenCalc.v3.2.1.apk|com.darkempire78.opencalculator|com.darkempire78.opencalculator.activities.MainActivity"
  "gallery|var/evidence/fixtures/github-apks/gallery-396-foss-release.apk|com.simplemobiletools.gallery.pro|com.simplemobiletools.gallery.pro.activities.SplashActivity.Red"
  "newpipe|var/evidence/fixtures/github-apks/NewPipe_v0.29.0.apk|org.schabi.newpipe|org.schabi.newpipe.MainActivity"
)

$HDC shell "cat /proc/sys/kernel/random/boot_id; getenforce; param get const.product.name; param get const.product.model" \
  >"$OUT/raw/device-identity.txt" 2>&1

for row in "${apps[@]}"; do
  IFS='|' read -r label apk bundle activity <<<"$row"
  remote="/data/local/tmp/$(basename "$apk")"
  sha256sum "$apk" >"$OUT/raw/${label}-host-sha256.txt"
  $HDC file send "$apk" "$remote" >"$OUT/raw/${label}-send.txt" 2>&1
  $HDC shell "sha256sum '$remote'; bm install -p '$remote'; bm dump -n '$bundle'" \
    >"$OUT/raw/${label}-install-query.txt" 2>&1
  $HDC shell "hilog -r" >"$OUT/raw/${label}-hilog-clear.txt" 2>&1
  $HDC shell "aa start -a '$activity' -b '$bundle' -W" >"$OUT/raw/${label}-start.txt" 2>&1
  sleep 10
  $HDC shell "pidof '$bundle'; pidof appspawn-x; aa dump -a; hidumper -s WindowManagerService -a '-a'; getenforce" \
    >"$OUT/raw/${label}-state.txt" 2>&1
  $HDC shell snapshot_display >"$OUT/raw/${label}-snapshot.txt" 2>&1
  snapshot_path="$(sed -n 's/^success: .* write to \\([^ ]*\\.jpeg\\) as jpeg.*$/\\1/p' "$OUT/raw/${label}-snapshot.txt" | tail -1)"
  $HDC file recv "$snapshot_path" "$OUT/screens/${label}.jpeg" \
    >"$OUT/raw/${label}-snapshot-recv.txt" 2>&1
  $HDC shell "hilog -x" >"$OUT/raw/${label}-hilog.txt" 2>&1
  $HDC shell "aa force-stop '$bundle'" >"$OUT/raw/${label}-force-stop.txt" 2>&1
done

sha256sum "$OUT"/screens/*.jpeg >"$OUT/raw/screens-sha256.txt" 2>&1
