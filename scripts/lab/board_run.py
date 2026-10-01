#!/usr/bin/env python3
"""Standard on-board run: the fixed steps of every board dispatch, in one command.

    board_run.py PLAN.json                 # execute
    board_run.py PLAN.json --dispatch      # print the dispatch text to send to a lane (no board access)
    board_run.py PLAN.json --detach        # start in its own session, print pid + log path, return at once

The steps are not optional and not re-typed per dispatch (2026-10-01: a hand-written dispatch dropped --hilog, another
said "two shards per board" and the lane ran them in parallel, a third said "keep only record.json" and the lane
deleted 198 never-committed screenshots, a fourth went to a full sweep with two fixes that had never activated):
  1. LOCK the board (board_note.sh), refuse if another lane holds it; UNLOCK on every exit path;
  2. activation smoke gate (activation_smoke.py) with the plan's smoke spec: fingerprints = expected state,
     controls alive, every fix's activation marker, single-copy libraries and child-view hashes. FAIL = stop;
  3. shards run one after another, one bms_batch process at a time, each with --reinstall --hilog --shots 5,20,
     each into its own new directory; nothing under the output root is ever deleted;
  4. after each shard its facts.txt TOTAL line is appended to the board verbatim; screenshots are left for the
     outer loop to read and sign.

PLAN.json:
  {"serial": "<connect-key>", "lane": "oc-t4", "entry": "97", "why": "U9 full sweep 5ea shard",
   "board": "<abs path of .octos/boards/app-lighting.md>", "out": "<new dir>",
   "smoke_spec": "knowledge/smoke/<x>.json",
   "shards": [{"name": "v1", "manifest": "...", "input_root": "...", "keys_file": "..."}, ...]}
Relative paths are resolved against the repo; $WORKSPACES is expanded.
Lanes start it with --detach (2026-10-01 13:43: oc-t4 ran it inside an agent bash tool call; the tool's 6-minute
timeout killed board_run and bms_batch mid-shard, after fd-uhabits was uninstalled and before it was reinstalled, and
the board stayed locked). SIGTERM / SIGHUP now unwind through the same finally (before_unlock, then UNLOCK).
Required offline_precheck (user rule 2026-10-01): {"hypothesis": "...", "evidence": [existing paths], "result":
"not-falsified"} -- what this window tests and the existing evidence (run-dir maps / hilog / faultlog, DIGEST, AOSP
source) it was checked against first; a hypothesis that existing evidence already falsifies never takes a board.
Optional after_lock is an argv list run right after LOCK, before the smoke gate: the overlay deploy of a short window
(e.g. sweep_bind_deploy.py --no-run --no-rollback ...). Non-zero = no smoke, no shards; before_unlock still runs.
Optional before_unlock is an argv list executed while the lock is still held, including on smoke failure.
It must finish the authorized rollback and verification. Failure retains the lock for recovery.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import lab_paths  # noqa: E402

BATCH = REPO / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
RULES = [
    'board_run.py 一条命令做完,不手写步骤',
    '先 LOCK 板(board_note.sh),结束或出错都 UNLOCK',
    '先过生效冒烟门(activation_smoke.py:指纹 / 对照 / 每个修复的生效日志 / 子进程单份库 / 子进程视图 sha),FAIL 就停',
    '每块板同一时刻只跑一个 bms_batch 进程,分片顺序跑(bms_batch 自带同板进程锁)',
    '每个分片都带 --reinstall --hilog --shots 5,20,各进新目录',
    '原始运行目录一个字节不删;落库只复制',
    '车道里用 --detach 起(agent 的工具调用超时会连带杀掉前台进程),再按日志和黑板轮询',
    '上板前先用已有证据离线核这次的假设(运行目录的 maps / hilog / faultlog、DIGEST、本机 AOSP 源码),能离线证伪就不上板;plan 里写 offline_precheck(hypothesis / evidence / result=not-falsified),缺了 board_run 拒跑',
    '每个分片的 facts.txt TOTAL 行原样贴黑板;截图交外环读图签数',
]


def expand(p):
    if '$WORKSPACES' in str(p) and not os.environ.get('WORKSPACES'):
        os.environ['WORKSPACES'] = str(lab_paths.workspaces())
    p = os.path.expanduser(os.path.expandvars(str(p)))
    return p if os.path.isabs(p) else str(REPO / p)


def dispatch_text(plan, plan_path):
    lines = [f'上板单(#{plan["entry"]},{plan["why"]}):在 westlake-harness 下执行',
             f'  python3 scripts/lab/board_run.py {plan_path}',
             '这条命令固定做下面几件事,不要拆开手写:']
    lines += [f'  {i}. {r}' for i, r in enumerate(RULES, 1)]
    lines.append('跑完贴每个分片 facts.txt 的 TOTAL 行原样(脚本已自动贴一份),截图不自判、交外环。')
    return '\n'.join(lines)


def precheck_problem(pre):
    """The window's hypothesis must have been checked against existing evidence first (user rule 2026-10-01: run dirs'
    maps / hilog / faultlog, DIGEST, AOSP source). Returns a refusal reason, or None."""
    if not isinstance(pre, dict):
        return ('plan needs "offline_precheck": {"hypothesis": ..., "evidence": [existing paths: run-dir maps / hilog / '
                'faultlog, DIGEST lines, AOSP source], "result": "not-falsified"}')
    if not str(pre.get('hypothesis', '')).strip():
        return 'offline_precheck.hypothesis is empty'
    ev = pre.get('evidence') or []
    if not ev:
        return 'offline_precheck.evidence is empty: name the existing evidence the hypothesis was checked against'
    missing = [e for e in ev if not Path(expand(str(e).split(':')[0])).exists()]
    if missing:
        return 'offline_precheck.evidence not found: ' + ', '.join(missing)
    if pre.get('result') != 'not-falsified':
        return f'offline_precheck.result is {pre.get("result")!r}; a hypothesis falsified offline does not go on a board'
    return None


def board_append(plan, text):
    subprocess.run([str(HERE / 'board_append.sh'), plan['board'], text], check=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('plan', type=Path)
    ap.add_argument('--dispatch', action='store_true', help='print the dispatch text and exit')
    ap.add_argument('--detach', action='store_true', help='run in a new session (survives the caller), log beside out')
    args = ap.parse_args(argv)
    plan = json.loads(args.plan.read_text())
    for k in ('serial', 'lane', 'entry', 'why', 'board', 'out', 'smoke_spec', 'shards'):
        if k not in plan:
            sys.exit(f'plan missing {k}')
    plan['board'] = expand(plan['board'])
    cleanup, deploy = plan.get('before_unlock'), plan.get('after_lock')
    for name, argv_ in (('before_unlock', cleanup), ('after_lock', deploy)):
        if argv_ is not None and (not isinstance(argv_, list) or not argv_ or
                                  any(not isinstance(x, str) or not x for x in argv_)):
            sys.exit(f'{name} must be a nonempty argv list')
    if args.dispatch:
        print(dispatch_text(plan, args.plan)); return 0
    problem = precheck_problem(plan.get('offline_precheck'))
    if problem:
        sys.exit(f'REFUSE (offline precheck, user rule 2026-10-01): {problem}')
    note = str(lab_paths.tools() / 'board_note.sh')
    out = Path(expand(plan['out']))
    if out.exists():
        sys.exit(f'output root {out} exists; every run gets a new directory')
    if args.detach:
        out.parent.mkdir(parents=True, exist_ok=True)
        log = out.parent / f'{out.name}.board-run.log'
        with open(log, 'w') as fh:
            child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), str(args.plan.resolve())],
                                     cwd=REPO, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                     start_new_session=True)
        print(f'board_run detached: pid {child.pid}, log {log}'); return 0
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda signum, frame: sys.exit(128 + signum))
    out.mkdir(parents=True)
    rc = subprocess.run([note, 'lock', plan['board'], plan['serial'], plan['lane'],
                         f'#{plan["entry"]} {plan["why"]} (board_run.py)']).returncode
    held = subprocess.run([note, 'held', plan['serial']], capture_output=True, text=True).stdout.split()
    if rc or not held or held[0] != plan['lane']:
        sys.exit(f'could not take the board lock for {plan["serial"]} (held: {" ".join(held) or "none"})')
    result = {'smoke': None, 'shards': []}
    try:
        if deploy:
            with open(out / 'after-lock.log', 'w') as fh:
                result['after_lock'] = subprocess.run([os.path.expandvars(x) for x in deploy], cwd=REPO,
                                                      stdout=fh, stderr=subprocess.STDOUT).returncode
            if result['after_lock']:
                board_append(plan, f'PROGRESS({plan["entry"]}): {plan["lane"]} board_run after_lock(部署)失败 '
                                   f'rc={result["after_lock"]}({out / "after-lock.log"});不跑冒烟和分片')
                return 1
        smoke = subprocess.run([sys.executable, str(HERE / 'activation_smoke.py'), '--spec', expand(plan['smoke_spec']),
                                '--serial', plan['serial'], '--lane', plan['lane'], '--out', str(out / 'smoke')])
        result['smoke'] = smoke.returncode
        verdict = 'PASS' if smoke.returncode == 0 else 'FAIL'
        board_append(plan, f'PROGRESS({plan["entry"]}): {plan["lane"]} board_run 生效冒烟 {verdict} '
                           f'({out / "smoke/smoke-result.json"});{"开始分片" if verdict == "PASS" else "停,不跑全量"}')
        if smoke.returncode != 0:
            return 1
        for shard in plan['shards']:
            keys = Path(expand(shard['keys_file'])).read_text().strip()
            sout = out / shard['name']
            cmd = [sys.executable, str(BATCH), '--execute', '--serial', plan['serial'], '--lane', plan['lane'],
                   '--manifest', expand(shard['manifest']), '--input-root', expand(shard['input_root']),
                   '--keys', keys, '--reinstall', '--hilog', '--shots', '5,20', '--out', str(sout)]
            with open(out / f'{shard["name"]}.log', 'w') as fh:
                code = subprocess.run(cmd, cwd=REPO, stdout=fh, stderr=subprocess.STDOUT).returncode
            facts = sorted(sout.glob('*/*/facts.txt'))
            total = facts[0].read_text().strip().splitlines()[-1] if facts else f'no facts.txt (rc={code})'
            result['shards'].append({'name': shard['name'], 'rc': code, 'facts': str(facts[0]) if facts else None,
                                     'total': total})
            board_append(plan, f'PROGRESS({plan["entry"]}): {plan["lane"]} board_run 分片 {shard["name"]} '
                               f'({facts[0] if facts else sout}):「{total}」')
        return 0
    finally:
        cleanup_error = None
        if cleanup:
            try:
                with open(out / 'before-unlock.log', 'w') as fh:
                    code = subprocess.run([os.path.expandvars(x) for x in cleanup], cwd=REPO,
                                          stdout=fh, stderr=subprocess.STDOUT).returncode
                result['before_unlock'] = code
                if code:
                    cleanup_error = f'before_unlock failed (rc={code}); lock retained for recovery'
            except Exception as exc:
                cleanup_error = f'before_unlock failed: {exc}; lock retained for recovery'
                result['before_unlock_error'] = str(exc)
        (out / 'board-run-result.json').write_text(json.dumps(result, indent=1, ensure_ascii=False))
        if cleanup_error:
            board_append(plan, f'PROGRESS({plan["entry"]}): {plan["lane"]} {cleanup_error}')
            raise RuntimeError(cleanup_error)
        subprocess.run([note, 'unlock', plan['board'], plan['serial'], plan['lane']])


if __name__ == '__main__':
    sys.exit(main())
