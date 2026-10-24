"""Offline reproduction only; no subprocesses or device operations."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE.parent
ROOT = P.parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def pin(path):
    return {'path': str(path.relative_to(P)), 'bytes': path.stat().st_size,
            'sha256': sha(path)}

def compute():
    full = P / '.private/7013-full-log-01'
    body = full / '7013.stderr'
    expected = '9940ebdcb209b1c63361064fc6e91e2d293ff65ec4ff049cbd130bafa8ab14b2'
    assert sha(body) == expected and body.stat().st_size == 28216090
    for label in ('before', 'after'):
        text = (full / label / 'stdout').read_text()
        assert '66352|574530|0|0|644|28216090|1792868775' in text
        assert expected in text and text.rstrip().endswith('T136_LOG_REMOTE_RC:0')
    for label in ('before', 'recv', 'after'):
        receipt = read(full / label / 'receipt.json')
        assert receipt['local_rc'] == 0
        for stream in ('stdout', 'stderr'):
            assert sha(full / label / stream) == receipt[stream + '_sha256']
        assert not (full / label / 'stderr').read_bytes()
    lines = body.read_bytes().splitlines(keepends=True)
    markers = []
    offset = 0
    for number, line in enumerate(lines, 1):
        if line.startswith(b'[HOST-SESSION]'):
            markers.append({'line': number, 'byte_offset': offset,
                            'text': line.decode().rstrip()})
        offset += len(line)
    assert [m['line'] for m in markers] == [257407, 257433]
    assert all(m['byte_offset'] > 4194304 for m in markers)
    build = read(ROOT / 'candidate-build-02/results.json')
    source_pins = []
    for name in ('session_recovery.h', 'session_recovery.cpp', 'wmc_recovery_impl.inc'):
        source = ROOT / 'session-recovery/candidate' / name
        assert sha(source) == build['source_pins']['candidate/' + name]
        source_pins.append({'path': str(source.relative_to(ROOT)), 'sha256': sha(source)})
    header = (ROOT / 'session-recovery/candidate/session_recovery.h').read_text().splitlines()
    assert header[87] == 'enum class Outcome { Idle, Throttled, InFlight, Rejected, Failed, StoppedUnknown, Committed };'
    success = P / '.private/execute-20261025-025813-43e2a3'
    bindings = {}
    for phase in ('firstopen-s30', 'recreated-s5'):
        f = success / (phase + '-binding.json'); b = read(f)
        assert b['object']['sha256'] == build['target_snapshot02_artifact']
        assert any(p['pid'] == 7013 and p['birth'] == 12014 for p in b['identity']['processes'])
        bindings[phase] = {'receipt': pin(f), 'identity': b['identity'], 'object': b['object']}
    run = P / '.private/execute-20261025-040803-e6f12a'
    result = read(run / 'result.json')
    assert result['released'] and result['power_final']['base'] == 30000 and result['power_final']['override'] == 10000
    receipts = sorted(run.glob('*/receipt.json'))
    click = next(f for f in receipts if f.parent.name.endswith('-ordinary-icon-once'))
    click_r = read(click)
    polls = sorted(run.glob('*ordinary-presence*/receipt.json'))
    idx = next(i for i, f in enumerate(polls) if 'PROC:25535:' in (f.parent / 'stdout').read_text())
    last_absent, first_present = polls[idx-1], polls[idx]
    times = {}
    for name, f in [('last_absent', last_absent), ('first_present', first_present)]:
        r = read(f)
        times[name] = {'receipt': pin(f), 'start_utc': r['start_utc'], 'end_utc': r['end_utc'],
                       'seconds_from_click_start': r['start_monotonic'] - click_r['start_monotonic'],
                       'seconds_from_click_end': r['end_monotonic'] - click_r['end_monotonic']}
    reviews = {}
    for label in ('ordinary-s40', 'ordinary-s60', 'ordinary-final'):
        review = read(run / (label + '.review.json'))
        image = run / (label + '.jpeg')
        assert sha(image) == review['image_sha256']
        assert sha(run / (label + '.layout.json')) == review['layout_sha256']
        reviews[label] = {'review': pin(run / (label + '.review.json')), 'image': pin(image),
                          'verdict': review['verdict'], 'reviewed_by': review['reviewed_by']}
    capture = next(f for f in receipts if f.parent.name.endswith('-ordinary-s60-capture'))
    capture_r = read(capture)
    counts = {}
    for name, token in [('icon_click', 'ordinary-icon-once'), ('feed_swipe', 'ordinary-feed-swipe'), ('content_click', 'ordinary-content-click')]:
        counts[name] = sum(f.parent.name.endswith('-' + token) and read(f)['local_rc'] == 0 and
                          (f.parent / 'stdout').read_text().rstrip().endswith(':0') for f in receipts)
    child_tuples = {(p['pid'], p['birth']) for x in result['identities'] for p in x['identity']['processes'] if p['name'] == 'com.ss.android.article.news'}
    return {
        'status': 'ordinary_evidence_verified_not_complete_t3',
        'full_log': pin(body), 'line_count': len(lines), 'markers': markers,
        'notify_destroy_literal_count': sum(b'NotifyDestroy' in x for x in lines),
        'safe_context': [{'line': n, 'text': lines[n-1].decode().rstrip()} for n in (257406,257407,257432,257433,257436,257444,257445,257446)],
        'source_pins': source_pins, 'enum_line': 88, 'outcome_6': 'Committed',
        'build_receipt': {'path': 'candidate-build-02/results.json', 'sha256': sha(ROOT / 'candidate-build-02/results.json')},
        'historical_actual_mapping': bindings,
        'interpretation': 'Both logical sessions logged successful recovery publication. This is not recreated touch verification or a complete t3 pass.',
        'ordinary_baseline': {
            'run': run.name, 'original_result': pin(run / 'result.json'),
            'worker_combined_feed_and_touch_boolean': result['feed_observed_and_verified'],
            'visible_feed_external_review': True, 'touch_verified_in_this_run': False,
            'click_receipt': pin(click), 'click_start_utc': click_r['start_utc'], 'click_end_utc': click_r['end_utc'],
            'child_observation_bracket': times, 'reviews': reviews,
            's60_capture_start_utc': capture_r['start_utc'], 's60_capture_end_utc': capture_r['end_utc'],
            's60_capture_seconds_after_click_start': capture_r['start_monotonic'] - click_r['start_monotonic'],
            'power_final': result['power_final'], 'released': result['released'],
            'facts': {'screenshots_received': len(list(run.glob('*.jpeg'))), 'command_receipts': len(receipts),
                      'sample_images': sorted(f.stem for f in run.glob('ordinary-s*.jpeg') if f.stem[10:].isdigit()),
                      'observed_article_pid_birth_tuples': [list(x) for x in sorted(child_tuples)], **counts}},
        'limits': ['Historical PID7013 log collected under later boot70b; not a current-boot live log.',
                   'Embedded PID/time, unchanged historical file metadata and historical maps supply correlation; filename alone does not prove birth.',
                   'HOST-SESSION lines have no wall-clock timestamp; adjacent records do not give an exact commit wall time.',
                   'Zero NotifyDestroy text does not establish absence of the call.',
                   'Private full log and images are not included in the public package.']}

if __name__ == '__main__':
    import sys
    computed = compute()
    if '--write' in sys.argv:
        (HERE / 'results.json').write_text(json.dumps(computed, indent=2) + '\n')
    else:
        assert computed == read(HERE / 'results.json')
    print('ordinary evidence checks passed')
