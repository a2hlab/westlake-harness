"""Bounded regular-log read recipes; no device discovery, UI or CLI execution.

The outer supplies the existing collector's exact same-child/boot/UID/exe guard,
checks its board holder/deadline and uses its HDC argv. Never pass an empty guard.
The identity binding is the SHA256 of the admitted same-window identity receipt.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import time

BLOCK = 4096
MAX_DELTA = 262144


@dataclass(frozen=True)
class Snapshot:
    path: str
    dev: int
    inode: int
    size: int
    binding: str


def snapshot(path, stat_output, binding):
    if not re.fullmatch(r"[0-9a-f]{64}", binding):
        raise ValueError("exact identity receipt SHA required")
    fields = stat_output.strip().split(":")
    if len(fields) != 3 or not all(x.isdecimal() for x in fields):
        raise ValueError("expected device:inode:size only")
    dev, inode, size = map(int, fields)
    if inode <= 0 or not path.startswith("/") or "\n" in path:
        raise ValueError("regular absolute file identity required")
    return Snapshot(path, dev, inode, size, binding)


def stat_body(path):
    """Use within the existing collector's read() identity sandwich."""
    p = shlex.quote(path)
    return f'test -f {p}; stat -L -c "%d:%i:%s" {p}'


def read_recipe(before, after, identity_guard, marker, cap=MAX_DELTA):
    if (before.path, before.dev, before.inode, before.binding) != (
            after.path, after.dev, after.inode, after.binding):
        raise ValueError("file or child binding changed")
    if after.size < before.size:
        raise ValueError("log truncated")
    if not 0 < cap <= MAX_DELTA:
        raise ValueError("cap outside admitted bound")
    if not identity_guard.strip() or not re.fullmatch(r"DELTA_[0-9a-f]{32}", marker):
        raise ValueError("guard and unique marker required")
    count = min(after.size - before.size, cap)
    skip, trim = divmod(before.size, BLOCK)
    blocks = (trim + count + BLOCK - 1) // BLOCK if count else 0
    p = shlex.quote(before.path)
    file_guard = (f'test -f {p}; test "$(stat -L -c %d:%i {p})" = '
                  f'{before.dev}:{before.inode}; '
                  f'test "$(stat -L -c %s {p})" -ge {after.size}; ')
    # Exact identity and regular-file checks both before and after read.
    guard = identity_guard.rstrip().rstrip(";") + "; " + file_guard
    read = f'dd if={p} bs={BLOCK} skip={skip} count={blocks}; ' if blocks else ""
    script = ('(set -eu; ' + guard + read + guard +
              f'printf "{marker}\\n" >&2)')
    return {'script': script, 'marker': marker, 'source_offset': before.size,
            'selected_bytes': count, 'raw_source_offset': skip * BLOCK,
            'trim_prefix': trim if count else 0, 'max_raw_bytes': blocks * BLOCK,
            'snapshot_end': after.size, 'truncated_by_cap': after.size-before.size > cap,
            'binding': before.binding, 'scope': 'fixed byte range, not whole window'}


def capture(argv, out, recipe, timeout):
    """Reuse collector subprocess.run semantics, retaining TimeoutExpired bytes.

    Caller MUST check holder and remaining monotonic budget before this call.
    This helper neither acquires a board lock nor authorizes execution.
    """
    if not 0 < timeout <= 10:
        raise ValueError("positive timeout <= 10s required")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out/'argv.json').write_text(json.dumps(argv)+'\n')
    (out/'recipe.json').write_text(json.dumps(recipe, indent=2)+'\n')
    start = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.run(argv, capture_output=True, timeout=timeout)
        stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, rc = exc.stdout or b'', exc.stderr or b'', None
        timed_out = True
    (out/'stdout.raw').write_bytes(stdout)
    (out/'stderr.raw').write_bytes(stderr)
    marker_ok = recipe['marker'].encode() in stderr.splitlines()
    trim, n = recipe['trim_prefix'], recipe['selected_bytes']
    selected = stdout[trim:trim+n]
    (out/'selected.raw').write_bytes(selected)
    complete = (not timed_out and rc == 0 and marker_ok and len(selected) == n
                and len(stdout) <= recipe['max_raw_bytes'])
    result = {'rc': rc, 'host_timeout': timed_out, 'postguard_marker': marker_ok,
              'status': 'BOUNDED_BYTES_COMPLETE' if complete else 'PARTIAL_UNVERIFIED',
              'source_offset': recipe['source_offset'], 'selected_bytes': len(selected),
              'requested_bytes': n, 'elapsed_seconds': time.monotonic()-start,
              'raw_stdout_sha256': hashlib.sha256(stdout).hexdigest(),
              'selected_sha256': hashlib.sha256(selected).hexdigest(),
              'whole_window': False, 'player_verdict': 'unknown'}
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result
