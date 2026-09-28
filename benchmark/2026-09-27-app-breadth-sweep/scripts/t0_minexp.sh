#!/usr/bin/env bash
# t0_minexp.sh <app-key> — T0 MINIMAL KEY EXPERIMENT (board entry #4/#1 step 1).
# Validates the FIXED forensics collection on ONE app on 5ea34a45 ONLY:
#   (a) child stderr retrieved BEFORE any cleanup, via THREE paths:
#       /proc/<child>/root/..., <runtime>/private-tmp/..., <stage>/parent.log
#   (b) hilog ring cleared before launch + one-shot dump after + OFF-device filter
#       (char-class patterns, drop HDC_LOG/ExecuteCommand) => no self-match
#   (c) if no *_content render node after 30 s: kill -QUIT <child>, then find where
#       the ART thread stack actually landed (stderr growth? /data/anr? hilog?)
#   (d) render_node from `hidumper -s RenderService` grep, full dump kept for binding
#   (e) unique-per-run screenshot path + recv verification
# Evidence lands in $OUT (VM). Nothing here classifies LIT — screenshot only.
set -uo pipefail
APP="${1:?usage: t0_minexp.sh <app-key>}"
DO_QUIT="${2:-auto}"                       # auto|force|never  (auto = only when no render node)
S5=5ea34a4500000000000000001123012c
HDC=/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh
W=/home/dspfac/a2hlab/source-closure/verify
OUT="$HOME/a2hlab/board/$S5/t0-minexp/$APP"
EPOCH=$(date +%s)
mkdir -p "$OUT"
h(){ "$HDC" -t "$S5" "$@"; }
hs(){ h shell "$@"; }

[ -d "$W" ] || { echo "FATAL: workspace $W missing (VM bind mount?)"; exit 3; }
"$HDC" list targets 2>/dev/null | grep -qx "$S5" || { echo "REFUSE: $S5 not attached"; exit 2; }

echo "=== t0-minexp $APP epoch=$EPOCH ==="
# ---- 1. clean slate + bound the hilog window ----
hs "aa force-stop org.westlake.imehost 2>/dev/null; pkill -f '[a]ppspawn-x' 2>/dev/null; true" >/dev/null 2>&1
hs "rm -f /data/service/el1/public/appspawnx/adapter_child_*.stderr /data/misc/appspawnx/adapter_child_*.stderr" >/dev/null 2>&1
sleep 2
hs "hilog -r" >/dev/null 2>&1     # clear ring: post-run one-shot dump = this run only
hs "power-shell timeout -o 3600000" >/dev/null 2>&1

# ---- 2. probe launch (serial-pinned inside probe too) ----
cd "$HOME/a2hlab/manifest"
timeout 200 python3 tools/probe_source_app.py \
  --workspace "$W" --westlake-source "$W/westlake" \
  --framework-report "$HOME/a2hlab/board/$S5/framework-2/device-report.json" \
  --app-input "$HOME/a2hlab/app-inputs/$APP" --app "$APP" \
  --hdc "$HDC" --serial "$S5" --out "$OUT/probe" \
  --host-build "$W/out/signed-host" --webview-input "$W/out/webview-input-source" \
  > "$OUT/probe.stdout" 2> "$OUT/probe.stderr"
RC=$?
for k in child runtime stage; do
  eval "$k=\$(python3 -c \"import json;print(json.load(open('$OUT/probe/device-report.json')).get('$k') or '')\" 2>/dev/null)"
done
echo "probe rc=$RC child=${child:-none} runtime=${runtime:-none} stage=${stage:-none}"
[ -n "${child:-}" ] || { echo "FATAL: no child pid (see $OUT/probe.stderr)"; exit 3; }

# ---- 3. wait 30 s, then collect ----
sleep 30
ALIVE=$(hs "[ -d /proc/$child ] && echo yes || echo no" | tr -d '\r')

# (d) render node — full dump kept, content lines + app-bound count
hs "hidumper -s RenderService" > "$OUT/rs.full.$EPOCH.txt" 2>/dev/null
grep -a "_content" "$OUT/rs.full.$EPOCH.txt" > "$OUT/rs.content.$EPOCH.txt" || true
NODE_N=$(wc -l < "$OUT/rs.content.$EPOCH.txt" | tr -d ' ')

