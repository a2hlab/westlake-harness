#!/usr/bin/env python3
"""U13 stage-A outer decision inputs, rebuilt from the executor's run tree.

  build_decision.py [--check-only]

1. Schema-2 process-selftest aggregate over exactly the U13 candidate's runner records
   (window*/u13-A*/<board>/runner/**/record.json). Excluded and listed: recovery smokes (they run after the
   rollback, on U10.1T8), window evidence copies (same run ids, no hilog), known-answer fixtures, executor
   state records (apply/baseline/rollback/final -- no app run).
2. One exact outer explanation per unknown (record, pid), classified from the record's own files; a case that
   fits no class stops the build. Independently of process_selftest's PID filter, every hilog is scanned for
   failure-class [WL-KS-PROBE] lines from ANY pid (a process that hit badtag and died before t5 would
   otherwise be invisible); one such line stops the build.
3. promotion_hook_u13.retention_reason must return None for both U13 bundles (common 91272eaf, 61b 8861a11a)
   with each board's stage-A candidate smoke standing in for the stage-B smoke.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
MASTER = HERE.parents[1]
sys.path.insert(0, str(MASTER / 'scripts/lab'))
sys.path.insert(0, str(MASTER / 'benchmark/2026-10-03-u13-stage-a-plan'))
import lab_paths  # noqa: E402
import process_selftest as ps  # noqa: E402
import promotion_hook_u13 as hook  # noqa: E402

ROOT = lab_paths.workspaces() / 'westlake-harness-u7-executor/benchmark/2026-10-03-u13-stage-a-plan'
REFERENCE = MASTER / 'benchmark/2026-10-03-u13-reference/sources.json'
AUTH = MASTER / 'benchmark/2026-10-03-u13-stage-a-plan/outer-window-authorization.json'
ROW = re.compile(r'^(\S+ \S+)\s+(\d+)\s+(\d+)\s+(\S)\s+(\S+)\s?(.*)$')
BOUND = '[B43-BIND] handleBindApplication returned OK'
BIND_FAILED = '[B43-BIND] ensureBindApplication FAILED'
BOARDS = {'5ea': '5ea34a4500000000000000001123012c', '5cd': '5cd1e3dd00000000000000000923012c',
          '61b': '61b0657200000000000000000324012c'}
SIGNED_AT = '2026-10-03T08:56:00+08:00'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def u13_records():
    return sorted(ROOT.glob('window*/u13-A*/*/runner/**/record.json'))


class Selected:
    """process_selftest.report() takes a root and rglobs it; hand it exactly the U13 records so the summary
    fields come from the same code as every per-shard report."""
    def __init__(self, records):
        self.records = records

    def rglob(self, _pattern):
        return self.records


def excluded():
    """Every record.json under ROOT that is not a U13 runner record, counted by why it is out."""
    keep = set(u13_records())
    out = {}
    for p in sorted(ROOT.rglob('record.json')):
        if p in keep:
            continue
        rel = str(p.relative_to(ROOT))
        why = ('known-answer fixture' if rel.startswith('evidence/') else
               'recovery smoke after rollback (runs on U10.1T8)' if '/recovery-smoke-' in rel else
               'window evidence copy of a runner record (same run id, no hilog)' if re.match(r'window[^/]*/evidence/', rel) else
               'executor state record (no app run)' if re.match(r'window[^/]*/u13-A[^/]*/[^/]+/(apply-device|baseline|post-apply|final-|restored-|rollback-)', rel) else
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
    """hilog 'MM-DD HH:MM:SS.mmm' -> seconds (same year; only differences are used)."""
    return datetime.strptime('2026-' + line[:18], '%Y-%m-%d %H:%M:%S.%f').timestamp()


def failure_lines_any_pid(lines):
    hits = []
    for n, line in enumerate(lines, 1):
        if '[WL-KS-PROBE]' in line and any(rx.search(line) for _, rx in ps.FAILURES.values()):
            hits.append(n)
    return hits


def classify(run, pid):
    """-> (reason, evidence path). Raises when the case fits no class."""
    rec_path = Path(run['record'])
    d = rec_path.parent
    rec = json.loads(rec_path.read_text())
    log = d / 'hilog.txt'
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
    """Exactly the (record, pid) set promotion_hook_u13.retention_reason requires an explanation for."""
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


def board_smoke(board):
    paths = sorted(ROOT.glob('window*/u13-A*/%s/runner/smoke/smoke-result.json' % board))
    return paths[-1]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check-only', action='store_true', help='rebuild in memory and compare with the files')
    args = ap.parse_args()
    records = u13_records()
    report = ps.report(Selected(records))
    # run_row collects pids in a set: its order follows the per-process string hash seed, so the same records give
    # different bytes (and report SHAs) run to run. Order processes by pid so the bound SHA is reproducible.
    for r in report['runs']:
        r['processes'] = dict(sorted(r['processes'].items(), key=lambda kv: int(kv[0])))
    body = json.dumps(report, indent=2) + '\n'
    any_pid = {}
    for r in report['runs']:
        log = Path(r['record']).parent / 'hilog.txt'
        if log.is_file():
            hits = failure_lines_any_pid(log.read_text(errors='replace').splitlines())
            if hits:
                any_pid[r['record']] = hits
    if report['error_count'] or any_pid:
        raise SystemExit('U13 failure-class probe line present: %d by pid filter, %d records by any-pid scan'
                         % (report['error_count'], len(any_pid)))
    rows = []
    for run, pid in issues(report):
        reason, evidence = classify(run, pid)
        rows.append(dict(record=run['record'], key=run['key'], pid=pid, line_sha256='unknown', line_number=None,
                         reason=reason, evidence=str(evidence), evidence_sha256=sha(evidence)))
    auth = json.loads(AUTH.read_text())
    reference = json.loads(REFERENCE.read_text())
    bundles = {}
    for name, serial in BOARDS.items():
        b = auth['per_board'][serial]['bundle_sha256']
        bundles.setdefault(b, []).append(name)
    report_sha = hashlib.sha256(body.encode()).hexdigest()
    outputs = {'selftest-u13-stage-a.json': body}
    checks = {}
    for bundle, boards in bundles.items():
        tag = 'common' if len(boards) > 1 else boards[0]
        comp = dict(bundle_sha256=bundle, native_manifest_sha256=auth['native_manifest_sha256'])
        expl = dict(schema='outer-selftest-explanations/v1', approved_by='outer(claude)', approved_at=SIGNED_AT,
                    boards=boards, report_sha256=report_sha, **comp, explanations=rows)
        expl_name = 'selftest-explanations-%s.json' % tag
        expl_body = json.dumps(expl, indent=1, ensure_ascii=False) + '\n'
        decision = json.loads((HERE / ('outer-stage-a-%s.json' % tag)).read_text())
        gate = decision['process_selftest_gate']
        gate.update(report_sha256=report_sha, measured_records=[r['record'] for r in report['runs']],
                    explanations_sha256=hashlib.sha256(expl_body.encode()).hexdigest())
        outputs[expl_name] = expl_body
        outputs['outer-stage-a-%s.json' % tag] = json.dumps(decision, indent=1, ensure_ascii=False) + '\n'
        checks[tag] = dict(boards=boards, decision=decision, comp=comp, expl_name=expl_name)
    if args.check_only:
        stale = [n for n, b in outputs.items() if not (HERE / n).is_file() or (HERE / n).read_text() != b]
        if stale:
            raise SystemExit('stale: ' + ', '.join(stale))
    else:
        for n, b in outputs.items():
            (HERE / n).write_text(b)
    result = {}
    for tag, c in checks.items():
        for board in c['boards']:
            smoke = json.loads(board_smoke(board).read_text())
            reason = hook.retention_reason(c['decision'], c['comp'], reference, smoke,
                                           HERE / 'selftest-u13-stage-a.json', HERE / c['expl_name'])
            result[board] = reason
    summary = dict(records=len(records), PASS=sum(r['status'] == 'PASS' for r in report['runs']),
                   unknown=report['unknown_runs'], REJECT=sum(r['status'] == 'REJECT' for r in report['runs']),
                   failure_lines_any_pid=0, explanations=len(rows), report_sha256=report_sha,
                   excluded={k: len(v) for k, v in excluded().items()}, retention_reason=result)
    print(json.dumps(summary, indent=1))
    return 0 if all(v is None for v in result.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
