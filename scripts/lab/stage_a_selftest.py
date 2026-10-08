#!/usr/bin/env python3
"""Stage-A selftest aggregate, parameterized for any U-series (from U13's build_decision.py).

    stage_a_selftest.py --root <executor run-tree root> --selector u14-candidate-union-v1 \
                        [--reference <sources.json>] [--out <dir>] [--known-answer <sha[:n]>]

Preserves every U13 behaviour, with the U13 tree reachable only through parameters:
  --root       e.g. $WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-03-u14-stage-a-plan
  --selector   physical U14 windows 1–6 direct + nested candidate runners, never U13 controls
  --pattern    legacy glob (U13: 'window*/u13-A*/*/runner/**/record.json'); an incomplete or
               contaminated U14 glob rejects instead of silently accepting 308 records
  --reference  reference sources.json (only needed for the retention-hook step; without it the
               script stops after the aggregate + explanations, which is the reusable half)

Behaviour kept from U13:
  1. Schema-2 process-selftest aggregate over EXACTLY the candidate's runner records.
  2. Excluded records counted per class (recovery smoke / evidence copy / contact-index symlink
     / fixture / executor state); an unrecognised non-runner record is an error, not a skip.
  3. Failure-line rescan from ANY pid (a pid that died before t5 must not be invisible).
  4. processes sorted by pid -> byte-reproducible report (stable SHA).
  5. Unknown (record, pid) auto-classified (icon-locator smoke / icon not found / bound-then-left /
     bind-failed / never-completed-bind / spawned-after-dump); unclassifiable is an error.
The script does NOT sign a decision — the outer does.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

MASTER = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MASTER / 'scripts/lab'))
if not (MASTER / 'scripts/lab/lab_paths.py').is_file():
    sys.path.append(str(MASTER.parent / 'westlake-harness/scripts/lab'))
# process_selftest.py lives in the U13 stage-A plan dir; it is on master, and the lane worktree
# may predate it — import from the shared master checkout when the local copy is absent
_plan_local = MASTER / 'benchmark/2026-10-03-u13-stage-a-plan'
_plan_master = MASTER.parent / 'westlake-harness/benchmark/2026-10-03-u13-stage-a-plan'
sys.path.insert(0, str(_plan_local if (_plan_local / 'process_selftest.py').is_file() else _plan_master))
import lab_paths  # noqa: E402
import process_selftest as ps  # noqa: E402

ROW = re.compile(r'^(\S+ \S+)\s+(\d+)\s+(\d+)\s+(\S)\s+(\S+)\s?(.*)$')
BOUND = '[B43-BIND] handleBindApplication returned OK'
BIND_FAILED = '[B43-BIND] ensureBindApplication FAILED'
U14_SELECTION = 'u14-candidate-union-v1'
U14_EXCLUSIONS = ('known-answer', 'recovery-smoke', 'evidence-copy', 'symlink', 'executor-state', 'U13-control')


def u14_record_class(root, source):
    relative = source.relative_to(root)
    if source.is_symlink() or any((root / parent).is_symlink() for parent in relative.parents if str(parent) != '.'):
        return 'symlink'
    name = relative.as_posix()
    if name.startswith('evidence/'):
        return 'known-answer'
    if re.match(r'window[1-6](?:-[^/]*)?/(?:landing|evidence|contact-index[^/]*)/', name):
        return 'evidence-copy'
    match = re.match(r'window[1-6](?:-[^/]*)?/u14-A[^/]*/(?:5ea|5cd|61b)/(.+)$', name)
    if match:
        tail = match[1]
        if '/recovery-smoke-' in '/' + tail:
            return 'recovery-smoke'
        if re.match(r'(?:runner/|candidate(?:-r\d+)?/runner/)', tail):
            return 'candidate'
        if re.match(r'control(?:-r\d+)?/runner/', tail):
            return 'U13-control'
        if re.match(r'(?:(?:(?:candidate|control)(?:-r\d+)?/)?transaction/)?(?:apply-device/|baseline/|post-apply/|final-[^/]+/|restored-[^/]+/|rollback-[^/]+/)', tail):
            return 'executor-state'
    raise SystemExit('unclassified U14 record: ' + name)


def u14_domain(root):
    records, omitted = [], {kind: [] for kind in U14_EXCLUSIONS}
    for source in sorted(root.rglob('record.json')):
        kind = u14_record_class(root, source)
        if kind == 'candidate':
            records.append(source)
        else:
            omitted[kind].append(source.relative_to(root).as_posix())
    if not records:
        raise SystemExit('no physical U14 candidate runner records')
    return records, omitted


def is_u14_selection(root, pattern):
    return pattern == U14_SELECTION or 'u14' in pattern.lower() or 'u14-stage-a' in root.name.lower()


def u14_selection_receipt(root):
    selected, omitted = u14_domain(root)
    body = dict(selector=U14_SELECTION, records=[source.relative_to(root).as_posix() for source in selected], excluded=omitted)
    return body, hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Selected:
    """Hand process_selftest.report() exactly the candidate's records (same code path)."""

    def __init__(self, records):
        self.records = records

    def rglob(self, _pattern):
        return self.records


