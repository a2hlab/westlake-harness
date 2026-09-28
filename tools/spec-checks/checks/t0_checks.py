"""Contract checks call production code; board evidence and offline negatives are separate."""
import copy
import hashlib
import json
import sys
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / 'benchmark/2026-09-27-app-breadth-sweep/scripts'
sys.path.insert(0, str(SCRIPTS))
import t0_collect as collector
import t0_capture as capture
import t0_evidence as evidence
import t0_review as review
import t0_batch

DATA = ROOT / 'benchmark/2026-09-28-blocker-triage'
RUN = DATA / 'runs/cx10-controls-20260928-1648'
SERIAL = '5ea34a4500000000000000001123012c'
WIKI = RUN / SERIAL / 'wikipedia'
MARKOR = DATA / 'runs/cx10-20260928-1636' / SERIAL / 'markor'
MANIFEST = json.loads((DATA / 'manifest.json').read_text())


def hilog():
    # Minimal synthetic transport input: real child-PID field format, no claim of a real crash.
    raw = '\n'.join(['100.500 42 42 E APP: Error relocating libdemo.so: symbol not found',
                     '100.600 43 43 F APP: Fatal signal 11',
                     '100.700 42 42 E HDC_LOG: ExecuteCommand Error relocating libdemo.so',
                     '99.500 42 42 E APP: Fatal signal 11'])
    assert collector.filter_hilog(raw, 42, 100, 101) == raw.splitlines()[0] + '\n'


def exited():
    class Exited:
        def shell(self, command, **kwargs):
            assert command == 'test -d /proc/16771', 'must not signal an exited child'
            return 1, ''
    with tempfile.TemporaryDirectory() as tmp:
        r = capture.stack_capture(Exited(), 16771, '/unused', Path(tmp), 0,
                                  collector.stack_sections, evidence.main_stack)
        assert r == {'status': 'capture-failed', 'reason': 'child-exited', 'pid': 16771}
    row = json.loads((MARKOR / 'triage.json').read_text())
    assert all(x['reason'] == 'child-exited' for x in row['observations']['stacks'])


def stderr():
    row = json.loads((MARKOR / 'triage.json').read_text())
    path = capture.stderr_path(row['runtime'], row['child_pid'])
    assert path == row['observations']['stderr']['path']
    payload = (MARKOR / 'stderr-evidence.txt').read_text()
    files = {path: payload + '\nTOUCH21-POLL synthetic-noise\n', path.replace('16771', '16770'): 'OLD'}
    with tempfile.TemporaryDirectory() as tmp:
        b = collector.Board(Path(tmp))
        def shell(command, **kwargs):
            assert path in command
            return (0, files[path]) if path in files else (44, '')
        b.shell = shell
        meta, raw = b.read(path, Path(tmp) / 'read.log')
        assert meta['status'] == 'ok' and 'OLD' not in raw
        assert 'TOUCH21-POLL' not in (Path(tmp) / 'read.log.filtered').read_text()
        files[path] = ''
        assert b.read(path, Path(tmp) / 'empty.log')[0]['status'] == 'empty'
        del files[path]
        assert b.read(path, Path(tmp) / 'missing.log')[0]['status'] == 'missing'


def stale():
    row = json.loads((WIKI / 'triage.json').read_text())
    image = WIKI.parent / 'wikipedia.jpeg'
    assert review.image_valid(row, image)
    assert not capture.fresh_snapshot(1, row['launch_epoch'] + 1, 1024, row['launch_epoch'])
    assert not capture.fresh_snapshot(0, row['launch_epoch'] - 1, 1024, row['launch_epoch'])
    damaged = copy.deepcopy(row)
    damaged['observations']['shot']['status'] = 'failed'
    assert not review.image_valid(damaged, image)


def locks():
    for rc, owner in [(75, ''), (0, 'oc-t0 123 now\n')]:
        calls = []
        def transport(argv, **kw):
            calls.append(argv)
            if argv[0] == 'mac':
                return subprocess.CompletedProcess(argv, rc, owner, '')
            if argv[1:] == ['list', 'targets']:
                return subprocess.CompletedProcess(argv, 0, SERIAL + '\n', '')
            return subprocess.CompletedProcess(argv, 0, b'\n__T0_RC__0\n', b'')
        with tempfile.TemporaryDirectory() as tmp, patch.object(collector.subprocess, 'run', transport):
            try:
                collector.Board(Path(tmp)).shell('mkdir /data/local/tmp/synthetic-lock-test')
            except RuntimeError:
                pass
            assert len(calls) == 1, 'production Board.shell reached HDC despite lock refusal'


