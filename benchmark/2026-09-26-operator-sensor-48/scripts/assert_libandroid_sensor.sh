#!/usr/bin/env bash
# #48 route C: assert the rebuilt core libandroid.so exports the 7 sensor no-ops
# metasec needs, so it relocates in the default namespace.
# usage: assert_libandroid_sensor.sh <libandroid.so>   (the core/native-runtime one, NOT webview)
set -u
L="${1:?usage: assert_libandroid_sensor.sh <libandroid.so>}"
need="ASensorManager_getInstance ASensorManager_getDefaultSensor ASensorManager_createEventQueue ASensorManager_destroyEventQueue ASensorEventQueue_getEvents ASensorEventQueue_enableSensor ASensorEventQueue_disableSensor"
fail=0
for s in $need; do
  # .so: dynamic symbols; .o: fall back to the plain symbol table
  if nm -D --defined-only "$L" 2>/dev/null | grep -qw "$s" || \
     readelf -W --dyn-syms "$L" 2>/dev/null | awk '$7!="UND"{print $8}' | grep -qw "$s" || \
     readelf -W -s "$L" 2>/dev/null | awk '$4=="FUNC"&&$5=="GLOBAL"&&$7!="UND"{print $8}' | grep -qw "$s"; then
    printf '  OK   %s\n' "$s"
  else
    printf '  MISS %s\n' "$s"; fail=1
  fi
done
[ "$fail" = 0 ] && echo "PASS: all 7 sensor no-ops exported" || echo "FAIL: missing sensor no-ops"
exit $fail
