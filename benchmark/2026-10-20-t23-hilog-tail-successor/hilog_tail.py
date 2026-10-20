#!/usr/bin/env python3
"""Offline command generator / receipt analyzer. Never invokes a device."""
import argparse
import hashlib
import json
import re
from pathlib import Path

BEGIN = 'WL_HILOG_BODY_BEGIN\n'
END = 'WL_HILOG_BODY_END\n'

def plan(pid, tail):
    if pid <= 0 or not 1 <= tail <= 2000:
        raise ValueError('positive PID and tail 1..2000 required')
    argv = ['hilog', '-P', str(pid), '-z', str(tail), '-L', 'D,I,W,E,F', '-v', 'epoch']
    shell = "printf 'WL_HILOG_BODY_BEGIN\\n'\n" + 'if ' + ' '.join(argv) + '; then wl_hilog_rc=0; else wl_hilog_rc=$?; fi'
    shell += "\nprintf '\\nWL_HILOG_BODY_END\\nWL_HILOG_RC=%s\\n' \"$wl_hilog_rc\"\n"
    return {'argv': argv, 'shell_fragment': shell, 'host_timeout_seconds': 8,
            'execution': 'outer only, sequential inside existing holder/boot/identity guards',
            'postguard_exit': 'retain raw; mark attribution unknown, not discard logs'}

def analyze(body, stderr, transport_rc, remote_rc, complete, pid, postguard='unknown'):
    text = body.decode('utf-8', errors='replace')
    errors = [int(n) for n in re.findall(r'\[CODE:\s*(-?\d+)\]', text + stderr.decode('utf-8', errors='replace')) if int(n) != 0]
    stamps = []
    other_pid_lines = 0
    for line in text.splitlines():
        m = re.match(r'^\s*(\d{10}(?:\.\d+)?)\s+(\d+)\s+', line)
        if m:
            if int(m[2]) == pid:
                stamps.append(m[1])
            else:
                other_pid_lines += 1
    success = complete and transport_rc == 0 and remote_rc == 0 and not errors and not other_pid_lines
    return {'status': 'COLLECTED' if success else 'REJECTED_OR_PARTIAL',
            'transport_rc': transport_rc, 'remote_rc': remote_rc, 'complete': complete,
            'body_error_codes': errors, 'body_bytes': len(body),
            'body_sha256': hashlib.sha256(body).hexdigest(), 'stderr_bytes': len(stderr),
            'timestamped_pid_lines': len(stamps), 'unexpected_pid_lines': other_pid_lines,
            'first_timestamp_epoch': stamps[0] if stamps else None,
            'last_timestamp_epoch': stamps[-1] if stamps else None,
            'coverage': 'captured tail only; not an action interval or full log history' if stamps else 'UNKNOWN_NO_PARSEABLE_PID_TIMESTAMPS',
            'postguard': postguard,
            'attribution': 'requires outer boot/PID/birth bookends; exited/unreadable postguard leaves reuse ambiguity',
            'elapsed_used_as_coverage': False}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='mode', required=True)
    p = sub.add_parser('plan'); p.add_argument('--pid', type=int, required=True); p.add_argument('--tail', type=int, default=2000)
    p = sub.add_parser('inspect'); p.add_argument('--stdout', type=Path, required=True); p.add_argument('--stderr', type=Path, required=True)
    p.add_argument('--transport-rc', type=int, required=True); p.add_argument('--pid', type=int, required=True)
    p.add_argument('--postguard', choices=['same', 'gone', 'unknown'], default='unknown')
    a = ap.parse_args()
    if a.mode == 'plan':
        result = plan(a.pid, a.tail)
    else:
        raw = a.stdout.read_bytes(); begin = BEGIN.encode(); end = END.encode()
        m = re.search(rb'\nWL_HILOG_RC=(-?\d+)\n?$', raw)
        complete = raw.count(begin) == 1 and raw.count(end) == 1 and m is not None and raw.index(begin) < raw.index(end)
        body = raw.split(begin, 1)[1].split(end, 1)[0] if complete else raw
        result = analyze(body, a.stderr.read_bytes(), a.transport_rc, int(m[1]) if m else None, complete, a.pid, a.postguard)
        result['raw_stdout_sha256'] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(result, indent=2))
    return 0 if a.mode == 'plan' or result['status'] == 'COLLECTED' else 2

if __name__ == '__main__':
    raise SystemExit(main())
