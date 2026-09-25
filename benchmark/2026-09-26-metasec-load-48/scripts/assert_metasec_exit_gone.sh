#!/usr/bin/env bash
# #48 board assertions for candidate A (loader patch f162c5e, or preseed A2).
# Run over ONE run's child.stderr; exit 0 only if all pass. The gate is 5 fresh
# starts each surviving 3 minutes; wrap this per run.
# usage: assert_metasec_exit_gone.sh <child.stderr>
set -u
f="${1:?usage: assert_metasec_exit_gone.sh <child.stderr>}"
fail=0
say(){ printf '%-46s %s\n' "$1" "$2"; }

# 1. metasec errno13 gone (no app_lib map failure)
e=$(grep -ac 'app_lib/libmetasec_ml.so: failed to map library.*errno=13' "$f")
[ "$e" = 0 ] && say "metasec app_lib errno13 == 0" PASS || { say "metasec app_lib errno13 == 0 (got $e)" FAIL; fail=1; }

# 2. no UnsatisfiedLinkError on the shared background thread
u=$(grep -ac "thread='platform-back-handler' java.lang.UnsatisfiedLinkError.*metasec" "$f")
[ "$u" = 0 ] && say "platform-back-handler ULE == 0" PASS || { say "platform-back-handler ULE == 0 (got $u)" FAIL; fail=1; }

# 3. no X.DEv null-Looper NPE
n=$(grep -ac 'X.DEv.<init>' "$f")
[ "$n" = 0 ] && say "X.DEv null-Looper NPE == 0" PASS || { say "X.DEv null-Looper NPE == 0 (got $n)" FAIL; fail=1; }

# 4. process did not take the return->exit path
x=$(grep -ac 'launchActivityThread RETURNED\|initChild() returned WITHOUT exception' "$f")
[ "$x" = 0 ] && say "main-return _exit path == 0" PASS || { say "main-return _exit path == 0 (got $x)" FAIL; fail=1; }

# 5. the reuse actually fired (loader path) OR the preseed link was mapped (A2)
r=$(grep -ac 'SOURCE-NATIVE-IDENTICAL-COPY.*libmetasec_ml.so\|reuse.*libmetasec' "$f")
say "loader-reuse fired (info, A1)" "${r}"

# 6. no NEW crash after loading metasec (watch the TLS residual on the same thread)
c=$(grep -ac '^Fatal signal\|DoLazyInit.*abort\|MSTaskManager' "$f")
say "post-load Fatal/DoLazyInit (info; 0 wanted)" "${c}"

exit $fail
