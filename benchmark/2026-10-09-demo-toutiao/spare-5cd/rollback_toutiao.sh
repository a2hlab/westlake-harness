#!/usr/bin/env bash
# rollback_toutiao.sh <SERIAL> — remove the Route-B Toutiao overlay and restore the pre-overlay fingerprint.
# RUNBOOK #12 compliant: NEVER kills appspawn-x. Hard-skips 61b (user demo). Verifies with snapshot_display.
set -u
SN="${1:?usage: rollback_toutiao.sh <SERIAL>}"
SKIP_SN="61b0657200000000000000000324012c"; [ "$SN" = "$SKIP_SN" ] && { echo "SKIP $SN (demo board)"; exit 0; }
HDC="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc"
RT="/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d"
STAGE="/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d"
D="/data/local/tmp/operator45"; F="$D/selfheal48"; PROV="/data/local/tmp/tt-prov"
OUT="${OUT:-$HOME/a2hlab-provision/$SN-rollback}"; mkdir -p "$OUT"
dev(){ gtimeout "${2:-40}" "$HDC" -t "$SN" shell "$1" 2>&1 | tr -d '\r'; }
say(){ printf '[rollback %s] %s\n' "${SN:0:8}" "$*"; }
gtimeout 20 "$HDC" list targets 2>/dev/null | grep -q "$SN" || { say "FAIL board not connected"; exit 1; }
# 1. stop B's watchdog/keeper and kill ONLY B's own processes (never appspawn-x)
dev "mkdir -p $F; touch $F/stop $D/stop $D/fresh48/stop $D/keeper.stop 2>/dev/null; for p in \$(cat $D/keeper.pid 2>/dev/null); do kill \$p 2>/dev/null; done; sleep 2; for p in \$(pidof com.ss.android.article.news source_app_namespace host_spawn); do kill -9 \$p 2>/dev/null; done; sleep 1; echo stopped" 30
# 2. uninstall the host HAP (removes the RT sandbox) + rm B's /data/local/tmp dirs (leave /data/local/tmp/asx: unified runtime bind-point)
dev "bm uninstall -n org.westlake.imehost 2>&1 | tail -1" 40
dev "rm -rf $STAGE $PROV $D; echo cleaned_tmp" 20
# 2b. reap Route B's orphan RT spawner (cc-t3 #91): B's RT ships its own appspawn-x under /data/local/tmp/asx;
#     source_app_namespace can leave it reparented to init (PPID 1). After the RT is removed above, its binary is
#     deleted, so we match name=appspawn-x AND exe shows "(deleted)" -> that is ONLY an orphan whose binary is gone.
#     RUNBOOK #12-safe: OH's init service is named "appspawn" (not matched); a LIVE route-a appspawn-x service has a
#     real (non-deleted) exe and is NOT matched. Exe-path match, never a blind pkill.
#     After the #91 isolation, B's spawner is named 'asx-spawner' (exe …/asx/asx-spawner); legacy overlays named it
#     'appspawn-x'. Reap either by exe-path with "(deleted)" — NEVER U13's /system/bin/appspawn-x (live, non-deleted exe).
dev "for p in \$(pidof asx-spawner appspawn-x 2>/dev/null); do e=\$(readlink /proc/\$p/exe 2>/dev/null); case \"\$e\" in *asx/asx-spawner*|*asx-spawner*'(deleted)'*|*asx/appspawn-x*'(deleted)'*|*appspawn-x*'(deleted)'*) echo \"reap orphan spawner pid=\$p exe=\$e\"; kill -9 \$p 2>/dev/null;; *) [ -n \"\$e\" ] && echo \"keep pid=\$p exe=\$e (live service, not a B orphan)\";; esac; done; echo spawner_reaped" 20
# 3. verify restored: imehost gone, no imehost0 window
gone=$(dev "bm dump -a 2>/dev/null | grep -c imehost" 20)
win=$(dev "hidumper -s WindowManagerService -a '-a' 2>/dev/null | grep -c imehost0" 15)
dev "rm -f /data/local/tmp/rb-shot.png; snapshot_display -t png -f /data/local/tmp/rb-shot.png >/dev/null 2>&1" 15 >/dev/null
gtimeout 30 "$HDC" -t "$SN" file recv /data/local/tmp/rb-shot.png "$OUT/rollback-screen.png" >/dev/null 2>&1
say "imehost_bundles_remaining=$gone imehost0_windows=$win shot=$OUT/rollback-screen.png"
if [ "$gone" = 0 ] && [ "$win" = 0 ]; then say "ROLLBACK OK (imehost uninstalled, no host window)"; echo OK > "$OUT/rollback-result"; exit 0
else say "ROLLBACK INCOMPLETE (imehost=$gone win=$win)"; echo INCOMPLETE > "$OUT/rollback-result"; exit 2; fi
