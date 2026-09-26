#!/usr/bin/env bash
# #49 board assertions for the shim refused-list fix (westlake b14e4d0, shim 85c789f4).
# The gate is 5 fresh starts each >3min on a video article. Run per run's cppcrash dir
# and child.stderr.
# usage: assert_heap_corruption_gone.sh <run-dir>
set -u
d="${1:?usage: assert_heap_corruption_gone.sh <run-dir>}"
fail=0
say(){ printf '%-46s %s\n' "$1" "$2"; }

# 1. no musl get_meta heap-corruption cppcrash
gm=0
for f in "$d"/cppcrash-*; do [ -e "$f" ] || continue; grep -aq 'get_meta' "$f" && gm=$((gm+1)); done
[ "$gm" = 0 ] && say "get_meta heap-corruption cppcrash == 0" PASS || { say "get_meta cppcrash == 0 (got $gm)" FAIL; fail=1; }

# 2. xasan/heap_tracker were refused (shim did its job)
cs=$(ls "$d"/child.stderr 2>/dev/null | head -1)
if [ -n "$cs" ]; then
  r=$(grep -ac 'refusing self-trapping library:.*libnpth_\(xasan\|heap_tracker\)' "$cs")
  say "shim refused xasan/heap_tracker (info)" "$r"
  # 3. no SIG11 killed the process
  s=$(grep -ac 'killed by signal 11' "$d"/parent.log 2>/dev/null)
  [ "${s:-0}" = 0 ] && say "process not killed by SIG11" PASS || { say "process not killed by SIG11 (got $s)" FAIL; fail=1; }
fi

# 4. feed/article still work: an article body reached and process alive at 180s
# (leave the lifetime/screenshot check to the harness; here only flag a hard crash)
c=$(grep -ac '^Fatal signal' "$cs" 2>/dev/null)
say "Fatal-signal banners (info; npth work_thread SIGABRT may remain)" "${c:-0}"

exit $fail
