#!/bin/bash
# _kimi.yue.sh
# Yue lane launcher: open two blue-background terminals on the rightmost
# display, one per yue lane:
#   1. _kimi.yue.design-verify.sh      (design/requirement validation, no device)
#   2. _kimi.yue.fn04-07-lifecycle.sh  (Fn04-Fn07 concept lifecycle agent)
# Safe to re-run: it only opens new windows, it never kills existing ones.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod +x "${DIR}/_kimi.yue.design-verify.sh" "${DIR}/_kimi.yue.fn04-07-lifecycle.sh" 2>/dev/null || true

# Rightmost screen rect in AppleScript coords (top-left origin, y down):
# "x1 y1 x2 y2"
RECT="$(osascript -l JavaScript -e '
ObjC.import("AppKit");
var screens=$.NSScreen.screens, main=screens.objectAtIndex(0).frame, best=null;
for (var i=0;i<screens.count;i++){var f=screens.objectAtIndex(i).frame; if(!best||f.origin.x>best.origin.x) best=f;}
var mainH=main.size.height;
var top=Math.round(mainH-(best.origin.y+best.size.height));
var bottom=Math.round(mainH-best.origin.y);
[Math.round(best.origin.x), top, Math.round(best.origin.x+best.size.width), bottom].join(" ")')"

read -r RX1 RY1 RX2 RY2 <<< "${RECT}"
MID_X=$(( (RX1 + RX2) / 2 ))
# small margins
RX1=$((RX1 + 10)); RY1=$((RY1 + 10)); RX2=$((RX2 - 10)); RY2=$((RY2 - 10))

osascript <<EOF
tell application "Terminal"
	activate
	set t1 to do script "${DIR}/_kimi.yue.design-verify.sh"
	set background color of t1 to {0, 5000, 28000}
	set normal text color of t1 to {56000, 58000, 60000}
	set cursor color of t1 to {65535, 65535, 65535}
	set bounds of front window to {${RX1}, ${RY1}, ${MID_X}, ${RY2}}

	set t2 to do script "${DIR}/_kimi.yue.fn04-07-lifecycle.sh"
	set background color of t2 to {0, 5000, 28000}
	set normal text color of t2 to {56000, 58000, 60000}
	set cursor color of t2 to {65535, 65535, 65535}
	set bounds of front window to {${MID_X}, ${RY1}, ${RX2}, ${RY2}}
end tell
EOF

echo "yue lanes launched on rightmost screen ${RECT}: design-verify (left half), fn04-07-lifecycle (right half)"
