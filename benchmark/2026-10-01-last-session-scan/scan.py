"""Offline PID-bound session lookup inventory; never a screenshot classifier."""

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
import first_fatal

SCORES = ROOT / 'benchmark/2026-10-01-u7-scoring/formal-66/results.json'
PATTERNS = [
    ('create-begin', r'createSession: bundle=(\S+) ability=(\S+) name=([^,]+),'),
    ('create-success', r'createSession: success, sessionId=(\d+)'),
    ('last-session', r'\[IPC\] ENTER oh_wm_set_last_session_local session=(\d+)'),
    ('bbq-create', r'BBQ\.create name=(.+?) ptr=([0-9A-Fa-fx]+)'),
    ('update-null', r'BBQ\.update: getOhNativeWindow\(sessionId=(\d+)\) returned null'),
    ('update-ok', r'BBQ\.update: sessionId=(\d+) .*OHNativeWindow=([0-9A-Fa-fx]+)'),
    ('surface-ok', r'BBQ\.getSurface: returning Surface with mNativeObject=([0-9A-Fa-fx]+) \(sessionId=(\d+)\)'),
    ('surface-empty', r'BBQ\.getSurface: .*returning empty Surface'),
    ('lifecycle', r'arr=\[\d+,"([^"]+)","(RESUME_ACTIVITY|PAUSE_ACTIVITY|STOP_ACTIVITY|DESTROY_ACTIVITY)"'),
    ('start-activity', r'nativeStartAbility: bundle=(\S+), ability=([^,]+),'),
    ('focus-request', r'createSession: RequestFocusStatus\(persistentId=(\d+)\) OK'),
    ('unknown-session', r'getOhNativeWindow: unknown sessionId[= ]+(\d+)'),
    ('gl-valid-surface-iae', r'java\.lang\.IllegalArgumentException:.*(?:SurfaceView|SurfaceHolder).*valid Surface'),
]
PATTERNS = [(kind, re.compile(pattern)) for kind, pattern in PATTERNS]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(events, pids, cutoff):
    selected = []
    native_messages = {(entry['pid'], entry['tid'], entry['timestamp'], entry['message']) for entry in events if '[stderr]' not in entry['message']}
    for event in events:
        if event['pid'] not in pids or (cutoff and event['timestamp'] > cutoff):
            continue
        if not first_fatal.classify.is_execution(event):
            continue
        if '[stderr]' in event['message']:
            canonical = event['message'].split('[stderr]', 1)[1].strip()
            if (event['pid'], event['tid'], event['timestamp'], canonical) in native_messages:
                continue
        for kind, pattern in PATTERNS:
            match = pattern.search(event['message'])
            if match:
                if kind == 'gl-valid-surface-iae' and not event['tag'].endswith('/GLSurfaceView'):
                    continue
                selected.append(dict(kind=kind, groups=list(match.groups()), **{key:event[key] for key in ['line', 'timestamp', 'pid', 'tid', 'message']}))
                break
    return selected


