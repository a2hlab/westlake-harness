#!/usr/bin/env python3
"""把 OH 侧 hilog / strace 解析成与安卓侧同格式的事件五元组。

输出列与 parse-events.py 完全一致：seq,pid,tid,name,effect,ts_order_only
只有列一致，diff-events.py 才能逐条对齐。
"""
from __future__ import annotations
import argparse, csv, re
from pathlib import Path

# hilog 行：MM-DD HH:MM:SS.mmm  PID  TID LEVEL DOMAIN/TAG: message
HILOG_RE = re.compile(
    r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+(\d+)\s+(\d+)\s+[A-Z]\s+'
    r'(?:[0-9a-fA-F]{5,6}/)?([^\s:]+)\s*:\s*(.*)$'
)
STRACE_OPENAT_RE = re.compile(
    r'^(\d+)\s+(?:(\d+)\s+)?([\d:.]+)\s+openat\([^,]*,\s*"([^"]+\.so[^"]*)"'
)
STRACE_MQ_RE = re.compile(
    r'^(\d+)\s+(?:(\d+)\s+)?([\d:.]+)\s+(epoll_wait|epoll_pwait|epoll_ctl|eventfd2?|futex)\('
)

# 关注词表：安卓概念 + OH 对应机制，两侧都要留，否则比对时会把「机制不同」漏掉
DEFAULT_KEYS = (
    # 安卓侧概念（适配层会照搬这些名字）
    'ActivityThread', 'Looper', 'MessageQueue', 'nativePollOnce',
    'RuntimeInit', 'ClassLoader', 'System.loadLibrary', 'JNI', 'art',
    # OH 侧机制
    'appspawn', 'AppSpawn', 'BMS', 'BundleMgr', 'AbilityManager', 'AAFwk',
    'ArkUI', 'WindowManager', 'WMS_LIFE', 'WMS_MAIN', 'RenderService',
    'EventRunner', 'EventHandler', 'IPC', 'SAMGR',
    # 通用
    'dlopen', 'linker', 'ld-musl', 'epoll', 'eventfd', 'SIG',
)


def parse_hilog(path: Path, keys=DEFAULT_KEYS):
    seq = 0
    for line in path.read_text(errors='replace').splitlines():
        m = HILOG_RE.match(line)
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
        m = STRACE_MQ_RE.search(line)
        if not m:
            continue
        pid = m.group(2) or m.group(1)
        seq += 1
        yield seq, pid, pid, m.group(4), line.strip()[:240], m.group(3)


def write_csv(rows, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['seq', 'pid', 'tid', 'name', 'effect', 'ts_order_only'])
        for row in rows:
            w.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hilog')
    ap.add_argument('--strace')
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()
    out = Path(args.outdir)

    if args.hilog and Path(args.hilog).exists():
        rows = list(parse_hilog(Path(args.hilog)))
        write_csv(rows, out / 'from-hilog.csv')
        print(f'hilog 事件：{len(rows)} 条')
    else:
        print('hilog 缺失 —— 未产出事件序列')

    if args.strace and Path(args.strace).exists():
        libs = list(parse_strace_libs(Path(args.strace)))
        mq = list(parse_strace_mq(Path(args.strace)))
        write_csv(libs, out / 'dlopen-order.csv')
        write_csv(mq, out / 'mq-syscalls.csv')
        print(f'首次 dlopen：{len(libs)} 条；消息队列系统调用：{len(mq)} 条')
    else:
        print('strace 缺失 —— 跳过 dlopen / 消息队列序列（此为降级，须在证据里写明）')


if __name__ == '__main__':
    main()
