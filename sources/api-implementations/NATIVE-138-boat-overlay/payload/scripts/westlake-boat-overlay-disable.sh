#!/system/bin/sh
# Reversible toggle for the Boat boot overlay (cc-t3 #91). DISABLED marker short-circuits westlake-boat-overlay.sh at
# the next boot (board comes up as the plain unified state, no Boat binds). Re-armable. No reboot here. No setenforce.
#   westlake-boat-overlay-disable.sh [disable|--enable|status]
set -u
ROOT=/data/westlake-demo/u13; M="$ROOT/BOAT_DISABLED"
mkdir -p "$ROOT" 2>/dev/null
case "${1:-disable}" in
  disable)  : > "$M" && echo "boat-overlay DISABLED ($M) — next boot skips Boat binds (unified state)";;
  --enable) rm -f "$M" && echo "boat-overlay ENABLED — next boot applies Boat binds";;
  status)   [ -e "$M" ] && echo "DISABLED" || echo "ENABLED";;
  *) echo "usage: $0 [disable|--enable|status]" >&2; exit 2;;
esac
exit 0