def collect(run_root):
    score = json.loads(SCORES.read_text())
    expected = {}
    for relative in ['evidence/5ea-prepared.json', 'signed-44/5cd-prepared.json', 'formal-66/61b-prepared.json']:
        body = json.loads((SCORES.parent.parent / relative).read_text())
        expected.update({row['key']:row for row in body['rows']})
    rows = []
    for shard, group in score['shards'].items():
        for scored in group['rows']:
            folder = (run_root / scored['record']).parent
            record, events, pids, _, _, pins = first_fatal.load_run(folder)
            previous = expected[scored['key']]
            for key in ['record_sha256', 'hilog_sha256']:
                if pins[key] != previous[key]:
                    raise ValueError('raw identity drift: ' + scored['key'] + '/' + key)
            if sorted(pids) != previous['target_pids']:
                raise ValueError('PID identity drift')
            shot = next((item for item in record.get('screenshots', []) if item.get('captured') and item.get('scheduled_seconds') == 20), None)
            if shot and sha(folder / 't20.jpeg') != scored['t20_sha256']:
                raise ValueError('signed screenshot bytes changed')
            cutoff = datetime.fromtimestamp(int(shot['remote_stat'].split()[1]), timezone(timedelta(hours=8))).strftime('%m-%d %H:%M:%S') + '.999' if shot else None
            selected = extract(events, pids, cutoff) if pids and cutoff else []
            rows.append(dict(key=scored['key'], shard=shard, visual=scored['visual'], authority=scored['authority'],
                             record=scored['record'], hilog=str(Path(scored['record']).with_name('hilog.txt')), pids=sorted(pids),
                             record_sha256=pins['record_sha256'], hilog_sha256=pins['hilog_sha256'], t20_sha256=scored['t20_sha256'],
                             binding_lines=pins['binding_lines'], cutoff=cutoff, log_complete=previous['log_complete'],
                             status=record['status'], input_error=record.get('error'), events=selected))
    if len(rows) != 66 or len({row['key'] for row in rows}) != 66:
        raise ValueError('need exact 66-key cohort')
    return dict(schema_version=1, source='WORKSPACES/westlake-harness-wiki/benchmark/2026-10-01-u7-sweep',
                signed_scores_sha256=sha(SCORES), first_fatal_sha256=sha(ROOT / 'scripts/lab/first_fatal.py'),
                criteria_sha256=sha(HERE / 'CRITERIA.md'), rows=sorted(rows, key=lambda row:row['key']))


