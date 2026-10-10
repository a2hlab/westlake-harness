#!/system/bin/sh
# Reversible DISABLE toggle for the U13 autostart. Drops (or clears, with --enable) the DISABLED marker that both boot
# services short-circuit on. After `disable` + reboot the board lands on BARE /system (no replay, no appspawn-x start,
# no overlay) while the cfg/scripts/archive stay installed and re-armable. Does NOT reboot; does NOT remove anything.
set -u
ROOT=/data/westlake-demo/u13
M="$ROOT/DISABLED"
[ -d "$ROOT" ] || { echo "disable: not installed ($ROOT absent)"; exit 1; }
case "${1:-disable}" in
  disable)
    { echo "disabled_at=$(date -Iseconds 2>/dev/null)"; echo "by=westlake-u13-autostart-disable"; } > "$M" 2>/dev/null || { echo "disable: cannot write $M"; exit 1; }
    chmod 0444 "$M" 2>/dev/null
    echo "disable: DISABLED marker set -> next boot lands on bare /system (machinery stays, re-arm with --enable)" ;;
  --enable|enable)
    rm -f "$M" 2>/dev/null && echo "enable: marker cleared -> autostart armed for next boot" || { echo "enable: could not clear $M"; exit 1; } ;;
  status)
    [ -e "$M" ] && echo "status: DISABLED ($(sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/ /g' "$M" 2>/dev/null))" || echo "status: ENABLED" ;;
  *) echo "usage: $0 [disable|--enable|status]"; exit 2 ;;
esac
