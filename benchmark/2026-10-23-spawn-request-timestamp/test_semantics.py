#!/usr/bin/env python3
"""Real local /bin/sh replay; production absolute paths never execute."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
COMMAND = '/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/host_spawn'
ARGS = ['/dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002',
        '/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/request.bin']
DATA = b'original-stdin\x00\xff\n'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fake = out / 'fake.py'
    fake.write_text('''import os,sys,json
from pathlib import Path
data=sys.stdin.buffer.read()
Path(os.environ['FAKE_RECORD']).write_text(json.dumps({'argv':sys.argv[1:],'stdin_hex':data.hex()}))
sys.stdout.buffer.write(b'client-stdout\\x00\\xfe\\n'+data);sys.stdout.buffer.flush()
try: os.write(2,b'client-stderr\\n')
except OSError: pass
sys.exit(int(os.environ['FAKE_RC']))
''')
    baseline = (ROOT / 'baseline.sh').read_text()
    candidate = (ROOT / 'candidate.sh').read_text()
    require(baseline.splitlines()[1] == candidate.splitlines()[5], 'original command changed')
    require(shlex.split(candidate.splitlines()[5]) == [COMMAND] + ARGS, 'argv drift')
    cases = [('success', 0, False, False, False),
             ('client_nonzero', 17, False, False, False),
             ('missing_uptime', 0, True, False, False),
             ('missing_uptime_nonzero', 23, True, False, True),
             ('closed_stderr', 0, False, True, False),
             ('closed_stderr_nonzero', 29, False, True, True),
             ('readonly_stderr', 27, False, 'readonly', False),
             ('readonly_stderr_nonzero', 31, False, 'readonly', True)]
    results = []
    for name, code, missing, closed, errexit in cases:
        case = out / name
        case.mkdir()
        uptime = case / 'uptime'
        if not missing:
            uptime.write_text('1234.56 987.65\n')
        pair = {}
        for label, source in [('baseline', baseline), ('candidate', candidate)]:
            # Fixture-only remapping; never modifies production candidate.
            mapped = source.replace(COMMAND, shlex.quote(sys.executable)+' '+shlex.quote(str(fake)), 1)
            mapped = mapped.replace('/proc/uptime', shlex.quote(str(uptime)))
            require(COMMAND not in mapped and '/proc/uptime' not in mapped, 'fixture mapping incomplete')
            script = case / (label + '.sh')
            script.write_text(mapped)
            argv = ['/bin/sh'] + (['-e'] if errexit else []) + [str(script)]
            if closed == 'readonly':
                argv = ['/bin/sh', '-c', 'exec 2</dev/null; exec "$@"', 'fixture'] + argv
            elif closed:
                argv = ['/bin/sh', '-c', 'exec 2>&-; exec "$@"', 'fixture'] + argv
            env = os.environ.copy()
            record = case / (label + '.client.json')
            env.update(FAKE_RECORD=str(record), FAKE_RC=str(code))
            (case / (label+'.argv.json')).write_text(json.dumps(argv)+'\n')
            (case / (label+'.stdin')).write_bytes(DATA)
            start = {'monotonic_ns':time.monotonic_ns(),'wall_ns':time.time_ns()}
            (case / (label+'.start.json')).write_text(json.dumps(start)+'\n')
            proc = subprocess.run(argv,input=DATA,capture_output=True,env=env,timeout=5)
            (case / (label+'.stdout')).write_bytes(proc.stdout)
            (case / (label+'.stderr')).write_bytes(proc.stderr)
            (case / (label+'.receipt.json')).write_text(json.dumps({'rc':proc.returncode,'end_monotonic_ns':time.monotonic_ns(),'end_wall_ns':time.time_ns()})+'\n')
            require(record.is_file(), name+': client did not execute')
            client = json.loads(record.read_text())
            require(client == {'argv':ARGS,'stdin_hex':DATA.hex()}, name+': argv/stdin mismatch')
            require(proc.returncode == code, name+': rc mismatch')
            pair[label] = proc
        require(pair['baseline'].stdout == pair['candidate'].stdout == b'client-stdout\x00\xfe\n'+DATA, name+': stdout mismatch')
        marker = b'' if missing or closed else b'[WL-SPAWN-REQUEST] uptime_s=1234.56\n'
        require(pair['candidate'].stderr == marker+pair['baseline'].stderr, name+': stderr mismatch/order')
        results.append({'case':name,'status':'PASS','client_rc':code,'closed_stderr':closed,'missing_uptime':missing,'shell_errexit':errexit})
    result = {'status':'OFFLINE_SHELL_PASS_NOT_DEPLOYED','shell':'/bin/sh',
              'cases':results,'production_candidate_sha256':hashlib.sha256((ROOT/'candidate.sh').read_bytes()).hexdigest(),
              'device_calls':0,'real_host_spawn_calls':0,
              'limit':'Host shell execution proves tested semantics; device shell not executed.'}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
