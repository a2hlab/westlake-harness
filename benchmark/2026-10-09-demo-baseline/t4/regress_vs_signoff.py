#!/usr/bin/env python3
"""Offline byte comparison plus conservative screenshot triage, never a UI verdict."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
REPO = BASE.parents[1]
WS = Path(os.environ.get('WORKSPACES', REPO.parent))
sys.path.insert(0, str(REPO / 'scripts/lab'))
import run_facts


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text())


def expand(s):
    return Path(os.path.expanduser(os.path.expandvars(str(s).replace('$WORKSPACES', str(WS)))))


def portable(p):
    return str(p).replace(str(WS), '$WORKSPACES')


def last_capture(record_path):
    """Use the final scheduled slot, never hide missing t20 with an earlier t5."""
    p = Path(record_path)
    r = read(p)
    shots = r.get('screenshots') or []
    timed = [s for s in shots if isinstance(s.get('scheduled_seconds'), (float, int))]
    if not timed:
        return None, None, None
    s = max(timed, key=lambda x: x['scheduled_seconds'])
    t = float(s['scheduled_seconds'])
    tag = 't' + str(t).removesuffix('.0')
    if not s.get('captured'):
        return tag, None, 'last scheduled capture not captured'
    image = p.parent / Path(s.get('path') or (tag + '.jpeg')).name
    if not image.is_file():
        image = expand(s.get('path') or str(image))
    if not image.is_file():
        return tag, None, 'recorded image absent'
    if not s.get('sha256') or sha(image) != s['sha256']:
        return tag, image, 'recorded image SHA mismatch'
    return tag, image, None


def signature(p):
    r = read(p)
    tag, image, problem = last_capture(p)
    uid = (r.get('bms') or {}).get('uid')
    pids = run_facts.pids_for_uid(Path(p).parent / ('processes-' + str(tag) + '.txt'), uid) if tag and uid is not None else None
    return {'package': r.get('package'), 'apk_sha256': r.get('apk_sha256'),
            'status': r.get('status'), 'error': r.get('error'),
            'last_shot_tag': tag, 'image_sha256': sha(image) if image else None,
            'alive_last': None if pids is None else bool(pids),
            'capture_problem': problem}, image


def references(signoff, t3):
    """Resolve the exact outer-selected batch, including signed retry batches."""
    rows = {}
    for key, verdict in signoff['verdicts'].items():
        batch = verdict['batch']
        if batch == 'window1':
            candidates = [t3 / 'window1-evidence' / key / 'record.json']
        else:
            folder = t3 / 'plans-v2' / batch
            mapping = folder / 'sheet-mapping.json'
            if mapping.is_file():
                candidates = [expand(v['record']) for v in read(mapping) if v['key'] == key and v.get('record')]
            else:
                candidates = list((folder / 'runner').glob('*/*/*/' + key + '/record.json'))
        candidates = [p for p in candidates if p.is_file()]
        if len(candidates) != 1:
            raise ValueError('signed baseline record unresolved/ambiguous: ' + key + ' batch=' + batch)
        p = candidates[0]
        if read(p).get('key') != key:
            raise ValueError('baseline record key mismatch: ' + key)
        sig, image = signature(p)
        if sig['capture_problem']:
            raise ValueError('baseline evidence invalid: ' + key + ' ' + sig['capture_problem'])
        rows[key] = {'record': portable(p), 'record_sha256': sha(p),
                     'image': portable(image) if image else None,
                     'signed_verdict': verdict['verdict'], 'batch': batch, 'signature': sig}
    return rows


def records(root):
    result = {}
    # The driver aggregates canonical key folders with symlinks; Path.rglob does not
    # descend those folders. Follow them explicitly, rejecting cycles/duplicate trees.
    paths, visited = [], set()
    for folder, dirs, files in os.walk(root, followlinks=True):
        actual = Path(folder).resolve()
        if actual in visited:
            raise ValueError('duplicate/cyclic observed directory: ' + str(folder))
        visited.add(actual)
        if 'record.json' in files:
            paths.append(Path(folder) / 'record.json')
    for p in sorted(paths):
        r = read(p)
        key = r.get('key')
        if not key or r.get('install_only'):
            continue
        if key in result:
            raise ValueError('duplicate observed key; pass a canonical final view: ' + key)
        result[key] = p
    return result


def screen_class(image):
    """Triage only: calibrated launcher body or nearly pure black/white.

    The launcher reference is outer-confirmed, not an app-key allowlist. Cropping
    ignores status/navigation bars; resizing tolerates compression, clock and icon
    variation. Other wallpapers are not covered: same_class is NOT proof of lit.
    Decode/reference failures are suspect, so missing tooling cannot hide evidence.
    """
    try:
        reference = read(HERE / 'launcher-body-reference.json')
        rgb = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(image), '-vf',
            'crop=iw:ih*0.87:0:ih*0.06,scale=32:48', '-frames:v', '1',
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'],
            capture_output=True, check=True, timeout=15).stdout
        if len(rgb) != 32 * 48 * 3 or len(reference['rgb']) != len(rgb):
            raise ValueError('invalid RGB body/reference')
        pixels = [rgb[i:i+3] for i in range(0, len(rgb), 3)]
        black = sum(max(v) <= 8 for v in pixels) / len(pixels)
        white = sum(min(v) >= 247 for v in pixels) / len(pixels)
        distance = sum(abs(a-b) for a,b in zip(rgb, reference['rgb'])) / len(rgb)
        reason = 'pure_black' if black >= .98 else 'pure_white' if white >= .98 else \
                 'launcher_body_match' if distance <= 22 else None
        return {'class': 'suspect' if reason else 'same_class', 'reason': reason,
                'launcher_body_mean_absolute_error': round(distance, 4),
                'black_fraction': round(black, 4), 'white_fraction': round(white, 4),
                'launcher_threshold': 22, 'blank_threshold': .98}
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        return {'class': 'suspect', 'reason': 'image_classifier_unavailable: ' + str(exc)}


def compare(observed, baseline):
    rows = []
    for key, ref in sorted(baseline.items()):
        p = observed.get(key)
        item = {'key': key, 'signed_verdict': ref['signed_verdict'],
                'baseline_record': ref['record'], 'baseline_image': ref['image'],
                'record': portable(p) if p else None, 'image': None, 'reason': []}
        if p is None:
            item.update(category='missing', reason=['no record'])
        else:
            sig, image = signature(p)
            item['image'] = portable(image) if image else None
            item['signature'] = sig
            difference = [field for field in sig if sig[field] != ref['signature'].get(field)]
            if sig['capture_problem']:
                # Corrupt existing bytes are changed; absent promised captures are missing.
                category = 'changed' if image else 'missing'
                item.update(category=category, reason=[sig['capture_problem']])
            elif not image and ref['signature']['image_sha256']:
                item.update(category='missing', reason=['no final image; baseline has one'])
            else:
                item.update(category='changed' if difference else 'same', reason=difference)
        if item.get('image'):
            item['semantic'] = screen_class(expand(item['image'])) if not item.get('signature', {}).get('capture_problem') else {'class': 'suspect', 'reason': item['reason']}
        else:
            item['semantic'] = {'class': 'missing', 'reason': 'no trustworthy final image'}
        rows.append(item)
    return {'schema': 'demo-regression-evidence/v2', 'classification_is_ui_verdict': False,
            'summary': {c: sum(r['category'] == c for r in rows) for c in ('same', 'changed', 'missing')},
            'semantic_summary': {c: sum(r['semantic']['class'] == c for r in rows) for c in ('same_class', 'suspect', 'missing')},
            'extra_keys': sorted(set(observed) - set(baseline)), 'keys': rows}


def changed_sheet(report, out, script):
    changed = [r for r in report['keys'] if r['semantic']['class'] == 'suspect']
    images = out / 'changed-images'
    images.mkdir()
    inputs = []
    mapping = []
    for i, row in enumerate(changed):
        dest = images / (row['key'] + '.jpeg')
        if row.get('image'):
            dest.symlink_to(expand(row['image']).resolve())
        inputs.append(str(dest))  # absent source becomes explicit grey tile
        mapping.append({'key': row['key'], 'row': i // 6 + 1, 'column': i % 6 + 1,
                        'source': row['image'], 'baseline_image': row['baseline_image']})
    (out / 'changed-sheet-mapping.json').write_text(json.dumps(mapping, indent=2) + '\n')
    if inputs:
        with (out / 'contact-sheet.txt').open('w') as log:
            subprocess.run(['bash', str(script), str(out / 'changed-contact-sheet.jpeg'),
                            '--cols', '6', '--width', '260', *inputs], stdout=log, stderr=subprocess.STDOUT, check=True)
    return len(inputs)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('run', type=Path)
    ap.add_argument('--signoff', type=Path, default=BASE / 't3-outer-signoff.json')
    ap.add_argument('--baseline-t3', type=Path, default=BASE / 't3')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--sheet', action='store_true')
    a = ap.parse_args(argv)
    if a.out.exists():
        raise ValueError('fresh output required')
    signoff = read(a.signoff)
    # t5 subset (user 2026-10-11, Plan-2): if the round declares a key subset (batch-apps.json next to the run),
    # compare only those keys vs the signoff. The other signoff keys are cross-validated on the 5cd v1 Permissive
    # full-128 prerun, not re-run on 61b, so they are NOT counted "missing". signoff_sha256 stays the full-128 SHA.
    batch = a.run.parent / 'batch-apps.json'
    if batch.is_file():
        run_keys = {app['key'] for app in read(batch)['apps']}
        signoff = dict(signoff, verdicts={k: v for k, v in signoff['verdicts'].items() if k in run_keys})
    ref = references(signoff, a.baseline_t3)
    report = compare(records(a.run), ref)
    report['signoff_sha256'] = sha(a.signoff)
    report['run'] = portable(a.run.resolve())
    a.out.mkdir(parents=True)
    (a.out / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    (a.out / 'reference-index.json').write_text(json.dumps(ref, indent=2) + '\n')
    for category in ('same', 'changed', 'missing'):
        (a.out / (category + '.keys')).write_text(''.join(r['key'] + '\n' for r in report['keys'] if r['category'] == category))
    for category in ('same_class', 'suspect'):
        (a.out / (category + '.keys')).write_text(''.join(r['key'] + '\n' for r in report['keys'] if r['semantic']['class'] == category))
    if a.sheet:
        changed_sheet(report, a.out, REPO / 'scripts/lab/contact_sheet.sh')
    print(json.dumps({'byte_comparison': report['summary'], 'semantic_triage': report['semantic_summary']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