def candidate_records(root, pattern):
    if is_u14_selection(root, pattern):
        expected, _ = u14_domain(root)
        selected = expected if pattern == U14_SELECTION else sorted(root.glob(pattern))
        missing, extra = set(expected) - set(selected), set(selected) - set(expected)
        if missing or extra:
            raise SystemExit('incomplete or contaminated U14 selection: selected=%d expected=%d missing=%d extra=%d' %
                             (len(selected), len(expected), len(missing), len(extra)))
        return expected
    return sorted(root.glob(pattern))


def excluded(root, pattern):
    """Every record.json under root that is not a candidate runner record, by why it is out."""
    if is_u14_selection(root, pattern):
        candidate_records(root, pattern)
        return u14_domain(root)[1]
    keep = set(candidate_records(root, pattern))
    out = {}
    for p in sorted(root.rglob('record.json')):
        if p in keep:
            continue
        rel = str(p.relative_to(root))
        why = ('known-answer fixture' if rel.startswith('evidence/') else
               'recovery smoke after rollback (runs on the restored base)' if '/recovery-smoke-' in rel else
               'window evidence copy of a runner record (same run id, no hilog)' if re.match(r'window[^/]*/evidence/', rel) else
               'executor state record (no app run)' if re.match(r'window[^/]*/u\d+-A[^/]*/[^/]+/(apply-device|baseline|post-apply|final-|restored-|rollback-)', rel) else
               'contact-index symlink to a counted runner record' if re.match(r'window[^/]*/contact-index-', rel) and p.resolve() in {k.resolve() for k in keep} else
               None)
        if why is None:
            raise SystemExit('unclassified non-runner record: ' + rel)
        out.setdefault(why, []).append(rel)
    return out


def pid_lines(lines):
    by = {}
    for n, line in enumerate(lines, 1):
        m = ROW.match(line)
        if m:
            by.setdefault(m[2], []).append((n, line))
    return by


def secs(line):
    return datetime.strptime('2026-' + line[:18], '%Y-%m-%d %H:%M:%S.%f').timestamp()


def failure_lines_any_pid(lines):
    return [n for n, line in enumerate(lines, 1)
            if '[WL-KS-PROBE]' in line and any(rx.search(line) for _, rx in ps.FAILURES.values())]


