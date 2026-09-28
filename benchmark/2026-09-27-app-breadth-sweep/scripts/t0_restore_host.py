"""Authorized #11 data-preserving host restore. Run on the VM under board lock."""
import json
import subprocess
import sys
from pathlib import Path
import t0_collect as c

ALLOWED = {'5ea34a4500000000000000001123012c', '61b0657200000000000000000324012c'}
EXPECTED = '8cfa5bb1eb1a26fa69dbfd5618cecf0aefb282f6035aa9af24dcb9f96eb81267'


def identity(board):
    _, digest = board.shell('sha256sum /data/app/el1/bundle/public/org.westlake.imehost/entry.hap')
    _, dump = board.shell('bm dump -n org.westlake.imehost')
    obj = json.loads(dump[dump.index('{'):])['applicationInfo']
    return {'hap_sha256': digest.split()[0], 'versionName': obj['versionName'],
            'versionCode': obj['versionCode'], 'bundleName': obj['bundleName']}


serial, run_id = sys.argv[1:]
if serial not in ALLOWED or not c.re.fullmatch(r'[a-zA-Z0-9_-]+', run_id):
    raise SystemExit('invalid serial/run_id')
c.SERIAL = serial
out = Path.home() / 'a2hlab/ws' / ('out-appsweep-t0-' + run_id) / serial / 'host-restore'
out.mkdir(parents=True, exist_ok=False)
b = c.Board(out)
b.ready()
hap = c.W / 'out/signed-host/source-host.hap'
assert c.sha(hap) == EXPECTED
record = {'serial': serial, 'run_id': run_id, 'before': identity(b), 'input_sha256': c.sha(hap)}
c.save(out / 'restore.json', record)
b.ready()
p = subprocess.run([c.HDC, '-t', serial, 'install', '-r', str(hap)], capture_output=True, text=True, timeout=90)
(out / 'install.txt').write_text(p.stdout + p.stderr)
record['install_rc'] = p.returncode
record['after'] = identity(b)
record['passed'] = p.returncode == 0 and record['after']['hap_sha256'] == EXPECTED
c.save(out / 'restore.json', record)
print(json.dumps(record), flush=True)
raise SystemExit(0 if record['passed'] else 2)
