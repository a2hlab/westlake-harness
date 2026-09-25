#!/system/bin/sh
# #48 candidate A2 (no rebuild): before the app starts, pre-seed the app's private
# app_lib/libmetasec_ml.so as a symlink to the executable asx copy, so metasec's
# System.load maps the asx inode (a location OH allows the app to execute) instead
# of the non-executable app_lib copy that gives errno13.
#
# This is the fast, no-rebuild probe. The sound fix is the loader patch
# (art-build fix/metasec-load-48 f162c5e), which is immune to metasec rewriting
# its own copy. A2 only holds if metasec does NOT unlink/overwrite the file
# before System.load — verify on the board (see the assertions below).
#
# Idempotent. Run as the board's su shell, before front-staging the app.
# usage: preseed_metasec_applib.sh [pkg] [asx_root] [app_uid]
set -u
PKG="${1:-com.ss.android.article.news}"
ASX="${2:-/data/local/tmp/asx}"
APP_UID48="${3:-20010053}"
SRC="$ASX/lib/arm64-v8a/libmetasec_ml.so"
DIR="/data/data/$PKG/app_lib"
DST="$DIR/libmetasec_ml.so"

[ -f "$SRC" ] || { echo "preseed: source missing: $SRC" >&2; exit 2; }
mkdir -p "$DIR" || exit 3
# idempotent: replace whatever is there (stale file or old link) with the link
rm -f "$DST"
ln -s "$SRC" "$DST" || exit 4
# make the app uid able to traverse/read the link and its dir
chown "$APP_UID48:$APP_UID48" "$DIR" 2>/dev/null
chown -h "$APP_UID48:$APP_UID48" "$DST" 2>/dev/null
# give the app-data SELinux label so normal_hap may reach the link (target inode's
# own label still governs the executable mapping, which asx already permits)
restorecon "$DIR" "$DST" 2>/dev/null
ls -lZ "$DST" 2>/dev/null || ls -l "$DST"
echo "preseed: $DST -> $SRC"
