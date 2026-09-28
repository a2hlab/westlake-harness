#!/bin/bash
# Toutiao "usable" acceptance on one OH board, as the operator defined it: the feed shows real headlines, it
# scrolls, an article opens, and the process is still alive afterwards. Prints one JSON line.
# usage: toutiao_accept.sh <serial> <framework-report (VM path)> <tag> [extra probe_source_app.py args...]
# Each check reads the view tree (tap channel `v`), never a screenshot alone; coordinates are screen
# coordinates (the #8 touch fix maps them to the right window).
set -u
S=$1; FW=$2; TAG=$3; shift 3; EXTRA="$*"
H=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
HDC=/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh
D=/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/ttdrive.sh
RUN=/home/zhaoyue/a2hlab/board/$S/$TAG
dev() { "$H" -t "$S" shell "$1" | LC_ALL=C tr -d '\r'; }
alive() { dev "[ -d /proc/$CHILD ] && echo 1 || echo 0"; }
texts() {  # distinct quoted texts in the current view tree
  VT_WAIT=6 "$D" "$S" "$RUN" vt 2>/dev/null | python3 -c '
import re, sys
sys.stdin.reconfigure(errors="replace")
seen = []
for line in sys.stdin:
    m = re.search(r"\"(.+?)\"\s*$", line.rstrip())
    if m and m.group(1) not in seen: seen.append(m.group(1))
print("\n".join(seen))'
}

dev 'kill -9 $(pidof appspawn-x) 2>/dev/null; power-shell wakeup >/dev/null; power-shell timeout -o 86400000 >/dev/null' >/dev/null
net=$(dev "ping -c3 -W3 223.5.5.5 2>&1 | grep -oE '[0-9]+% packet loss'")
CHILD=$(orb -m a2hlab bash -lc "A=/home/dspfac/a2hlab/source-closure/verify; B=\$A/out; cd ~/a2hlab/manifest && python3 tools/probe_source_app.py \
  --workspace \$A --westlake-source \$A/westlake --framework-report $FW --app-input ~/a2hlab/app-inputs/toutiao --app toutiao \
  --hdc $HDC --serial $S --out $RUN --host-build \$B/signed-host --webview-input \$B/webview-input-source \
  --android-native-target libvision_core.so --android-native-target libc++_shared.so $EXTRA 2>&1" | grep -o '"child": [0-9]*' | grep -o '[0-9]*$')
[ -z "$CHILD" ] && { echo '{"launch":"failed"}'; exit 1; }
start=$(date +%s)
sleep 60
dev 'power-shell wakeup >/dev/null; aa start -b org.westlake.imehost -a EntryAbility >/dev/null'
"$D" "$S" "$RUN" consent >/dev/null 2>&1
sleep 20
feed=$(texts)
headlines=$(printf '%s\n' "$feed" | awk 'length($0) >= 12' | grep -vE '个人信息|同意|网络不可用|搜你想看的' | head -8)
# scroll the feed up by a screen, then open the first long-text row by its screen centre
dev "echo 'd 600 1500' > /data/local/tmp/noice_tap; sleep 0.05; echo 'm 600 1000' > /data/local/tmp/noice_tap; sleep 0.05; echo 'u 600 600' > /data/local/tmp/noice_tap"
sleep 4
after_scroll=$(texts)
scrolled=$([ "$(printf '%s' "$feed" | md5)" != "$(printf '%s' "$after_scroll" | md5)" ] && echo true || echo false)
dev "echo 'c 600 700' > /data/local/tmp/noice_tap"
sleep 8
after_tap=$(texts)
opened=$([ "$(printf '%s' "$after_scroll" | md5)" != "$(printf '%s' "$after_tap" | md5)" ] && echo true || echo false)
sleep 60
alive_end=$(alive)
crash=$(dev "ls /data/log/faultlog/temp/ | grep -- '-$CHILD-'")
python3 - "$S" "$TAG" "$CHILD" "$net" "$(( $(date +%s) - start ))" "$scrolled" "$opened" "$alive_end" "$crash" "$headlines" <<'EOF'
import json, sys
s, tag, child, net, secs, scrolled, opened, alive, crash, heads = sys.argv[1:11]
heads = [h for h in heads.split("\n") if h]
print(json.dumps({"serial": s[:8], "tag": tag, "child": int(child), "network": net, "seconds": int(secs),
                  "headlines": heads, "feed_has_content": len(heads) >= 3, "scrolled": scrolled == "true",
                  "article_opened": opened == "true", "alive_at_end": alive == "1", "crash": crash or None},
                 ensure_ascii=False))
EOF
