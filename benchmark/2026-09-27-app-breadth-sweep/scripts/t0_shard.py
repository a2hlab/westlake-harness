"""Run an explicitly assigned blocked-app shard only after production control admission."""
import argparse
import json
import subprocess
from pathlib import Path
import t0_collect as c
import t0_review as review
import t0_batch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('serial', choices=sorted(c.ALLOWED_SERIALS))
    ap.add_argument('run_id')
    ap.add_argument('control_run')
    ap.add_argument('reviews', type=Path)
    ap.add_argument('keys', help='comma-separated fixed-manifest app keys')
    args = ap.parse_args()
    c.SERIAL = args.serial
    root = Path(__file__).resolve().parents[3] / 'benchmark/2026-09-28-blocker-triage'
    if (root / 'stop-record.json').exists():
        raise SystemExit('REFUSE: T0 stopped under #16; boards handed back for BMS route')
    keys = args.keys.split(',')
    manifest = {r['key']: r for r in json.loads((root / 'manifest.json').read_text())['blocked']}
    if not keys or len(set(keys)) != len(keys) or any(k not in manifest for k in keys):
        ap.error('keys must be unique members of the 43-app manifest')
    admission = review.load_admission(root / 'runs' / args.control_run, args.serial, json.loads(args.reviews.read_text()))
    if not admission['eligible']:
        raise SystemExit('REFUSE: board without full signed control set: ' + json.dumps(admission))
    base = c.capture_ops.isolated_root(Path.home(), args.run_id) / args.serial
    base.mkdir(parents=True, exist_ok=True)
    if any(p.name not in ('base-audit', 'isolation-audit') for p in base.iterdir()):
        raise SystemExit('REFUSE: run already has attempts')
    c.save(base / 'admission.json', admission)
    def before(key):
        source = Path.home() / 'a2hlab/app-inputs' / key / 'app-input.json'
        if c.sha(source) != manifest[key]['input_sha256']:
            c.save(base / 'failure.json', {'key': key, 'error': 'fixed input identity changed; no launch'})
            raise RuntimeError('fixed input identity changed; no launch')
    def notify(n, key, state):
        command = c.TOOLS + 'board_note.sh progress /Users/zhaoyue/orca/workspaces/westlake-harness/.octos/boards/app-lighting.md 10 cx-t0 ' + c.shlex.quote(f'3/5 {args.serial[:8]} 分片 {n}/{len(keys)} {key} {state}')
        subprocess.run(['mac', 'bash', '-c', command], check=True)
    return t0_batch.run(keys, args.run_id, base, notify, before)


if __name__ == '__main__':
    raise SystemExit(main())