def detach():
    calls = []
    def transport(argv, **kw):
        calls.append(argv)
        if argv[0] == 'mac':
            return subprocess.CompletedProcess(argv, 0, 'cx-t0 123 now\n', '')
        if argv[1:] == ['list', 'targets']:
            return subprocess.CompletedProcess(argv, 0, '61b0657200000000000000000324012c\n', '')
        return subprocess.CompletedProcess(argv, 0, b'\n__T0_RC__0\n', b'')
    with tempfile.TemporaryDirectory() as tmp, patch.object(collector.subprocess, 'run', transport):
        base = Path(tmp)
        def attempt(key, run):
            out = base / key
            out.mkdir()
            state = 'completed'
            if key != 'first':
                try:
                    collector.Board(out).shell('mkdir /data/local/tmp/synthetic-detach-test')
                except RuntimeError:
                    state = 'interrupted'
            collector.save(out / 'triage.json', {'status': state})
            return 2 if state == 'interrupted' else 0
        with patch.object(collector, 'collect', attempt):
            assert t0_batch.run(['first', 'lost', 'remaining'], 'test', base) == 2
        assert json.loads((base / 'shard.json').read_text()) == {'first': 'completed', 'lost': 'interrupted', 'remaining': 'not-run'}
        assert all('shell' not in argv for argv in calls), 'write reached detached target'


def isolation():
    assert capture.isolated_root('/home/test', 'run1') == Path('/home/test/a2hlab/ws/out-appsweep-t0-run1')
    try:
        capture.isolated_root('/home/test', '../../app-inputs')
    except ValueError:
        pass
    else:
        raise AssertionError('path traversal accepted')
    # Recorded real copies also retain their source input hashes.
    for p in RUN.glob('*/*/input-hashes.json'):
        d = json.loads(p.read_text())
        assert d['before'] == d['after'], p
    audit = RUN / SERIAL / 'isolation-audit'
    before = json.loads((audit / 'before.json').read_text())
    after = json.loads((audit / 'after.json').read_text())
    assert before['files'] == after['files'] and all(before['files'].values())


def cleanup():
    row = json.loads((MARKOR / 'triage.json').read_text())
    assert evidence.cleanup_paths(row['runtime'], row['stage']) == [row['runtime'], row['stage']]
    rt = '/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bf' + '0' * 24
    st = '/data/local/tmp/a2hlab-app-c91d26bf' + '0' * 24
    try:
        evidence.cleanup_paths(rt, st)
    except ValueError:
        pass
    else:
        raise AssertionError('protected Toutiao paths accepted')
    receipt = json.loads((RUN / SERIAL / 'cleanup/cleanup.json').read_text())
    assert receipt['protected_paths_present'] and receipt['protected_listing_unchanged'] and receipt['protected_contents_unchanged']
    before = (RUN / SERIAL / 'cleanup/protected-hashes-before.txt').read_text().splitlines()
    after = (RUN / SERIAL / 'cleanup/protected-hashes-after.txt').read_text().splitlines()
    assert before and sorted(before) == sorted(after)


def exclude():
    # Feed real partial control rows with no signatures: never grant admission.
    rows = {p.parent.name: json.loads(p.read_text()) for p in (RUN / SERIAL).glob('*/triage.json')}
    audit = {'serial': SERIAL, 'run_id': 'cx10-controls-20260928-1648', 'passed': False}
    r = review.admit(rows, [], audit, audit, RUN / SERIAL)
    assert not r['eligible'] and r['state'] == 'base_mismatch'


def merge():
    row = evidence.interpret(MARKOR)
    app = next(a for a in MANIFEST['blocked'] if a['key'] == 'markor')
    newer = copy.deepcopy(row)
    newer['finish_epoch'] += 1
    newer['run_id'] += '-retry'
    r = review.select_attempts([app], [row, newer], [SERIAL])
    assert len(r['effective']) == 1 and r['effective'][0]['run_id'] == newer['run_id']
    assert len(r['attempts']) == 2
    assert not review.select_attempts([app], [row], [])['effective']
    effective = current()['effective_records']
    assert len(effective) == 43 and {r['key'] for r in effective} == {r['key'] for r in MANIFEST['blocked']}


def jvm():
    for name in ['quit0.stack.txt', 'quit1.stack.txt']:
        r = evidence.main_stack((WIKI / name).read_text())
        assert r['status'] == 'ok' and r['idle'] is True
    assert evidence.main_stack('no current stack')['status'] == 'capture-failed'


def current():
    import t0_summarize
    return t0_summarize.build()


