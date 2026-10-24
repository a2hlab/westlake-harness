#!/usr/bin/env python3
"""Offline evidence summarizer. Never invokes device commands or reads tools/."""
import hashlib
import json
import re
import shutil
from pathlib import Path

OUT = Path(__file__).resolve().parent
BASE = Path.home() / '.local/share/westlake'
NAMES = ['recents-close-reopen-20261024', 'desktop-reopen-20261024',
         'desktop-reopen-02-20261024']
PINS = {}


def pin(p):
    data = p.read_bytes()
    key = '$HOME/' + p.relative_to(Path.home()).as_posix()
    PINS[key] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    return key


def read(p):
    pin(p)
    return p.read_text().strip()


def js(p):
    return json.loads(read(p))


def identity(p):
    d = js(p)
    return {'evidence': pin(p), 'boot': d['boot'], 'device_uptime': float(d['uptime']),
            'ps_rc': d['ps_rc'], 'ps_err': d['ps_err'],
            'processes': [{k: x[k] for k in ('role', 'pid', 'ppid', 'birth', 'uid', 'errors')}
                          for x in d['procs'] if x['role'] in ('host', 'parent', 'child')]}


def command(p):
    argv = js(p)
    pin(p.with_suffix('.stderr'))
    return {'evidence': pin(p), 'ui_command': argv[-1],
            'rc': int(read(p.with_suffix('.rc'))),
            'start': read(p.with_suffix('.start')), 'end': read(p.with_suffix('.end')),
            'stdout': read(p.with_suffix('.stdout')),
            'stderr_bytes': p.with_suffix('.stderr').stat().st_size}


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


windows = []
facts = []
for name in NAMES:
    r = BASE / name
    actions = []
    for p in sorted((r / 'raw').glob('*/*.argv')):
        # Only ordinary UI command receipts; never recorder/control implementation.
        argv = json.loads(p.read_text())
        if 'uitest uiInput' in argv[-1]:
            actions.append(command(p))
    counts = {k: sum(a['rc'] == 0 and token in a['ui_command'] for a in actions)
              for k, token in [('home', 'keyEvent Home'), ('click', 'uiInput click'),
                               ('swipe', 'uiInput swipe'), ('recent', 'keyEvent 10011'),
                               ('wake', 'keyEvent WakeUp')]}
    images = []
    for p in sorted((r / 'raw').glob('*/*.jpeg')):
        stem = p.with_name(p.stem + '_rs.rc')
        received = stem.exists() and read(stem) == '0'
        images.append({'path': pin(p), 'received_rc0': received, **PINS[pin(p)]})
    ids = [identity(p) for p in sorted((r / 'raw').glob('*/*.ident.json'))]
    pre = list(map(int, read(r / 'raw/POWER_PRE').split()))
    power_text = read(r / 'raw/09/pw.stdout')
    match = re.search(r'Timeout=(\d+)ms\s+OverrideTimeout=(\d+)ms', power_text)
    after = list(map(int, match.groups()))
    cleanup = {'power_before': pre, 'power_after': after, 'power_rc': int(read(r / 'raw/09/pw.rc')),
               'power_equal': pre == after, 'unlock_rc': int(read(r / 'raw/09/unlock.rc')),
               'held_rc': int(read(r / 'raw/09/held.rc')), 'held_stdout': read(r / 'raw/09/held.stdout'),
               'completed': read(r / 'DONE')}
    for f in ['raw/09/VERIFY', 'raw/09/pw.start', 'raw/09/unlock.end',
              'raw/00/PREFLIGHT_OK', 'raw/01/lock.rc', 'raw/LOCK_T', 'raw/LOCK_EPOCH',
              'raw/05/wait.start', 'raw/05/wait.timeout', 'raw/05/FOUND']:
        if (r / f).exists(): pin(r / f)
    windows.append({'root': '$HOME/.local/share/westlake/' + name, 'actions': actions,
                    'successful_ui_counts': counts, 'images': images, 'identities': ids, 'cleanup': cleanup})
    facts.append(f'RUN {name} screenshots_received={sum(x["received_rc0"] for x in images)} '
                 f'screenshot_files={len(images)} home={counts["home"]} click={counts["click"]} '
                 f'swipe={counts["swipe"]} recent={counts["recent"]} '
                 f'power_restored={str(cleanup["power_equal"]).lower()} '
                 f'unlock_rc={cleanup["unlock_rc"]} held_rc={cleanup["held_rc"]} '
                 f'held_stdout_bytes={len(cleanup["held_stdout"].encode())}')
    for i in ids:
        roles = {role: [x for x in i['processes'] if x['role'] == role] for role in ['host', 'parent', 'child']}
        facts.append('IDENTITY ' + name + '/' + i['evidence'].split('/')[-1] +
                     f' uptime={i["device_uptime"]} ' + ' '.join(
                         f'{role}_count={len(ps)} {role}_pid_birth=' + ','.join(f'{p["pid"]}:{p["birth"]}' for p in ps)
                         for role, ps in roles.items()))

