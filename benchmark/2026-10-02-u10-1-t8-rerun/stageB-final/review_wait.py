"""Wait for an outer, fresh-window promotion signature; expiry always finishes U9."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

H = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('promotion_hook', H / 'promotion_hook.py')
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


def wait_for_decision(path, deadline, now=time.time, sleep=time.sleep):
    while now() < deadline:
        if path.is_file():
            try:
                json.loads(path.read_text())  # an interrupted/partial write is not a decision
                return True
            except (ValueError, OSError):
                pass
        sleep(min(5, max(0, deadline - now())))
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    root = args.root
    smoke_path = root / 'runner/smoke/smoke-result.json'
    identity_path = root / 'post-apply/candidate-318.json'
    decision = root / 'outer-promotion.json'
    ready = (smoke_path.is_file() and json.loads(smoke_path.read_text()).get('passed') is True
             and identity_path.is_file() and not json.loads(identity_path.read_text()).get('diff')
             and not json.loads(identity_path.read_text()).get('absent'))
    try:
        if ready:
            # board_run creates runner immediately before acquiring the lock. Birthtime
            # is stable on the Mac; do not use its mtime (which changes during the sweep).
            stat = (root / 'runner').stat()
            started = getattr(stat, 'st_birthtime', (root / 'window-input.json').stat().st_mtime)
            # >=6min reserved for exact U9 rollback, 318 and recovery HW/ZZ.
            deadline = min(time.time() + 20 * 60, started + 24 * 60)
            shots = sorted(str(p) for p in (root / 'runner/smoke').glob('group-*/*/*/*/t20.jpeg'))
            hilogs = sorted(str(p) for p in (root / 'runner/toutiao-retest').glob('*/*/toutiao/hilog.txt'))
            receipt = {'serial': args.serial, 'window_root': str(root), 'decision_path': str(decision),
                       'smoke': str(smoke_path), 't20': shots, 'candidate_318': str(identity_path),
                       'identities': json.loads(identity_path.read_text()), 'toutiao_hilog': hilogs,
                       'wait_until_epoch': deadline, 'max_wait_seconds': 1200,
                       'rollback_reserve_minutes': 6}
            (root / 'approval-ready.json').write_text(json.dumps(receipt, indent=2) + '\n')
            text = (f"PROGRESS(90): cx-t0 阶段B {args.serial} 待外环鲜签；approval-ready={root / 'approval-ready.json'}；"
                    f"smoke={smoke_path}；t20={shots}；318/双指纹={identity_path}；头条hilog={hilogs}；"
                    f"请写 {decision}，最多等20min且锁起24min截止留6min恢复，无签finish U9。\n")
            subprocess.run(['bash', str(hook.R / 'scripts/lab/board_append.sh'),
                            str(hook.M / '.octos/boards/app-lighting.md')], input=text, text=True, check=True)
            print(text, flush=True)
            wait_for_decision(decision, deadline)
    finally:
        hook.finish(args.serial, root, Path(os.path.expandvars(plan['before_unlock_restored_spec'])), decision,
                    Path(os.path.expandvars(plan['stage_a_decision'])))


if __name__ == '__main__':
    main()