def all_observations():
    rows = current()['effective_records']
    assert len(rows) == 43 and review.observations_complete(rows, MANIFEST['blocked'])
    assert not review.observations_complete(rows[:38], MANIFEST['blocked'])
    for row in rows:
        block = row['candidate_blocker']
        if block['class'] != 'capture-failed':
            source = DATA / row['evidence_dir'] / block['source']
            assert source.is_file() and block['evidence'] in source.read_text()


def all_jvm():
    jvm()
    rows = current()['effective_records']
    assert review.pure_jvm_complete(rows)
    assert not review.pure_jvm_complete([])


def controls():
    import t0_summarize
    state = current()
    assert any(a['eligible'] for a in state['admissions'])
    for a in state['admissions']:
        if a['eligible']:
            root = DATA / 'runs' / t0_summarize.CONTROL_RUNS[a['serial']] / a['serial']
            row = json.loads((root / 'wikipedia/triage.json').read_text())
            assert review.image_valid(row, root / 'wikipedia.jpeg')
            row['observations']['shot']['status'] = 'failed'
            assert not review.image_valid(row, root / 'wikipedia.jpeg')


CHECKS = {'t0_blocked_apps_have_observations': all_observations,
          't0_pure_jvm_apps_have_main_stack': all_jvm, 't0_lit_control_set_unchanged': controls,
          't0_hilog_keeps_own_pid_crash_only': hilog, 't0_stack_timeout_marked_capture_failed': exited,
          't0_stderr_located_by_pid': stderr, 't0_stale_screenshot_rejected': stale,
          't0_lock_contention_no_writes': locks, 't0_midrun_detach_stops_shard': detach,
          't0_isolated_out_root': isolation, 't0_cleanup_exempts_toutiao_dirs': cleanup,
          't0_board_without_full_lit_control_excluded': exclude,
          't0_merged_triage_one_record_per_app': merge, 'main_idle_regression': jvm}
MUTANTS = {
 't0_blocked_apps_have_observations': (review, 'observations_complete', lambda *a: True),
 't0_pure_jvm_apps_have_main_stack': (review, 'pure_jvm_complete', lambda *a: True),
 't0_lit_control_set_unchanged': (review, 'image_valid', lambda *a: True),
 't0_hilog_keeps_own_pid_crash_only': (collector, 'filter_hilog', lambda raw, *a: raw),
 't0_stack_timeout_marked_capture_failed': (capture, 'stack_capture', lambda *a, **kw: {'status': 'ok'}),
 't0_stderr_located_by_pid': (capture, 'stderr_path', lambda rt, pid: f'{rt}/private-tmp/adapter_child_{pid-1}.stderr'),
 't0_stale_screenshot_rejected': (capture, 'fresh_snapshot', lambda *a: True),
 't0_lock_contention_no_writes': (capture, 'lock_owner_valid', lambda *a: True),
 't0_midrun_detach_stops_shard': (capture, 'attached', lambda *a: True),
 't0_isolated_out_root': (capture, 'isolated_root', lambda home, run: Path(home) / 'a2hlab/ws' / ('out-appsweep-t0-' + run)),
 't0_cleanup_exempts_toutiao_dirs': (evidence, 'cleanup_paths', lambda rt, st: [rt, st]),
 't0_board_without_full_lit_control_excluded': (review, 'admit', lambda *a: {'eligible': True, 'state': 'accepted'}),
 't0_merged_triage_one_record_per_app': (review, 'select_attempts', lambda m, a, s: {'effective': a, 'attempts': a}),
 'main_idle_regression': (evidence, 'main_stack', lambda x: {'status': 'ok', 'idle': False}),
}


def run(name, negatives=True):
    CHECKS[name]()
    if negatives:
        module, attr, fn = MUTANTS[name]
        with patch.object(module, attr, fn):
            try:
                CHECKS[name]()
            except AssertionError:
                print('DETECTED production logic mutation:', name, flush=True)
            else:
                raise AssertionError('negative control escaped: ' + name)
    print('PASS', name, 'offline regression + captured evidence', flush=True)


if __name__ == '__main__':
    if sys.argv[1] == 'all-offline':
        for name in CHECKS:
            if name not in ('t0_blocked_apps_have_observations', 't0_pure_jvm_apps_have_main_stack', 't0_lit_control_set_unchanged', 't0_merged_triage_one_record_per_app'):
                run(name)
    elif sys.argv[1] == 't0_negative_controls_fail':
        for name in ('t0_hilog_keeps_own_pid_crash_only', 't0_stale_screenshot_rejected'):
            run(name)
    else:
        run(sys.argv[1])
