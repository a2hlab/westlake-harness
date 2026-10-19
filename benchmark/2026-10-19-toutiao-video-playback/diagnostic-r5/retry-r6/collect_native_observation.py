"""Read existing same-child logs under the outer board lock; never enable logging."""
import argparse
import json
import re
import shlex
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
for key in ('boot', 'parent', 'parent-birth', 'child', 'child-birth', 'tag'):
    parser.add_argument('--' + key, required=True)
args = parser.parse_args()
assert re.fullmatch(r'[0-9a-f-]{36}', args.boot)
assert re.fullmatch(r'[a-z0-9-]+', args.tag)
assert all(v.isdigit() for v in (args.parent, args.parent_birth, args.child, args.child_birth))
root = next(p for p in Path(__file__).resolve().parents if (p / 'scripts/lab/board_note.sh').is_file())
sys.path.insert(0, str(root / 'benchmark/2026-09-28-bms-route-deploy/batch'))
import bms_batch as b

out = Path.home() / '.local/share/westlake/toutiao-resume-20261019' / args.tag
out.mkdir(exist_ok=False)
board = b.Board('61b0657200000000000000000324012c',
                '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc',
                'bash ' + shlex.quote(str(root / 'scripts/lab/board_note.sh')),
                'outer(codex)', out / 'commands')
board.boot = args.boot
board.ready()
record = vars(args).copy()
record.update(playback='unknown', audio='unknown', child_survived_collection=False)
(out / 'identity.json').write_text(json.dumps(record, indent=2) + '\n')

def read(name, command, required=True):
    rc, text = board.shell(command, required=False)
    (out / name).write_text(text)
    if required:
        assert rc == 0, (name, rc)
    return rc, text

def identity(label):
    _, parent = read(label + '-parent.stat', 'cat /proc/' + args.parent + '/stat')
    assert parent.rsplit(') ', 1)[1].split()[19] == args.parent_birth
    rc, child = read(label + '-child.stat', 'cat /proc/' + args.child + '/stat', False)
    if rc:
        return False
    fields = child.rsplit(') ', 1)[1].split()
    assert fields[19] == args.child_birth and fields[1] == args.parent
    _, status = read(label + '-child.status', 'cat /proc/' + args.child + '/status')
    assert re.search(r'^Uid:\s+20011206\s+20011206\s', status, re.M)
    return True

record['child_present_before'] = identity('before')
read('parameter.txt', 'param get debug.ttplayer.log.enable', False)
read('hilog.txt', 'hilog -x -P ' + args.child + ' -L D,I,W,E,F -v monotonic')
log = '/proc/' + args.parent + '/root/data/service/el1/public/appspawnx/adapter_child_' + args.child + '.stderr'
board.receive(log, out / 'child.stderr')
read('maps.txt', 'cat /proc/' + args.child + '/maps', False)
record['child_present_after'] = identity('after')
record['child_survived_collection'] = record['child_present_before'] and record['child_present_after']
(out / 'identity.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
