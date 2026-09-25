#!/system/bin/sh
# Device-side driver for one Toutiao launch. Every action is stamped with
# CLOCK_REALTIME (date +%s.%N); the screenrecord Winscope track carries the
# realtime->elapsed offset, so these stamps land on the video/atrace clock.
# usage: drive.sh fresh|second OUT_DIR
PKG=com.ss.android.article.news
mode=$1; out=$2; log=$out/drive.log
mkdir -p $out; : > $log
t() { echo "$1 $(date +%s.%N)" >> $log; }
focus() { dumpsys window | grep -m1 mCurrentFocus; }
# Two windows steal focus on this phone and are closed with BACK before any
# tab tap: the system notification prompt (targetSdk 30 app on Android 16;
# BACK dismisses without recording a grant/deny) and Toutiao's own login
# promo (TransparentAccountLoginActivity, ~8 s into a second launch; first
# BACK hides its IME). BACK is never sent while focus is null or unknown, so
# the app itself is never backed out of.
clear_prompt() {
  for k in 1 2 3 4 5 6; do
    f=$(focus); echo "FOCUS $(date +%s.%N) $f" >> $log
    case "$f" in
      *activity.MainActivity*) return;;
      *GrantPermissionsActivity*|*LoginActivity*) t "BACK_$k"; input keyevent 4; sleep 1.5;;
      *) sleep 1;;
    esac
  done
}
tap() { clear_prompt; t "TAP_$1 $2 $3"; input tap $2 $3; }
t LAUNCH
am start -W -a android.intent.action.MAIN -c android.intent.category.LAUNCHER \
  -n $PKG/.activity.MainActivity > $out/amstart.txt 2>&1
t LAUNCHED
sleep 3
if [ "$mode" = fresh ]; then tap consent 600 1238; sleep 3; else sleep 7; fi
clear_prompt
dumpsys gfxinfo $PKG > $out/gfx_launch.txt; dumpsys gfxinfo $PKG reset > /dev/null
t GFX_RESET
sleep 1
tap hotspot 923 188; sleep 7
tap shenzhen 270 188; sleep 7
tap rebang 373 188; sleep 7
tap tuijian 64 188; sleep 7
dumpsys gfxinfo $PKG > $out/gfx_taps.txt
t END
