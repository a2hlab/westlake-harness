#!/system/bin/sh
set -u
set -f
LC_ALL=C; export LC_ALL
LABEL_RECIPE_SHA256=9d23b52fb4cad50a1fea0a039873c5e4e510bd10fc18b2b07fce3c77a4a250c2
label_context() {
case "$1" in
/system/bin/appspawn-x) printf "%s\n" u:object_r:appspawn_exec:s0 ;;
/system/android/etc/fonts.xml) printf "%s\n" u:object_r:system_fonts_file:s0 ;;
/data/app|/data/app/*) printf "%s\n" u:object_r:data_app_el1_file:s0 ;;
/system/lib64/seccomp|/system/lib64/seccomp/*) printf "%s\n" u:object_r:system_file:s0 ;;
/system/android/lib64|/system/android/lib64/*) printf "%s\n" u:object_r:system_lib_file:s0 ;;
/system/lib64/westlake/route-a|/system/lib64/westlake/route-a/*) printf "%s\n" u:object_r:system_lib_file:s0 ;;
/system/android/framework/arm64/boot*.art) printf "%s\n" u:object_r:system_lib_file:s0 ;;
/system/android/framework/arm64/boot*.oat) printf "%s\n" u:object_r:system_lib_file:s0 ;;
/system/android/framework/arm64/boot*.vdex) printf "%s\n" u:object_r:system_lib_file:s0 ;;
*.jar) printf "%s\n" u:object_r:system_file:s0 ;;
*.json) printf "%s\n" u:object_r:system_etc_file:s0 ;;
*.so) printf "%s\n" u:object_r:system_lib_file:s0 ;;
*) printf "%s\n" u:object_r:system_file:s0 ;;
esac
}
label_required() { printf "%s\n" /system/bin/appspawn-x /system/android /system/lib64/appspawn/libwestlake_android_child.z.so /system/lib64/libwestlake_thread_guard_registry.so; }
label_safe() {
 case "$1" in *[!A-Za-z0-9_./+-]*|*//*|*/../*|*/./*|*/..|*/.|*/) return 1 ;; esac
 case "$1" in /system/*|/data/app/*) return 0 ;; *) return 1 ;; esac
}
label_source_safe() {
 case "$1" in *[!A-Za-z0-9_./+-]*|*//*|*/../*|*/./*|*/..|*/.|*/) return 1 ;; esac
 case "$1" in /data/*) return 0 ;; *) return 1 ;; esac
}
mode=${1:-audit}
case "$mode" in
 context) label_safe "${2:-}" || exit 2; label_context "$2"; exit 0 ;;
 audit|apply|audit-source|apply-source) ;;
 *) printf 'FAIL invalid mode\n'; exit 2 ;;
esac
plan=$(cat "${2:--}") || { printf 'FAIL plan unreadable\n'; exit 2; }
[ -n "$plan" ] || { printf 'FAIL empty plan\n'; exit 2; }
tab=$(printf '\t')
seen='|'
while IFS="$tab" read -r kind target source extra; do
 [ -z "$extra" ] || { printf 'FAIL invalid plan columns\n'; exit 2; }
 case "$kind" in file|directory) ;; *) printf 'FAIL invalid target kind\n'; exit 2 ;; esac
 label_safe "$target" || { printf 'FAIL unsafe target %s\n' "$target"; exit 2; }
 case "$seen" in *"|$target|"*) printf 'FAIL duplicate target %s\n' "$target"; exit 2 ;; esac
 seen="$seen$target|"
 case "$mode" in *-source) label_source_safe "$source" || { printf 'FAIL unsafe source %s\n' "$source"; exit 2; } ;; esac
done <<LABEL_PLAN_VALIDATE
$plan
LABEL_PLAN_VALIDATE
required=$(label_required)
while IFS= read -r wanted; do
 covered=0
 while IFS="$tab" read -r kind target source extra; do
  [ "$wanted" = "$target" ] && covered=1
  if [ "$kind" = directory ]; then case "$wanted" in "$target"/*) covered=1 ;; esac; fi
 done <<LABEL_PLAN_COVERAGE
$plan
LABEL_PLAN_COVERAGE
 [ "$covered" = 1 ] || { printf 'FAIL required target missing %s\n' "$wanted"; exit 2; }
done <<LABEL_REQUIRED
$required
LABEL_REQUIRED
paths=0
bad=0
seen_paths='|'
while IFS="$tab" read -r kind target source extra; do
 physical=$target
 case "$mode" in *-source) physical=$source ;; esac
 if [ "$kind" = directory ]; then
  toybox test -d "$physical" || { printf 'FAIL directory absent %s\n' "$physical"; exit 1; }
  entries=$(find "$physical" -print) || { printf 'FAIL incomplete tree %s\n' "$physical"; exit 1; }
 else
  toybox test -e "$physical" || { printf 'FAIL file absent %s\n' "$physical"; exit 1; }
  entries=$physical
 fi
 [ -n "$entries" ] || { printf 'FAIL empty inventory %s\n' "$physical"; exit 1; }
 while IFS= read -r entry; do
  case "$mode" in
   *-source) label_source_safe "$entry" || exit 2 ;;
   *) label_safe "$entry" || exit 2 ;;
  esac
  canonical="$target${entry#"$physical"}"
  seen_paths="$seen_paths$canonical|"
  expected=$(label_context "$canonical")
  listing=$(ls -Zd "$entry") || { printf 'FAIL %s expected=%s actual=unreadable\n' "$canonical" "$expected"; exit 1; }
  actual='?'
  labels=0
  for field in $listing; do
   case "$field" in *:object_r:*:s0) actual=$field; labels=$((labels+1)) ;; esac
  done
  [ "$labels" = 1 ] || actual='?'
  case "$mode" in
   apply|apply-source)
    if [ "$actual" != "$expected" ]; then
     chcon -h "$expected" "$entry" || { printf 'FAIL %s expected=%s actual=%s chcon=failed\n' "$canonical" "$expected" "$actual"; exit 1; }
     listing=$(ls -Zd "$entry") || exit 1
     actual='?'; labels=0
     for field in $listing; do
      case "$field" in *:object_r:*:s0) actual=$field; labels=$((labels+1)) ;; esac
     done
     [ "$labels" = 1 ] || actual='?'
    fi ;;
  esac
  paths=$((paths+1))
  if [ "$actual" != "$expected" ]; then
   bad=$((bad+1))
   printf 'FAIL %s expected=%s actual=%s\n' "$canonical" "$expected" "$actual"
  fi
 done <<LABEL_ENTRIES
$entries
LABEL_ENTRIES
done <<LABEL_PLAN_APPLY
$plan
LABEL_PLAN_APPLY
while IFS= read -r wanted; do
 case "$seen_paths" in *"|$wanted|"*) ;; *) printf 'FAIL required readback absent %s\n' "$wanted"; exit 1 ;; esac
done <<LABEL_FINAL_REQUIRED
$required
LABEL_FINAL_REQUIRED
printf 'LABEL-RECIPE paths=%s mismatches=%s recipe=%s\n' "$paths" "$bad" "$LABEL_RECIPE_SHA256"
if [ "$bad" = 0 ]; then printf 'PASS\n'; exit 0; fi
printf 'FAIL\n'; exit 1
