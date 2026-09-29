"""#48: offline fake-board stub dry-run of probe_unknown22.py's first-app flow.

Validates the cold_stop FileNotFoundError fix WITHOUT touching the board:
- real bms_batch.cold_stop (the crash site) runs against a FakeBoard
- Board/parse_bundle/prepare_sandbox/desktop_launch are stubbed
- KEYS trimmed to the first app (termux)
PASS criteria: termux dir + processes-before.txt exist, no exception, record written.
"""
import sys, json, types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import bms_batch as b

class FakeBoard:
    serial = '61b-STUB'
    boot = 'stub-boot-id-0000000000000000000000'
    def __init__(self, *a, **k): self.calls = []
    def ready(self): self.calls.append('ready'); return True
    def shell(self, cmd, timeout=60, required=True):
        self.calls.append(cmd[:60])
        if cmd.startswith('ps -A'):
            # header + one clean appspawn-x root; no target-uid rows
            return 0, '  PID  PPID   UID NAME\n    1     0     0 init\n  100     1     0 appspawn-x\n'
        if cmd.startswith('hilog'):
            return 0, ''
        return 0, ''
    def receive(self, remote, local, timeout=60):
        Path(local).write_text('stub'); return True

def fake_parse_bundle(text, package):
    return {'queryable': True, 'uid': 20010999, 'uid_candidates': [20010999],
            'desktop_activity': 'net.gsantner.markor.activity.MainActivity'}

b.Board = FakeBoard
b.parse_bundle = fake_parse_bundle
def fake_sandbox(board, package, uid, out, *a, **k):
    (Path(out) / 'sandbox-preparation.json').write_text('{}')
    return {}
b.prepare_sandbox = fake_sandbox
def fake_launch(board, app, remote, out, record, pages=10):
    record['clicked'] = True
    record['selected_icon'] = {'id': 'STUB'}
b.desktop_launch = fake_launch

src = Path(ROOT / 'probe_unknown22.py').read_text()
src = src.replace("RUN = 'b4-48-unknown22-61b-20260929T1015'", "RUN = 'b4-48-stub-dryrun-mac'")
import re
src = re.sub(r"KEYS = \[.*?\]", "KEYS = ['termux']", src, count=1, flags=re.S)
g = {'__name__': '__main__', '__file__': str(ROOT / 'probe_unknown22.py')}
try:
    exec(compile(src, 'probe_unknown22.py', 'exec'), g)
except SystemExit as e:
    print('SystemExit', e.code); raise
