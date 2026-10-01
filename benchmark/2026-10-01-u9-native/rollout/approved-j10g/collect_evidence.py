"""Copy small rollout receipts and index original screenshots without deleting them."""
import argparse
import csv
import json
import os
from pathlib import Path

H = Path(__file__).resolve().parent
W = Path(os.environ.get('WORKSPACES', H.parents[4]))


def portable(value):
    if isinstance(value, str):
        return value.replace(str(W), '$WORKSPACES')
    if isinstance(value, list):
        return [portable(v) for v in value]
    if isinstance(value, dict):
        return {k: portable(v) for k, v in value.items()}
    return value


def collect(board, plan_file=None):
    source = H / 'boards' / board
    plan = json.loads((plan_file or H / ('plan-' + board + '.json')).read_text())
    out = H / 'evidence' / board
    out.mkdir(parents=True, exist_ok=True)
    for name, path in [('smoke-result.json', source / 'runner/smoke/smoke-result.json'),
                       ('final-u9.json', source / 'final-u9.json'),
                       ('runner-result.json', source / 'runner/board-run-result.json')]:
        if path.exists():
            (out / name).write_text(json.dumps(portable(json.loads(path.read_text())), indent=2) + '\n')
    facts = []
    for shard in [s['name'] for s in plan['shards']]:
        for path in (source / 'runner' / shard).glob('*/*/facts.txt'):
            target = out / (shard + '-facts.txt')
            target.write_text(path.read_text())
            facts.append(str(target.relative_to(H)))
    screenshots = []
    for record in (source / 'runner').rglob('record.json'):
        if '/commands/' in str(record):
            continue
        data = json.loads(record.read_text())
        for shot in data.get('screenshots', []):
            if shot.get('captured'):
                screenshots.append({
                    'key': data.get('key', record.parent.name),
                    'run': portable(str(record.parent)),
                    'seconds': shot.get('scheduled_seconds'),
                    'path': portable(shot.get('path', '')),
                    'sha256': shot.get('sha256', ''),
                    'verdict': 'pending_outer_review',
                })
    with (out / 'screenshots.csv').open('w') as fh:
        writer = csv.DictWriter(fh, fieldnames=['key', 'run', 'seconds', 'path', 'sha256', 'verdict'])
        writer.writeheader()
        writer.writerows(screenshots)
    remaining = {}
    for shard in plan['shards']:
        attempted = {json.loads(p.read_text()).get('key', p.parent.name)
                     for p in (source / 'runner' / shard['name']).glob('*/*/*/record.json')}
        keys = Path(os.path.expandvars(shard['keys_file'])).read_text().split()
        remaining[shard['name']] = [k for k in keys if k not in attempted]
    (out / 'remaining.json').write_text(json.dumps(remaining, indent=2) + '\n')
    print(json.dumps({'board': board, 'facts': facts, 'remaining': {k: len(v) for k, v in remaining.items()}}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('board', choices=['5ea', '5cd', '61b', '5ea-r2-vm'])
    parser.add_argument('--plan', type=Path)
    args = parser.parse_args()
    collect(args.board, args.plan)
