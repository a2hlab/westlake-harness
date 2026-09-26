#!/system/bin/sh
set -eu
RUNTIME=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d
PKG=com.ss.android.article.news
mode=fresh
prepare_profile(){
 if [ "$mode" = fresh ]; then
  # Preserve the original consent data once. Rotate only our disposable profiles.
  if [ ! -e "$RUNTIME/operator-speed50-original" ]; then
   old="$RUNTIME/operator-speed50-original"
  else
   old="$RUNTIME/operator-speed50-previous"
   rm -rf "$old" || return 1
  fi
  mkdir -p "$old" || return 1
  for p in app-data data webview-t-data; do
   [ ! -e "$RUNTIME/$p" ] || mv "$RUNTIME/$p" "$old/$p" || return 1
  done
 fi
 mkdir -p "$RUNTIME/data/dalvik-cache/arm64" "$RUNTIME/app-data/$PKG/code_cache" "$RUNTIME/app-data/$PKG/app_webview" "$RUNTIME/app-data/org.westlake.imehost" "$RUNTIME/webview-t-data" || return 1
 chown -R 20010053:20010053 "$RUNTIME/data" "$RUNTIME/app-data" "$RUNTIME/webview-t-data"
 chcon -R u:object_r:data_app_el2_file:s0 "$RUNTIME/app-data/$PKG"
}
prepare_profile
echo 1048576 > /proc/sys/vm/max_map_count
power-shell timeout -o 86400000
power-shell wakeup
aa start -b org.westlake.imehost -a EntryAbility
