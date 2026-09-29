#!/usr/bin/env python3
"""B7 (#54) acceptance checks over results.json + committed evidence (raw runs are not needed).

  verify.py first_cause | wall_crossed | lit | no_regression | blocked
"""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / 'results.json').read_text())
KEYS = ['opencamera', 'fd-android', 'fd-k9', 'fd-libre', 'fd-saber', 'fd-catima', 'fd-fennec_fdroid']


def fail(msg):
    print('FAIL:', msg); sys.exit(1)


def excerpt_has(key, lines):
    text = (HERE / 'evidence' / (key + '.txt')).read_text()
    return all(f'{l["line"]}: {l["text"]}' in text for l in lines)


def first_cause():
    for key in KEYS:
        fc = R['apps'][key]['first_cause']
        if not fc['lines'] or not fc['file'].startswith('runs/') or len(fc['sha256']) != 64:
            fail(key + ' has no first-cause line with a pinned source file')
        if not excerpt_has(key, fc['lines']):
            fail(key + ' first-cause line missing from evidence excerpt')
    print('first_cause: 7/7 apps have an original line + file + sha256, mirrored in evidence/')


def wall_crossed():
    crossed = [k for k in KEYS if R['apps'][k].get('wall') == 'crossed']
    for key in crossed:
        after = R['apps'][key]['after_fix']
        if after['original_error_count'] != 0 or not after.get('positive_marker') or not after['next_stage']:
            fail(key + ' marked crossed without zero original errors + positive marker + next stage')
        if not excerpt_has(key, after['positive_marker'] + after['next_stage']):
            fail(key + ' after-fix lines missing from evidence excerpt')
    classes = {('user-service' if k in ('fd-catima', 'fd-fennec_fdroid') else 'native-library-dir') for k in crossed}
    if not crossed:
        fail('no wall crossed')
    log = (HERE / 'evidence/installer/host-test-run.log').read_text()
    if 'class=DECLARED_XML_ONLY' not in log or log.count('refusing template placeholder') != 2:
        fail('installer host test does not show the XML-only placeholder with both tamper refusals kept')
    print('wall_crossed: %s crossed (%s); installer XML-only placeholder + 2 tamper refusals'
          % (', '.join(crossed), ', '.join(sorted(classes))))


def lit():
    if not R['lit_candidates']:
        fail('no app survived past its B7 wall with its own window; nothing for the outer loop to read')
    print('lit: candidates pending outer review:', R['lit_candidates'])


def no_regression():
    hw = R['no_regression']['helloworld']
    for shot in (hw['with_both_fixes'], hw['installer_only_no_jar_overlay']):
        p = HERE / shot['path']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != shot['sha256']:
            fail('HelloWorld screenshot missing or changed: ' + shot['path'])
    if not hw['observed_pids']:
        fail('HelloWorld process not alive at the final capture')
    if not R['no_regression']['zigzag']['launched']:
        fail('ZigZag not launched on 5cd: ' + R['no_regression']['zigzag']['reason'][:160])
    print('no_regression: HelloWorld and ZigZag screenshots pending outer review')


def blocked():
    blocked = [k for k in KEYS if R['apps'][k].get('wall') == 'blocked']
    for key in blocked:
        rec = R['apps'][key]
        if len(rec.get('blocked_reason', '')) < 80 or not rec.get('fix_site') or rec.get('lit'):
            fail(key + ' blocked without a reason, fix site, or is counted as lit')
    if set(blocked) | {k for k in KEYS if R['apps'][k].get('wall') == 'crossed'} != set(KEYS):
        fail('some app is neither crossed nor blocked')
    print('blocked: %s carry blocked_reason + fix_site, none counted as lit' % ', '.join(blocked))


{'first_cause': first_cause, 'wall_crossed': wall_crossed, 'lit': lit,
 'no_regression': no_regression, 'blocked': blocked}[sys.argv[1]]()