def correlate(events):
    pending_session, pending_queue, latest_lookup, last = {}, {}, {}, {}
    sessions, queues, writes, lookups, surfaces, lifecycle, unknowns, exceptions = [], [], [], [], [], [], [], []
    for event in events:
        kind, groups = event['kind'], event['groups']
        thread = (event['pid'], event['tid'])
        if kind == 'create-begin':
            pending_session[thread] = event
        elif kind == 'create-success':
            begin = pending_session.pop(thread, None)
            name = begin['groups'][2].split('/', 1)[-1] if begin else None
            window_type = re.search(r'androidType=(\d+)', begin['message']) if begin else None
            sessions.append(dict(pid=event['pid'], session=int(groups[0]), activity=name, android_type=int(window_type.group(1)) if window_type else None, begin=begin, success=event))
        elif kind == 'last-session':
            last[event['pid']] = int(groups[0])
            writes.append(dict(session=int(groups[0]), **event))
        elif kind == 'bbq-create':
            activity = re.fullmatch(r'VRI\[(.+)\]', groups[0])
            queue = dict(pid=event['pid'], ptr=groups[1], name=groups[0], activity=activity.group(1) if activity else None,
                         create=event, session=None, association='unbound', updates=[], surfaces=[])
            queues.append(queue)
            pending_queue[thread] = queue
        elif kind in {'update-null', 'update-ok'}:
            session = int(groups[0])
            queue = pending_queue.pop(thread, None)
            if queue is not None:
                queue['session'] = session
                queue['association'] = 'same-PID/TID-next-update-provisional-no-queue-id-in-update'
            else:
                matches = [item for item in queues if item['pid'] == event['pid'] and item['session'] == session]
                queue = matches[0] if len(matches) == 1 else None
            matches = [item for item in sessions if item['pid'] == event['pid'] and item['session'] == session]
            activity = matches[0]['activity'] if len(matches) == 1 else None
            lookup = dict(event=event, session=session, last_session=last.get(event['pid']), non_last=last.get(event['pid']) != session if event['pid'] in last else None,
                          activity=activity, android_type=matches[0]['android_type'] if len(matches)==1 else None,
                          queue_ptr=queue['ptr'] if queue else None, queue_association=queue['association'] if queue else 'unknown', outcome=kind)
            lookups.append(lookup)
            latest_lookup[thread] = (lookup, queue)
            if queue is not None:
                queue['updates'].append(lookup)
        elif kind in {'surface-empty', 'surface-ok'}:
            match = re.search(r'sessionId=(\d+)', event['message'])
            session = int(match.group(1)) if match else None
            previous, queue = latest_lookup.get(thread, (None, None))
            bound = previous is not None and (session is None or session == previous['session'])
            surface = dict(event=event, explicit_session=session, session=session if session is not None else previous['session'] if bound else None,
                           preceding_lookup_line=previous['event']['line'] if bound else None, association='same-PID/TID-preceding-lookup-provisional' if bound else 'unknown')
            surfaces.append(surface)
            if bound and queue is not None:
                queue['surfaces'].append(surface)
        elif kind == 'lifecycle':
            lifecycle.append(event)
        elif kind == 'unknown-session':
            unknowns.append(dict(event=event, session=int(groups[0]), last_session=last.get(event['pid'])))
        elif kind == 'gl-valid-surface-iae':
            exceptions.append(event)
    for unknown in unknowns:
        matching = [entry for entry in sessions if entry['pid']==unknown['event']['pid'] and entry['session']==unknown['session']]
        session = matching[0] if len(matching)==1 else None
        unknown['activity'] = session['activity'] if session else None
        unknown['relative_to_create_success'] = ('before-success' if unknown['event']['line'] < session['success']['line'] else 'after-success') if session else 'no-matching-success'
        following = next((entry for entry in lookups if entry['session']==unknown['session'] and entry['event']['pid']==unknown['event']['pid'] and entry['event']['tid']==unknown['event']['tid'] and entry['event']['line']>unknown['event']['line']), None)
        unknown['next_same_pid_tid_session_bbq_update'] = dict(line=following['event']['line'], outcome=following['outcome']) if following else None
    return dict(create_session_count=len(sessions), distinct_session_count=len({(entry['pid'],entry['session']) for entry in sessions}),
                sessions=sessions, last_session_sequence=writes, queues=queues, lookups=lookups, surface_events=surfaces, lifecycle=lifecycle,
                null_count=sum(entry['outcome']=='update-null' for entry in lookups), empty_surface_count=sum(entry['event']['kind']=='surface-empty' for entry in surfaces),
                unknown_session_count=len(unknowns), unknown_sessions=unknowns, gl_valid_surface_iae_count=len(exceptions), gl_valid_surface_iae=exceptions)


def impact(row, foreground=None, background=None):
    nulls = [entry for entry in row['lookups'] if entry['outcome'] == 'update-null']
    if not row['pids'] or not row['cutoff'] or not row['log_complete']:
        return 'unknown-incomplete-evidence'
    if row['distinct_session_count'] == 0:
        return 'no-session-observed-not-a-negative'
    if row['distinct_session_count'] == 1:
        return 'single-session-null-counterexample' if nulls else 'single-session-not-exposed'
    if not nulls:
        return 'multi-session-no-null-observed'
    failed = {entry['activity'] for entry in nulls}
    if foreground and foreground in failed:
        return 'foreground-null-white-candidate'
    if background and None not in failed and failed <= set(background):
        return 'background-only-not-on-screen-blocker'
    return 'null-foreground-unknown'


