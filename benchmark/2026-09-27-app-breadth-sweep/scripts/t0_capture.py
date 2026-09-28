"""Small production capture operations usable with a fake transport for negative controls."""
import hashlib
import re
import subprocess
import time
from pathlib import Path


def stderr_path(runtime, pid):
    if not re.fullmatch(r'/data/app/el2/100/base/org\.westlake\.imehost/files/a2hlab-source-[0-9a-f]{32}', runtime) or not isinstance(pid, int) or pid <= 0:
        raise ValueError('invalid current child identity')
    return f'{runtime}/private-tmp/adapter_child_{pid}.stderr'


def stack_capture(board, pid, rtpath, out, index, sections, main, sleep=time.sleep, now=time.time):
    rc, _ = board.shell(f'test -d /proc/{pid}', required=False)
    capture = {'status': 'capture-failed', 'reason': 'child-exited', 'pid': pid}
    if rc != 0:
        return capture
    capture.update(sent_epoch=now(), reason='no-complete-stack-within-12s')
    _, old = board.read(rtpath, out / f'quit{index}.before.stderr')
    rc, _ = board.shell(f'kill -QUIT {pid}', required=False)
    if rc:
        capture['reason'] = 'signal-failed-or-child-exited'
        return capture
    for _ in range(6):
        sleep(2)
        _, new = board.read(rtpath, out / f'quit{index}.after.stderr')
        complete = sections(new[len(old):] if new.startswith(old) else '', pid)
        if complete:
            name = f'quit{index}.stack.txt'
            (out / name).write_text(complete[-1])
            capture.update(status='ok', reason=None, file=name, main=main(complete[-1]))
            break
    sleep(max(0, 5 - (now() - capture['sent_epoch'])))
    return capture


def fresh_snapshot(rc, mtime, size, start):
    return rc == 0 and mtime >= start and size > 0


def isolated_root(home, run):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', run):
        raise ValueError('run id must be a single component')
    return Path(home) / 'a2hlab/ws' / ('out-appsweep-t0-' + run)


def lock_owner_valid(rc, output):
    return rc == 0 and output.startswith('cx-t0 ')


def attached(rc, output, serial):
    return rc == 0 and serial in output.split()
