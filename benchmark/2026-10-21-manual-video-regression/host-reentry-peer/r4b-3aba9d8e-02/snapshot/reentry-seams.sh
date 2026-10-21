#!/system/bin/sh
# File interface compatible with reentry-seams.sh@900c54a2.
# Table rules reused from candidate-r3/strict_wm.sh. No device calls, awk or Python.
rc_isnat() { case "$1" in ''|*[!0-9]*) return 1;; *) return 0;; esac; }
rc_isint() {
 case "$1" in
 ''|-) return 1;;
 -*) rc_isnat "${1#-}";;
 *) rc_isnat "$1";;
 esac
}

# One complete read; output: name pid wid z owned(yes|no).
# Subshell confines parser variables and noglob to this validator.
rc_validate_wms() (
 set -f
 [ "$#" = 2 ] && [ -f "$1" ] && [ -r "$1" ] || return 1
 rc_file=$1; rc_owned=$2
 for rc_pid in $rc_owned; do
  rc_isnat "$rc_pid" && [ "$rc_pid" -gt 0 ] || return 1
 done
 rc_header=0; rc_footer=0; rc_focuses=0; rc_all=0; rc_high=0
 rc_count=0; rc_total=0; rc_focus=; rc_rows=; rc_ids=' '; rc_result=no
 rc_boot=0; rc_remote=0
 while IFS= read -r rc_line || [ -n "$rc_line" ]; do
  set -- $rc_line
  [ "$#" -gt 0 ] || continue
  case "$1" in -*) continue;; esac
  if [ "$1" = WindowName ]; then
   [ "$rc_header" = 0 ] && [ "$rc_footer" = 0 ] && [ "$#" -ge 10 ] || return 1
   [ "$1:$2:$3:$4:$5:$6:$7:$8:$9" = WindowName:DisplayId:Pid:WinId:Type:Mode:Flag:ZOrd:Orientation ] && [ "${10}" = '[' ] || return 1
   rc_header=1; continue
  fi
  if [ "$rc_header" = 0 ]; then
   # Optional original capture envelope: one kernel boot UUID before WMS.
   [ "$rc_boot" = 0 ] && [ "$#" = 1 ] && [ "${#1}" = 36 ] || return 1
   case "$1" in *[!0-9a-f-]*) return 1;; esac
   case "$1" in ????????-????-????-????-????????????) :;; *) return 1;; esac
   rc_boot=1; continue
  fi
  case "$1" in
   Focus)
    [ "$rc_footer" = 0 ] && [ "$rc_focuses" = 0 ] && [ "$#" = 3 ] && [ "$2" = window: ] && rc_isnat "$3" || return 1
    rc_focuses=1; rc_focus=$3; continue;;
   All)
    [ "$rc_all" = 0 ] && [ "$#" = 3 ] && [ "$2:$3" = Focus:window: ] || return 1
    rc_all=1; continue;;
   DisplayId:)
    [ "$#" = 4 ] && [ "$3" = WindowId: ] && rc_isnat "$2" && rc_isnat "$4" || return 1
    [ "$2" = 0 ] || return 1
    continue;;
   SingleHand:)
    [ "$#" = 4 ] || return 1
    continue;;
   Total)
    [ "$rc_footer" = 0 ] && [ "$rc_focuses" = 1 ] && [ "$#" = 4 ] && [ "$2:$3" = window:num: ] && rc_isnat "$4" && [ "$4" -gt 0 ] || return 1
    rc_total=$4; rc_footer=1; continue;;
   Highlighted)
    [ "$rc_high" = 0 ] && [ "$#" = 3 ] && [ "$2" = windows: ] && rc_isnat "$3" || return 1
    rc_high=1; continue;;
   WMS_REMOTE_RC=*)
    [ "$rc_remote" = 0 ] && [ "$rc_footer" = 1 ] && [ "$#" = 1 ] && [ "$1" = WMS_REMOTE_RC=0 ] || return 1
    rc_remote=1; continue;;
  esac
  # Every other nonblank line is a data row, never silently skipped.
  [ "$rc_footer" = 0 ] && [ "$rc_focuses" = 0 ] && [ "$#" -ge 15 ] || return 1
  [ "${10}" = '[' ] && [ "${15}" = ']' ] || return 1
  for rc_num in "$2" "$3" "$4" "$5" "$6" "$7" "$9"; do rc_isnat "$rc_num" || return 1; done
  rc_isint "$8" || return 1
  for rc_num in "${11}" "${12}" "${13}" "${14}"; do rc_isint "$rc_num" || return 1; done
  [ "$3" -gt 0 ] && [ "$4" -gt 0 ] || return 1
  case "$rc_ids" in *" $4 "*) return 1;; esac
  rc_ids="$rc_ids$4 "
  rc_count=$((rc_count + 1))
  rc_rows="$rc_rows$1 $3 $4 $8
"
  for rc_pid in $rc_owned; do [ "$3" != "$rc_pid" ] || rc_result=yes; done
 done < "$rc_file"
 [ "$rc_header" = 1 ] && [ "$rc_footer" = 1 ] && [ "$rc_focuses" = 1 ] && [ "$rc_count" -gt 0 ] || return 1
 # Real OH totals may exceed printed rows. Equality would reject valid captures.
 [ "$rc_total" -ge "$rc_count" ] || return 1
 rc_hits=0; rc_match=
 while read -r rc_name rc_pid rc_wid rc_z; do
  [ "$rc_wid" = "$rc_focus" ] || continue
  rc_hits=$((rc_hits + 1)); rc_match="$rc_name $rc_pid $rc_wid $rc_z"
 done <<ROWS
$rc_rows
ROWS
 [ "$rc_hits" = 1 ] || return 1
 printf '%s %s\n' "$rc_match" "$rc_result"
)

# <dumpfile> -> "name pid wid z" or "error". Only visible focused rows qualify.
rc_parse_focus() {
 rc_valid=$(rc_validate_wms "$1" '') || { echo error; return 0; }
 set -- $rc_valid
 [ "$#" = 5 ] || { echo error; return 0; }
 case "$4" in -*) echo error; return 0;; esac
 printf '%s %s %s %s\n' "$1" "$2" "$3" "$4"
}

# <dumpfile> <owned child pids> -> yes/no/unknown. Hidden child windows count.
rc_parse_owned_window() {
 rc_valid=$(rc_validate_wms "$1" "$2") || { echo unknown; return 0; }
 set -- $rc_valid
 [ "$#" = 5 ] || { echo unknown; return 0; }
 printf '%s\n' "$5"
}

# Classification only; caller must verify process identity and parent WID.
rc_classify_focus() {
 rc_focus_arg=$1; rc_desk_arg=$2; rc_host_arg=$3; rc_hostwid_arg=$4
 case "$rc_focus_arg" in error|'') echo error; return 0;; esac
 set -- $rc_focus_arg
 [ "$#" = 4 ] && rc_isnat "$2" && rc_isnat "$3" && rc_isnat "$4" || { echo error; return 0; }
 if [ -n "$rc_desk_arg" ] && [ "$1" = "$rc_desk_arg" ]; then echo desktop
 elif [ "$1" = "$rc_host_arg" ] && [ "$3" = "$rc_hostwid_arg" ]; then echo "host $3"
 else echo other
 fi
}
