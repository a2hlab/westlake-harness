#!/bin/bash
# judge_regression.sh <run-dir> — one-shot regression judging kit (offline, read-only).
#   ① regress_vs_signoff.py vs the 61b t3 outer signoff (byte+semantic, t20 last-capture tier)
#   ② contact-sheet wall of every key's best capture (t20 > t10 > t5), no PIL needed (HTML)
#   ③ per-key first-fatal-line grep from hilog.txt
# Output: <run-dir>/../judge-<basename> or --out DIR. Works while a round is still
# running (missing t20 → best lower tier, flagged in summary).
set -euo pipefail
SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
RUN=""
OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT=$2; shift 2 ;;
    *) RUN=$1; shift ;;
  esac
done
[ -n "$RUN" ] && [ -d "$RUN" ] || { echo "usage: judge_regression.sh <run-dir> [--out DIR]" >&2; exit 2; }
RUN=$(cd "$RUN" && pwd -P)
OUT=${OUT:-"$(dirname "$RUN")/judge-$(basename "$RUN")"}
mkdir -p "$OUT"

# locate regress_vs_signoff.py (own tree first, then the master checkout)
REGRESS=""
for c in "$SELF_DIR/../../benchmark/2026-10-09-demo-baseline/t4/regress_vs_signoff.py" \
         "${WORKSPACES:-$HOME/orca/workspaces}/westlake-harness/benchmark/2026-10-09-demo-baseline/t4/regress_vs_signoff.py"; do
  [ -f "$c" ] && REGRESS=$(cd "$(dirname "$c")" && pwd)/$(basename "$c") && break
done
[ -n "$REGRESS" ] || { echo "regress_vs_signoff.py not found" >&2; exit 2; }

echo "== [1/3] regress_vs_signoff vs 61b t3 signoff"
# Prefer the merged final/ tree: while a round is in progress, window-NN/runner
# copies coexist with final/ and regress_vs_signoff refuses duplicates.
REG_IN="$RUN"
# final/<serial>/<key> are SYMLINKS into window-NN/runner trees; plain find does
# not follow them, so detect via shell glob and point regress at final/ only.
if ls "$RUN"/final/*/*/record.json >/dev/null 2>&1; then
  REG_IN="$RUN/final"
fi
rm -rf "$OUT/regression"   # regress_vs_signoff refuses non-fresh output (L216)
python3 "$REGRESS" "$REG_IN" --out "$OUT/regression"
cat "$OUT/regression"/comparison.json 2>/dev/null | head -2 || true

echo "== [2/3]+[3/3] wall + first-fatal (python)"
python3 - "$RUN" "$OUT" <<'PY'
import json, re, sys, html
from pathlib import Path
run, out = Path(sys.argv[1]), Path(sys.argv[2])

# per-key dirs: prefer final/<serial>/<key>, else any depth-<=4 record.json holder
keys = {}
for rec in sorted(run.rglob('record.json')):
    d = rec.parent
    if 'final' in d.parts or d.name not in keys:
        keys.setdefault(d.name, d)
    keys[d.name] = keys.get(d.name) or d

FATAL = re.compile(r'(?:F [0-9]+ +[0-9]+ F |Fatal signal|SIGSEGV|SIGABRT|Check failed|Runtime aborting)')  # case-sensitive: "non-fatal" must NOT match
rows, missing_t20 = [], []
for key in sorted(keys):
    d = keys[key]
    tier = 'none'
    for t in ('t20', 't10', 't5'):
        if (d / f'{t}.jpeg').is_file():
            tier = t; break
    if tier != 't20':
        missing_t20.append(f'{key}({tier if tier != "none" else "no-capture"})')
    fatal = 'NONE'
    h = d / 'hilog.txt'
    if h.is_file():
        for line in h.read_text(errors='replace').splitlines():
            if FATAL.search(line):
                fatal = line.strip()[:150]; break
    rows.append((key, tier, fatal))

with open(out / 'fatal-first.tsv', 'w') as f:
    f.write('key\tcapture_tier\tfirst_fatal\n')
    for k, t, x in rows: f.write(f'{k}\t{t}\t{x}\n')

with open(out / 'wall.html', 'w') as f:
    f.write('<html><head><meta charset="utf-8"><title>regression wall</title>'
            '<style>body{background:#222;color:#ccc;font:12px monospace}'
            'img{height:220px;margin:2px;border:1px solid #555}'
            'div{display:inline-block;text-align:center;vertical-align:top}'
            'a{color:#8cf;text-decoration:none}</style></head><body>\n')
    for k, t, x in rows:
        d = keys[k]
        rel = d / f'{t}.jpeg'
        if t == 'none':
            f.write(f'<div><p>{html.escape(k)}</p><p>[no capture]</p></div>\n'); continue
        try: uri = rel.resolve().as_uri()
        except Exception: uri = html.escape(str(rel))
        mark = '' if t == 't20' else f' [{t}]'
        f.write(f'<div><a href="{uri}"><img src="{uri}" loading="lazy"></a><br>{html.escape(k)}{mark}</div>\n')
    f.write('</body></html>\n')

n = len(rows); nofatal = sum(1 for r in rows if r[2] == 'NONE')
summary = {
    'keys_judged': n, 't20_missing': missing_t20, 'keys_with_fatal': n - nofatal,
    't20_tier_note': 't20 preferred; [t10]/[t5] fallback flagged (round in progress?)',
    'permissive_note': 'regress_vs_signoff reads no selinux field — Permissive runs judged identically',
}
(out / 'summary.json').write_text(json.dumps(summary, indent=1, ensure_ascii=False) + '\n')
print(f"keys={n} t20_missing={len(missing_t20)} with_fatal={n - nofatal}")
print(f"wall: {out/'wall.html'}  fatal: {out/'fatal-first.tsv'}")
PY
echo "== done: $OUT (wall.html / fatal-first.tsv / summary.json / regression/)"