def classify(run, pid):
    """-> (reason, evidence path). Raises when the case fits no class."""
    rec_path = Path(run['record'])
    d = rec_path.parent
    rec = json.loads(rec_path.read_text())
    log = d / 'hilog.txt'
    if (rec.get('status') == 'batch_interrupted' and rec.get('clicked') is False and
            rec.get('error') == 'HDC lost remote status marker' and not rec.get('screenshots') and not log.exists()):
        return ('Interrupted before desktop click; HDC lost remote status marker, no hilog or screenshots. '
                'No probe observation: unknown, not crypto success (pre-launch-board-loss).', rec_path)
    if run['key'] == 'probe' and not log.exists() and 'package' in rec and 'bms' not in rec:
        return ('activation-smoke launcher icon-locator step (selected %s); not an app run: no key, no BMS uid and '
                'no hilog by design, so no [WL-KS-PROBE] line can exist' % rec['selected_icon']['id'], rec_path)
    if rec.get('status') == 'app_failed' and not list(d.glob('processes-t*.txt')):
        return ('status app_failed: the desktop icon of %s was not found after the retries, the app was never launched '
                '(no processes-t*.txt, no screenshots); nothing ran, so no probe' % rec['package'], rec_path)
    lines = log.read_text(errors='replace').splitlines()
    by = pid_lines(lines)
    pkg = rec['package']
    spawned = [p for p, rows in by.items() if any('FilterAppTrace %s %s' % (pkg, p) in l for _, l in rows[:5])]
    end = lines[-1][:18]
    if pid == '*':
        if not spawned:
            raise SystemExit('no spawned pid for %s' % run['record'])
        parts = []
        for p in spawned:
            rows = by[p]
            ok = [(n, l) for n, l in rows if '[WL-KS-PROBE]' in l and ps.OK.search(l)]
            bound = any(BOUND in l for _, l in rows)
            failed = next((l for _, l in rows if BIND_FAILED in l), None)
            if bound and ok:
                parts.append('pid %s bound and logged validateAead=OK at hilog line %d, then left: absent by PID number '
                             'from every processes-t*.txt, last line %s (hilog dump %s)' % (p, ok[0][0], rows[-1][1][:18], end))
            elif not bound and not any('[WL-KS-PROBE]' in l for _, l in rows):
                cause = ''
                if failed:
                    at = next(i for i, (_, l) in enumerate(rows) if BIND_FAILED in l)
                    cause = next((l.split('[stderr]')[-1].strip()[:150] for _, l in rows[at:] if 'Caused by:' in l), '')
                parts.append('pid %s never completed handleBindApplication (%s); the probe runs only after bind returns OK'
                             % (p, ('bind FAILED, ' + cause) if failed else 'died before bind'))
            else:
                raise SystemExit('unclassified spawned pid %s in %s' % (p, run['record']))
        return ('no appspawn-x process with BMS uid %s in any processes-t*.txt; ' % run['uid'] + '; '.join(parts), log)
    rows = by.get(pid, [])
    if not rows:
        return ('pid %s is listed in processes-t20.txt but has 0 lines in the hilog: spawned after the hilog dump (%s)'
                % (pid, end), log)
    if any(BIND_FAILED in l for _, l in rows):
        at = next(i for i, (_, l) in enumerate(rows) if BIND_FAILED in l)
        cause = next((l.split('[stderr]')[-1].strip()[:150] for _, l in rows[at:] if 'Caused by:' in l), '')
        return ('pid %s never completed handleBindApplication (bind FAILED, %s); the probe runs only after bind returns OK'
                % (pid, cause), log)
    if not any(BOUND in l for _, l in rows) and secs(lines[-1]) - secs(rows[-1][1]) <= 3:
        return ('pid %s spawned %s and was still in pre-bind init when the hilog was dumped (its last line %s, dump %s); '
                'the probe runs only after bind returns OK' % (pid, rows[0][1][:18], rows[-1][1][:18], end), log)
    raise SystemExit('unclassified pid %s in %s' % (pid, run['record']))


def issues(report):
    out = []
    for r in report['runs']:
        if not (r.get('status') != 'PASS' or r.get('validateAead_OK_count', 0) <= 0 or not r.get('processes') or
                any(v.get('status') != 'PASS' or not v.get('validateAead_OK') for v in r.get('processes', {}).values())):
            continue
        silent = [p for p, v in r.get('processes', {}).items() if v.get('status') != 'PASS' or not v.get('validateAead_OK')]
        out += [(r, p) for p in silent]
        if not silent or r.get('complete_hilog') is False:
            out.append((r, '*'))
    return out