# (a) stderr trio, BEFORE any cleanup, BEFORE any signal
sd(){ hs "[ -f \"$1\" ] && wc -c < \"$1\" || echo -1" | tr -d '\r'; }
P_PROC="/proc/$child/root/data/local/tmp/adapter_child_$child.stderr"
P_RT="$runtime/private-tmp/adapter_child_$child.stderr"
P_SVC="/data/service/el1/public/appspawnx/adapter_child_$child.stderr"
S_PROC=$(sd "$P_PROC"); S_RT=$(sd "$P_RT"); S_SVC=$(sd "$P_SVC")
[ "$S_RT" != "-1" ] && h file recv "$P_RT" "$OUT/child.stderr.pre" >/dev/null 2>&1
[ "$S_PROC" != "-1" ] && hs "cat $P_PROC" > "$OUT/child.stderr.proc" 2>/dev/null
h file recv "$stage/parent.log" "$OUT/parent.log" >/dev/null 2>&1
echo "stderr sizes: proc=$S_PROC runtime=$S_RT svc=$S_SVC"

# (c) SIGQUIT when no render node (or forced for the experiment)
QUIT=no
if [ "$ALIVE" = "yes" ] && { [ "$DO_QUIT" = "force" ] || { [ "$DO_QUIT" = "auto" ] && [ "$NODE_N" = "0" ]; }; }; then
  PRE_SZ=$S_RT
  hs "kill -QUIT $child" >/dev/null 2>&1; QUIT=yes
  sleep 6
  POST_SZ=$(sd "$P_RT")
  echo "SIGQUIT sent: stderr $PRE_SZ -> $POST_SZ bytes"
  [ "$POST_SZ" != "-1" ] && [ "$POST_SZ" != "$PRE_SZ" ] && \
    hs "tail -c $((POST_SZ - PRE_SZ)) $P_RT" > "$OUT/quit.stack.txt" 2>/dev/null
  hs "/bin/ls -la /data/anr/ 2>/dev/null" > "$OUT/anr.ls.txt" 2>/dev/null
fi

# (e) screenshot: unique dir per run, verify local recv, remove remote copy
SDIR="/data/local/tmp/t0sweep/$EPOCH"
hs "mkdir -p $SDIR" >/dev/null 2>&1
hs "snapshot_display -f $SDIR/$APP.jpeg" >/dev/null 2>&1
h file recv "$SDIR/$APP.jpeg" "$OUT/screen.$EPOCH.jpeg" >/dev/null 2>&1
SHOT=ok; [ -s "$OUT/screen.$EPOCH.jpeg" ] || SHOT=missing
hs "rm -rf $SDIR" >/dev/null 2>&1

# (b) hilog one-shot, filtered OFF-device (char class, no self-match) + TOUCH21 filter for stderr
timeout 12 hs "hilog -x" > "$OUT/hilog.raw.$EPOCH.txt" 2>/dev/null
grep -aiE '[F]atal signal|[S]IGSEGV|[S]IGABRT|[c]annot locate symbol|[E]rror relocating|[s]ymbol not found|[U]nsatisfiedLink|[F]ATAL EXCEPTION' "$OUT/hilog.raw.$EPOCH.txt" \
  | grep -av "HDC_LOG" | grep -av "ExecuteCommand" > "$OUT/hilog.crash.$EPOCH.txt" || true
for f in "$OUT/child.stderr.pre" "$OUT/child.stderr.proc"; do
  [ -f "$f" ] || continue
  RAW=$(wc -l < "$f" | tr -d ' ')
  grep -av "TOUCH21-POLL" "$f" > "$f.filtered"
  FIL=$(wc -l < "$f.filtered" | tr -d ' ')
  echo "$f: raw=$RAW filtered=$FIL"
done

# ---- 4. teardown ----
hs "aa force-stop org.westlake.imehost 2>/dev/null; kill $child 2>/dev/null; pkill -f '[a]ppspawn-x' 2>/dev/null; true" >/dev/null 2>&1

echo "=== SUMMARY $APP ==="
cat <<EOF
{"app":"$APP","epoch":$EPOCH,"probe_rc":$RC,"child":$child,"alive_30s":"$ALIVE",
 "render_content_nodes":$NODE_N,"sigquit_sent":"$QUIT",
 "stderr_bytes":{"proc":$S_PROC,"runtime":$S_RT,"svc":$S_SVC},
 "parent_log_bytes":$( [ -f "$OUT/parent.log" ] && wc -c < "$OUT/parent.log" || echo 0 ),
 "hilog_crash_bytes":$(wc -c < "$OUT/hilog.crash.$EPOCH.txt" | tr -d ' '),
 "screenshot":"$SHOT","runtime":"$runtime"}
EOF
