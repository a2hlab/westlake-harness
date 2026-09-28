"""Production admission and attempt selection. Missing review never grants admission."""
import hashlib
import json
from pathlib import Path

CONTROLS = 'wikipedia termux ooniprobe antennapod aegis fd-AppManager fd-auxio fd-com-amaze-filemanager fd-com-kunzisoft-keepass-libre fd-droidify fd-fitness fd-netguard fd-noice'.split()


def image_valid(row, path):
    shot = row.get('observations', {}).get('shot', {})
    path = Path(path)
    return (shot.get('status') == 'ok' and shot.get('mtime', -1) >= row['launch_epoch']
            and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == shot.get('sha256'))


def hashes_match(before, after):
    return (bool(before.get('passed') and after.get('passed')) and bool(before.get('actual'))
            and before.get('actual') == after.get('actual')
            and before.get('actual') == before.get('expected')
            and after.get('actual') == after.get('expected'))


def admit(rows, reviews, before, after, image_dir):
    reasons = []
    if not hashes_match(before, after):
        reasons.append('deployment-hashes-differ-or-unverified')
    serial = before.get('serial')
    run = before.get('run_id')
    for key in CONTROLS + ['markor']:
        row = rows.get(key, {})
        signature = next((r for r in reviews if r.get('key') == key and r.get('serial') == serial and r.get('run_id') == run), {})
        required = 'not-lit' if key == 'markor' else 'lit'
        if (not row or row.get('status') != 'completed' or row.get('serial') != serial or row.get('run_id') != run
                or not image_valid(row, Path(image_dir) / (key + '.jpeg'))):
            reasons.append(key + ':missing-current-shot')
        if (not signature.get('reviewer') or not signature.get('criterion') or signature.get('verdict') != required
                or signature.get('sha256') != row.get('observations', {}).get('shot', {}).get('sha256')):
            reasons.append(key + ':missing-or-failing-review')
    return {'serial': serial, 'run_id': run, 'eligible': not reasons,
            'state': 'accepted' if not reasons else 'base_mismatch', 'reasons': reasons}


def select_attempts(manifest, attempts, admitted_serials):
    effective, rejected = [], []
    for app in manifest:
        candidates = []
        for row in attempts:
            if row.get('key') != app['key']:
                continue
            identity_ok = all(row.get(k) == app[k] for k in ('package', 'apk_sha256', 'launch_activity'))
            if (row.get('serial') in admitted_serials and row.get('status') == 'completed' and identity_ok
                    and not row.get('invalidated') and row.get('base_valid') is not False):
                candidates.append(row)
            else:
                rejected.append(row)
        if candidates:
            candidates.sort(key=lambda r: (r.get('finish_epoch', 0), r['run_id'], r['serial']))
            effective.append(candidates[-1])
            rejected.extend(candidates[:-1])
    return {'effective': effective, 'attempts': attempts, 'rejected_count': len(rejected),
            'pending_keys': [a['key'] for a in manifest if a['key'] not in {r['key'] for r in effective}]}


def observations_complete(rows, manifest):
    allowed = {a['key'] for a in manifest}
    valid = [r for r in rows if r.get('key') in allowed and r.get('candidate_blocker', {}).get('class') != 'capture-failed'
             and r.get('candidate_blocker', {}).get('source') and r.get('candidate_blocker', {}).get('evidence')]
    return len({r['key'] for r in valid}) >= 39


def load_admission(run_dir, serial, reviews):
    root = Path(run_dir) / serial
    if (root / 'invalidated.json').exists():
        return {'serial': serial, 'eligible': False, 'state': 'base_mismatch',
                'reasons': [json.loads((root / 'invalidated.json').read_text())['reason']]}
    rows = {p.parent.name: json.loads(p.read_text()) for p in root.glob('*/triage.json')}
    before_path = root / 'base-audit/before.json'
    after_path = root / 'base-audit/after.json'
    before = json.loads(before_path.read_text()) if before_path.exists() else {'serial': serial, 'run_id': Path(run_dir).name}
    after = json.loads(after_path.read_text()) if after_path.exists() else {}
    return admit(rows, reviews, before, after, root)


def pure_jvm_complete(rows):
    keys = 'markor fd-etar fd-uhabits fd-wifianalyzer fd-libretube opencamera fd-api'.split()
    by_key = {r['key']: r for r in rows}
    for key in keys:
        if key not in by_key:
            return False
        row = by_key[key]
        stacks = row.get('observations', {}).get('stacks', [])
        if len(stacks) != 2:
            return False
        if all(s.get('reason') == 'child-exited' for s in stacks):
            continue
        if any(s.get('pid') != row.get('child_pid') or s.get('main', {}).get('status') != 'ok' for s in stacks):
            return False
        if stacks[1]['sent_epoch'] - stacks[0]['sent_epoch'] < 5:
            return False
        if all(s['main']['idle'] for s in stacks) and row['candidate_blocker']['class'] == 'main-thread-blocked':
            return False
    return True