def build(intake, authority):
    if intake['signed_scores_sha256'] != sha(SCORES) or intake['criteria_sha256'] != sha(HERE / 'CRITERIA.md'):
        raise ValueError('cohort or criteria drift')
    if intake['first_fatal_sha256'] != sha(ROOT / 'scripts/lab/first_fatal.py'):
        raise ValueError('PID binder drift')
    for quote in authority['quotes']:
        if hashlib.sha256(quote['text'].encode()).hexdigest() != quote['sha256']:
            raise ValueError('authority quote drift')
    rows = []
    for source in intake['rows']:
        if any(event['pid'] not in source['pids'] or (source['cutoff'] and event['timestamp'] > source['cutoff']) for event in source['events']):
            raise ValueError('event outside PID or time scope')
        row = dict(source, **correlate(source['events']))
        binding = authority.get('activity_bindings', {}).get(source['key'], {})
        row['foreground_authority'] = binding or 'unknown: resume/request-focus is not proof of screen ownership'
        row['impact'] = impact(row, binding.get('foreground'), binding.get('background'))
        rows.append(row)
    controls = [row['key'] for row in rows if row['visual']=='own-ui' and row['impact']=='single-session-not-exposed'][:3]
    if len(rows) != 66 or len({row['key'] for row in rows}) != 66 or len(controls) != 3:
        raise ValueError('missing cohort or negative controls')
    return dict(schema_version=1, signed_scores_sha256=intake['signed_scores_sha256'], criteria_sha256=intake['criteria_sha256'],
                source=intake['source'], negative_controls=controls, summary=dict(keys=66, signed_visuals=dict(Counter(row['visual'] for row in rows)),
                impacts=dict(Counter(row['impact'] for row in rows)), null_keys=[row['key'] for row in rows if row['null_count']],
                null_events=sum(row['null_count'] for row in rows), empty_surface_events=sum(row['empty_surface_count'] for row in rows),
                session_distribution=dict(Counter(str(row['distinct_session_count']) for row in rows)),
                null_non_last_events=sum(entry['non_last'] is True for row in rows for entry in row['lookups'] if entry['outcome']=='update-null'),
                unknown_session_events=sum(row['unknown_session_count'] for row in rows),
                unknown_session_keys=[row['key'] for row in rows if row['unknown_session_count']],
                unknown_session_timing=dict(Counter(entry['relative_to_create_success'] for row in rows for entry in row['unknown_sessions'])),
                unknown_session_then_last_equal=sum(entry['session']==entry['last_session'] for row in rows for entry in row['unknown_sessions']),
                unknown_session_next_bbq_update=dict(Counter((entry['next_same_pid_tid_session_bbq_update'] or {}).get('outcome','unobserved') for row in rows for entry in row['unknown_sessions'])),
                gl_valid_surface_iae_events=sum(row['gl_valid_surface_iae_count'] for row in rows),
                gl_valid_surface_iae_keys=[row['key'] for row in rows if row['gl_valid_surface_iae_count']],
                signed_bright_null_keys=[row['key'] for row in rows if row['visual']=='own-ui' and row['null_count']]), rows=rows)


