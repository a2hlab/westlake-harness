#!/usr/bin/env python3
"""Integration-only external-command recorder; no native/device transport."""
import hashlib, json, os, re, socket, subprocess, sys
from pathlib import Path
root = Path(os.environ['CASE_ROOT'])
name, args = Path(sys.argv[0]).name, sys.argv[1:]
with (root / 'commands.jsonl').open('a') as f:
    f.write(json.dumps({'command': name, 'args': args}) + '\n')
model = json.loads((root / 'model.json').read_text())

def process(pid, uid, ppid):
    d = root / 'proc' / str(pid); d.mkdir(exist_ok=True)
    (d / 'stat').write_text(f'{pid} (fixture) S {ppid} ' + ' '.join(['0'] * 17) + ' 123 0\n')
    (d / 'status').write_text('Uid:\t' + '\t'.join([str(uid)] * 4) + '\n')
    (d / 'environ').write_bytes(b'WL_PARENT_ID=777\x00')
    view=d/'root/data/local/tmp/asx';view.mkdir(parents=True,exist_ok=True)
    (view/'prepare_jit50.sh').symlink_to(root/'runtime/prepare_jit50.sh')

if name == 'sha256sum':
    p = Path(args[0])
    sha = 'a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c' if '/proc/' in str(p) and p.name == 'exe' else hashlib.sha256(p.read_bytes()).hexdigest()
    print(sha + '  ' + str(p))
elif name == 'readlink':
    if args[0].endswith('/ns/mnt'):
        print('mnt:[1]' if '/proc/1/' in args[0] else 'mnt:[2]')
    else: print(str(root / 'device-data/local/tmp/asx/asx-spawner'))
elif name == 'stat':
    if args[-1].endswith('/prepare_jit50.sh'):
        st=Path(args[-1]).stat();print(f'{st.st_dev}:{st.st_ino}')
    else:print('20011206' if args[:2]==['-c','%u'] else ('20011206:20011206:700' if args[-1].endswith('art-volatile') else '1:2'))
elif name == 'hidumper':
    if not model.get('window_missing'): print('imehost0 a b 777 c d e 0')
elif name == 'sed':
    # Only the real start-parent's window-ID update is recorded/simulated.
    if args[0] == '-i':
        assert 'WL_PARENT_ID=' in args[1]
        p = Path(args[-1]); p.write_text(re.sub(r'WL_PARENT_ID=\d+', 'WL_PARENT_ID=777', p.read_text()))
    else:
        assert args[0] == '-n';sys.exit(subprocess.run(['/usr/bin/sed']+args).returncode)
elif name == 'nohup':
    os.execv(args[0], args)
elif name == 'source_app_namespace':
    assert (root/'state/lock/owner').is_file(), 'parent launch before candidate owner'
    process(os.getpid(), 0, 1)
    s=socket.socket(socket.AF_UNIX);s.bind(str(root/'socket'));s.close()
elif name == 'host_spawn':
    assert (root/'state/lock/owner').is_file(), 'child launch before candidate owner'
    assert args == [str(root / 'socket'), str(root / 'stage/request.bin')]
    data=(root/'stage/request.bin').read_bytes()
    assert all(int.from_bytes(data[n:n+4],'little')==20011206 for n in [312,316])
    identity=root/'state/parent-identity'
    parent=int(identity.read_text().split()[0]) if identity.exists() else 100
    process(200, 20011206, parent)
    print('result=0 pid=200')
elif name == 'nsenter':
    assert args[0] == '-t' and args[1].isdigit() and args[2:4] == ['-m','--']
    if model.get('jit_fail'): sys.exit(9)
    sys.exit(subprocess.run(args[4:]).returncode)
elif name == 'timeout':
    sys.exit(subprocess.run(args[1:]).returncode)
elif name == 'snapshot_display':
    Path(args[args.index('-f') + 1]).write_bytes(b'fixture frame: not a real screenshot')
elif name == 'screen-gate':
    print('feed')
elif name in ['chown', 'chmod']:
    assert args[-1].endswith('/code_cache/art-volatile') and str(root) in args[-1]
elif name == 'ls':
    print('fixture cache metadata; not real board SELinux evidence')
elif name == 'sleep':
    pass
else:
    sys.exit('UNEXPECTED_OR_FORBIDDEN_COMMAND ' + name)