def build(root, pattern):
    """Aggregate + explanations for one (root, pattern). Returns (report_body, report_sha, rows, excl, any_pid)."""
    records = candidate_records(root, pattern)
    if not records:
        raise SystemExit('no records match %s under %s' % (pattern, root))
    report = ps.report(Selected(records))
    for r in report['runs']:                      # pid-sorted processes -> byte-reproducible
        r['processes'] = dict(sorted(r['processes'].items(), key=lambda kv: int(kv[0])))
    body = json.dumps(report, indent=2) + '\n'
    report_sha = hashlib.sha256(body.encode()).hexdigest()
    any_pid = {}
    for r in report['runs']:
        log = Path(r['record']).parent / 'hilog.txt'
        if log.is_file():
            hits = failure_lines_any_pid(log.read_text(errors='replace').splitlines())
            if hits:
                any_pid[r['record']] = hits
    rows = []
    for run, pid in issues(report):
        reason, evidence = classify(run, pid)
        rows.append(dict(record=run['record'], key=run['key'], pid=pid, line_sha256='unknown', line_number=None,
                         reason=reason, evidence=str(evidence), evidence_sha256=sha(evidence)))
    excl = {k: len(v) for k, v in excluded(root, pattern).items()}
    return body, report_sha, rows, excl, any_pid, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', required=True, help='executor run-tree root (absolute or $WORKSPACES-relative)')
    selection = ap.add_mutually_exclusive_group(required=True)
    selection.add_argument('--pattern', help='legacy record glob; incomplete U14 selections reject')
    selection.add_argument('--selector', choices=[U14_SELECTION], help='complete physical U14 windows 1–6 candidate union')
    ap.add_argument('--reference', type=Path, help='reference sources.json; when given, also runs the retention hook path (requires the U13 plan importables)')
    ap.add_argument('--out', type=Path, help='output dir for <tag>-selftest.json (default: print summary only)')
    ap.add_argument('--known-answer', help='expected report-sha prefix (e.g. 0488fa09) for the tree being scanned')
    a = ap.parse_args(argv)
    a.pattern = a.selector or a.pattern

    root = Path(str(a.root).replace('$WORKSPACES', str(lab_paths.workspaces())))
    if not root.is_dir():
        raise SystemExit('no such root: %s' % root)
    body, report_sha, rows, excl, any_pid, report = build(root, a.pattern)
    if a.known_answer and not report_sha.startswith(a.known_answer):
        raise SystemExit('report sha %s does not match known answer prefix %s' % (report_sha, a.known_answer))
    if report['error_count'] or any_pid:
        raise SystemExit('failure-class probe line present: %d by pid filter, %d records by any-pid scan'
                         % (report['error_count'], len(any_pid)))
    if a.out:
        tag = re.sub(r'[^a-z0-9]+', '-', root.name.lower()).strip('-')
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / ('%s-selftest.json' % tag)).write_text(body)
        # explanations file: same row format as master's selftest-explanations-<tag>.json,
        # WITHOUT the bundle/approval fields -- the outer adds those when signing
        (a.out / ('%s-explanations.json' % tag)).write_text(
            json.dumps({'schema': 'outer-selftest-explanations/v1', 'report_sha256': report_sha,
                        'explanations': rows}, indent=1, ensure_ascii=False) + '\n')
    summary = dict(root=str(root), pattern=a.pattern, records=len(report['runs']),
                          PASS=sum(r['status'] == 'PASS' for r in report['runs']),
                          unknown=report['unknown_runs'],
                          REJECT=sum(r['status'] == 'REJECT' for r in report['runs']),
                          failure_lines_any_pid=len(any_pid), explanations=len(rows),
                          report_sha256=report_sha, excluded=excl)
    if is_u14_selection(root, a.pattern):
        selection_body, selection_sha = u14_selection_receipt(root)
        summary.update(selector=U14_SELECTION, selection_sha256=selection_sha,
                       pre_launch_board_loss=[row['record'] for row in rows if 'pre-launch-board-loss' in row['reason']])
        if a.out:
            (a.out / ('%s-selection.json' % tag)).write_text(json.dumps(selection_body, indent=2) + '\n')
    if a.out:
        (a.out / ('%s-summary.json' % tag)).write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
