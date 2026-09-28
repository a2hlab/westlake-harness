#!/usr/bin/env python3
"""Parse logcat/strace into order-only (seq,pid,tid,name,effect) tuples for task #70."""
from __future__ import annotations
import argparse, csv, re, sys
from pathlib import Path

LOGCAT_RE = re.compile(
    r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+(\d+)\s+(\d+)\s+[A-Z]\s+([^\s:]+)\s*:\s*(.*)$'
)
STRACE_OPENAT_RE = re.compile(
    r'^(\d+)\s+(?:(\d+)\s+)?([\d:.]+)\s+openat\([^,]*,\s*"([^"]+\.so[^"]*)"'
)
STRACE_EPOLL_RE = re.compile(
    r'^(\d+)\s+(?:(\d+)\s+)?([\d:.]+)\s+(epoll_wait|epoll_pwait|epoll_ctl|eventfd2?|futex)\('
)

DEFAULT_KEYS = (
    'ActivityThread', 'Looper', 'MessageQueue', 'nativePollOnce', 'Zygote',
    'RuntimeInit', 'ClassLoader', 'System.loadLibrary', 'dlopen', 'linker',
    'Genshin', 'Yuanshen', 'miHoYo', 'Unity', 'Download', 'epoll', 'eventfd',
)

def parse_logcat(path: Path, keys=DEFAULT_KEYS):
    seq = 0
    for line in path.read_text(errors='replace').splitlines():
        m = LOGCAT_RE.match(line)
        if not m:
            continue
        ts, pid, tid, tag, msg = m.groups()
        blob = f'{tag} {msg}'
        if not any(k.lower() in blob.lower() for k in keys):
            continue
        seq += 1
        yield seq, pid, tid, tag, msg[:240].replace('\t', ' '), ts

def parse_strace_libs(path: Path):
    seq = 0
    seen = set()
    for line in path.read_text(errors='replace').splitlines():
        m = STRACE_OPENAT_RE.search(line)
        if not m:
            continue
        pid = m.group(2) or m.group(1)
        so = m.group(4)
        if so in seen:
            continue
        seen.add(so)
        seq += 1
        yield seq, pid, pid, 'openat.so', so, m.group(3)

def parse_strace_mq(path: Path):
    seq = 0
    for line in path.read_text(errors='replace').splitlines():
        m = STRACE_EPOLL_RE.search(line)
        if not m:
            continue
        pid = m.group(2) or m.group(1)
        name = m.group(4)
        seq += 1
        yield seq, pid, pid, name, line.strip()[:240], m.group(3)

def write_csv(rows, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['seq', 'pid', 'tid', 'name', 'effect', 'ts_order_only'])
        for seq, pid, tid, name, effect, ts in rows:
            w.writerow([seq, pid, tid, name, effect, ts])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--logcat')
    ap.add_argument('--strace')
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()
    out = Path(args.outdir)
    if args.logcat:
        rows = list(parse_logcat(Path(args.logcat)))
        write_csv(rows, out / 'from-logcat.csv')
        print(f'logcat events: {len(rows)}')
    if args.strace and Path(args.strace).exists():
        libs = list(parse_strace_libs(Path(args.strace)))
        mq = list(parse_strace_mq(Path(args.strace)))
        write_csv(libs, out / 'dlopen-order.csv')
        write_csv(mq, out / 'mq-syscalls.csv')
        print(f'dlopen first-seen: {len(libs)}; mq syscalls: {len(mq)}')
    else:
        print('strace absent — skipped dlopen/mq CSVs')

if __name__ == '__main__':
    main()