def markdown(result):
    lines = ['# U7 last-session lookup impact', '', '## Corrected assumption', '',
             'A failed lookup is not itself a white-screen verdict. Only app-PID execution lines count; a later RESUME or focus request is not proof of which Activity owns the screenshot. Counts include pre-click initialization through signed t20. Session count means successful creations, not every createSession diagnostic.', '',
             'Criteria were written before the full scan in `CRITERIA.md`. All 66 signed first attempts are preserved; no screenshot category is recomputed. Queue links without explicit queue IDs are provisional and labeled. Null counts and last-session comparisons use explicit session IDs.', '',
             '## Summary', '', '```json', json.dumps(result['summary'], ensure_ascii=False, indent=2), '```', '',
             'Three signed-bright, one-session, zero-null controls: **' + ', '.join(result['negative_controls']) + '**.', '',
             '**Boundaries:** six signed-bright keys also have null lookup(s): a null is not sufficient for white. Their exact on-screen Activity is not independently bound by a bare RESUME/request-focus event, so background-only attribution stays unknown unless an Activity-level sign-off exists. Anki has two sessions with the same DeckPicker name (androidType 2 then 1); do not call this two Activities. AppManager has one successful session and no null in this sweep, despite its later A-class classification. No-null and zero-session cases are not universal proof of native-window correctness.', '',
             '## All 66 keys', '', '| Key | Sessions / unique | Last-session sequence | Null / empty | Unknown session | GL valid-Surface IAE | Null Activity (session) | Signed t20 | Impact |', '|---|---:|---|---:|---:|---:|---|---|---|']
    for row in result['rows']:
        activities = sorted({str(entry['activity']) + ' (' + str(entry['session']) + ')' for entry in row['lookups'] if entry['outcome']=='update-null'})
        lines.append('| ' + row['key'] + ' | ' + str(row['create_session_count']) + '/' + str(row['distinct_session_count']) + ' | ' + ' → '.join(str(entry['session']) for entry in row['last_session_sequence']) + ' | ' + str(row['null_count']) + '/' + str(row['empty_surface_count']) + ' | ' + str(row['unknown_session_count']) + ' | ' + str(row['gl_valid_surface_iae_count']) + ' | ' + ('; '.join(activities) or 'none observed') + ' | ' + row['visual'] + ' | ' + row['impact'] + ' |')
    lines += ['', '## Extended signature scope', '', 'Unknown-session diagnostics and BBQ null lookups are separate event families. Each unknown-session event retains its Activity, then-last session, timing relative to successful creation, and next same-PID/TID/session BBQ update (ordered correlation, not proof of a fallback implementation). A zero IAE count does not clear other GL/native failures. Signed-bright apps with these warnings remain bright; single-session controls prove absence of BBQ null, not absence of all warnings.', '',
              '**GLSurfaceView valid-Surface IAE appears only in fd-app and fd-shatteredpixeldungeon, one each.** Mindustry and x have neither added signature. PPSSPP has two unknown-session messages, Mobile four, but neither has this IAE. All three single-session bright controls themselves have two unknown-session messages and successful BBQ updates: the broader warning cannot be used as the white-screen rule.', '']
    lines += ['', '## Failure and negative-control evidence', '']
    for row in result['rows']:
        if not row['null_count'] and not row['unknown_session_count'] and not row['gl_valid_surface_iae_count'] and row['key'] not in result['negative_controls']:
            continue
        lines += ['### ' + row['key'], '', 'PID ' + str(row['pids']) + '; signed **' + row['visual'] + '** at `' + row['authority'] + '`; hilog SHA `' + row['hilog_sha256'] + '`.', '']
        for event in row['events']:
            if event['kind'] in {'create-begin','create-success','last-session','bbq-create','update-null','update-ok','surface-empty','surface-ok','unknown-session','gl-valid-surface-iae'}:
                lines.append('- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/' + row['hilog'] + ':' + str(event['line']) + '` — ' + event['message'])
        lines.append('')
    lines += ['## Replay', '', '```sh', 'python3 benchmark/2026-10-01-last-session-scan/scan.py collect > /tmp/last-session-intake.json', 'python3 benchmark/2026-10-01-last-session-scan/scan.py report > /tmp/last-session-results.json', 'python3 benchmark/2026-10-01-last-session-scan/test_scan.py', '```', '', 'See `results.json` for every queue/session/event and evidence pin, `authority.json` for Activity-level sign-offs, and `validation.json` plus `landing-paths.txt` for scoped delivery. No runtime change, board command or frozen score edit.', '']
    return '\n'.join(lines)


def load():
    import base64
    import gzip
    evidence = json.loads(gzip.decompress(base64.b64decode((HERE / 'evidence.json.gz.b64').read_bytes())))
    return build(evidence, json.loads((HERE / 'authority.json').read_text()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['collect','report','markdown'])
    parser.add_argument('--run-root', type=Path, default=ROOT.parent / 'westlake-harness-wiki/benchmark/2026-10-01-u7-sweep')
    args = parser.parse_args()
    result = collect(args.run_root) if args.mode == 'collect' else load()
    print(markdown(result) if args.mode == 'markdown' else json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2), end='' if args.mode=='markdown' else '\n')
