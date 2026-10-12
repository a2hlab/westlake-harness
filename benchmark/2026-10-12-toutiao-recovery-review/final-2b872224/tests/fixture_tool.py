#!/usr/bin/env python3
"""Fake command transport for the REAL shell candidate; all effects stay in the case dir."""
import json, os, sys, subprocess, shutil
from pathlib import Path

root = Path(os.environ['CASE_ROOT'])
name = Path(sys.argv[0]).name
args = sys.argv[1:]
model = json.loads((root / 'model.json').read_text())
with (root / 'calls.jsonl').open('a') as stream:
    stream.write(json.dumps({'command': name, 'args': args}) + '\n')
proc = root / 'proc'

def save():
    (root / 'model.json').write_text(json.dumps(model))

def process(pid, role):
    d = proc / str(pid); d.mkdir(exist_ok=True)
    # stat field 22: after state, skip19 fields; PPID is first field after state.
    birth = model.get('birth', '123')
    (d / 'stat').write_text(f'{pid} (fixture) S ' + str(100 if role == 'child' else 1) + ' ' + ' '.join(['0'] * 17) + f' {birth} 0\n')
    uid = '0' if role == 'parent' else model.get('uid', '20011206')
    (d / 'status').write_text('Uid:\t' + '\t'.join([uid] * 4) + '\n')
    (d / 'role').write_text(role)
    (d / 'ns').mkdir(exist_ok=True)

def pid_arg():
    s = ' '.join(args)
    import re
    m = re.search(r'/proc/(\d+)/', s)
    return m[1] if m else None

if name in ['mkdir', 'rm', 'rmdir', 'cp']:
    paths = [Path(a) for a in args if not a.startswith('-')]
    for p in paths:
        if not p.is_relative_to(root) or p.is_relative_to(root / 'runtime'):
            sys.exit('FORBIDDEN_FILE_EFFECT ' + str(p))
    sys.exit(subprocess.run(['/bin/' + name] + args).returncode)
elif name == 'readlink':
    pid = pid_arg()
    if args[0].endswith('/ns/mnt'):
        print('mnt:[1]' if pid == '1' or model.get('namespace') == 'global' else 'mnt:[2]')
    else:
        role = (proc / str(pid) / 'role').read_text()
        print(model.get('exe', '/data/local/tmp/asx/asx-spawner') if role == 'child' else model.get('parent_exe', '/data/local/tmp/asx/asx-spawner'))
elif name == 'sha256sum':
    print(model.get('sha', 'a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c') + '  ' + args[0])
elif name == 'stat':
    print(model.get('inode', '1:2') if '/root/' in args[-1] else '1:2')
elif name == 'timeout':
    rc = subprocess.run(args[1:]).returncode
    sys.exit(rc)
elif name == 'parent_tool':
    process(100, 'parent'); print('100')
elif name == 'spawn_tool':
    if model.get('spawn_fail'): sys.exit(7)
    n = model.get('spawns', 0); model['spawns'] = n + 1
    pid = 200 + n; process(pid, 'child'); save(); print(f'result=0 pid={pid}')
elif name == 'snapshot_display':
    frames = model.get('frames', ['unknown']); idx = model.get('captures', 0)
    label = frames[min(idx, len(frames) - 1)]
    model['captures'] = idx + 1; model['last_label'] = label; save()
    if label == 'snapshot_error':
        print('fixture: snapshot writer failed', file=sys.stderr); sys.exit(9)
    Path(args[args.index('-f') + 1]).write_bytes(b'fixture capture: ' + label.encode())
elif name == 'screen-gate':
    if model.get('classifier_fail'): sys.exit(8)
    print(model['last_label'])
elif name == 'sleep':
    model['sleeps'] = model.get('sleeps', 0) + 1
    if model.get('exit_every_sleep') or model.get('recycle_after_sleep') or model.get('stat_missing_after_sleep') or model.get('zombie_every_sleep'):
        pid = 199 + model.get('spawns', 0)
        d = proc / str(pid)
        if (d / 'stat').exists():
            if model.get('recycle_after_sleep'):
                s = (d / 'stat').read_text(); (d / 'stat').write_text(s.replace(' 123 0', ' 999 0'))
            elif model.get('stat_missing_after_sleep'): (d / 'stat').unlink()
            elif model.get('zombie_every_sleep'):
                (d / 'stat').write_text((d / 'stat').read_text().replace(') S ', ') Z '))
            else: shutil.rmtree(d)
    if model.get('stop_after_sleep'): (root / 'state' / 'stop').write_text('operator marker')
    save()
elif name in ['uinput', 'kill', 'pkill', 'killall', 'reboot', 'setenforce', 'begetctl', 'chown', 'chcon', 'mount']:
    sys.exit('FORBIDDEN_SIDE_EFFECT ' + name)
else:
    sys.exit('unexpected fixture command: ' + name)