final = BASE / NAMES[-1]
click_text = read(final / 'raw/06/click.stdout').splitlines()
click = [float(click_text[0].split()[0]), float(click_text[-1].split()[0])]
screens = []
for tag in ['t10', 't30', 't60', 't90']:
    p = final / f'raw/06/{tag}.jpeg'
    shutil.copyfile(p, OUT / 'screenshots' / p.name)
    screens.append({'name': tag, 'source': pin(p), 'sha256': PINS[pin(p)]['sha256'],
                    'public_path': 'screenshots/' + p.name, 'verdict': 'white',
                    'original_visual_reviewer': 'author' if tag == 't30' else 'outer',
                    'review_attribution_source': 'user closeout instruction, 2026-10-24',
                    'offline_author_rechecked': True,
                    'shot_start': read(final / f'raw/06/{tag}_shot.start'),
                    'shot_end': read(final / f'raw/06/{tag}_shot.end')})
wms = final / 'raw/08/wms.stdout'
pin(wms)
rows = [{'line': i, 'text': line} for i, line in enumerate(wms.read_text().splitlines(), 1)
        if line.startswith('imehost0') or line.startswith('Focus window:')]
observer = BASE / 'desktop-reopen-02-observer-20261024'
samples = [js(p) for p in sorted(observer.glob('sample-*.json'))]
result = js(observer / 'result.json')
receipts = [js(p) for p in sorted(observer.glob('command-*/receipt.json'))]
for p in sorted(observer.glob('command-*/*')):
    if p.name in ['stdout', 'stderr']: pin(p)  # hash only; never publish raw logs
plan = js(observer / 'plan.json')
coverage = {'accepted_samples': len(samples), 'reported': result,
            'first_uptime': samples[0]['uptime_bracket'][0], 'last_uptime': samples[-1]['uptime_bracket'][1],
            'start_after_click_end_s': round(samples[0]['uptime_bracket'][0] - click[1], 2),
            'all_stable': all(s['status'] == 'stable' for s in samples),
            'all_child_identities': sorted({tuple(s['child_identity']) for s in samples}),
            'offset_ranges': {key: sorted({(s['ranges'][key]['start'], s['ranges'][key]['end']) for s in samples})
                              for key in ('parent', 'events')},
            'command_receipts': len(receipts), 'terminal_receipt': receipts[-1],
            'duration_limit_s': plan['duration_s'],
            'limitation': 'Post-click visibility samples only; no pre-click coverage, no continuous execution proof. '
                          'Buffering or truncate/regrow between samples may be invisible.'}
facts.append(f'OBSERVER accepted_samples={len(samples)} command_receipts={len(receipts)} '
             f'first_uptime={coverage["first_uptime"]} last_uptime={coverage["last_uptime"]} '
             f'identity_transition_samples={result["identity_transition_samples"]} stop={result["reason"]}')
facts.append('PUBLIC screenshots=' + str(len(screens)) + ' names=' + ','.join(x['name'] for x in screens))
assert len(samples) == result['accepted_samples']
assert all(w['cleanup']['power_equal'] and w['cleanup']['unlock_rc'] == 0 and
           w['cleanup']['held_rc'] == 1 and not w['cleanup']['held_stdout'] for w in windows)
dump('results.json', {'status': 'observed_white_on_final_reopen; cause_unknown',
     'scope': 'Offline review only; device execution by original recorder, not this review.',
     'source_or_runtime_changes': False, 'repair_or_seal_claim': False,
     'windows_are_separate': True, 'windows': windows, 'final_click_device_uptime': click,
     'screenshots': screens, 'wms': {'evidence': pin(wms), 'rows': rows,
     'start': read(final / 'raw/08/wms.start'), 'end': read(final / 'raw/08/wms.end'),
     'limitation': 'After t90, before final Home; not click-time focus evidence.'}, 'observer': coverage,
     'window_outcomes': ['Close completed; GO wait expired without reopening.',
                         'Intermediate Home without target or click (operator report + no click receipt).',
                         'One desktop target click; four sampled white screens; final Home and cleanup.']})
dump('raw-manifest.json', {'scope': 'Exact selected evidence pins; not an inventory of every private file.',
                         'files': dict(sorted(PINS.items()))})
(OUT / 'facts.txt').write_text('\n'.join(facts) + '\n')
print('\n'.join(facts))
print('selected_private_pins=' + str(len(PINS)))
