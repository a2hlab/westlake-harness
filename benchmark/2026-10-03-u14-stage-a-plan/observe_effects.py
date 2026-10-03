"""U14 record-only M6 readout after each shard, retaining schema2 assessment."""
import importlib.util
import json
from pathlib import Path
import re
import sys

H = Path(__file__).resolve().parent
W = H.parents[2]
path = W / 'westlake-harness/benchmark/2026-10-03-u13-stage-a-plan/observe.py'
sys.path.insert(0, str(path.parent))
spec = importlib.util.spec_from_file_location('u14_schema2_observer', path)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

MARKER = 'FGGUARD WARN pass-through BACKGROUND_NEW for finishing token='


def effect_report(root):
    rows = []
    for record in sorted(root.rglob('record.json')):
        key = record.parent.name
        log = record.parent / 'hilog.txt'
        text = log.read_text(errors='replace') if log.exists() else ''
        lines = [line for line in text.splitlines() if MARKER in line]
        if key not in {'fd-AppManager', 'termux'} and not lines:
            continue
        rows.append({'key': key, 'marker_count': len(lines), 'marker_lines': lines,
                     'status': 'observed' if lines else 'untriggered/unknown',
                     'transition_lines': [line for line in text.splitlines()
                                          if re.search(r'CompleteBackground|delay complete terminate task|CompleteTerminate', line)]})
    return {'record_only': True, 'activation_veto': False, 'fix': 'U14-BRIDGE-M6', 'runs': rows}


def main(argv=None):
    args = base.argparse.ArgumentParser()
    args.add_argument('mode', choices=['shard'])
    args.add_argument('--plan', type=Path, required=True)
    args.add_argument('--root', type=Path, required=True)
    args.add_argument('--out', type=Path, required=True)
    args.add_argument('--name', required=True)
    a = args.parse_args(argv)
    plan = json.loads(a.plan.read_text())
    # The previously accepted crypto observation remains unchanged and non-vetoing.
    base.assess(plan, a.root, a.out, a.name)
    try:
        data = effect_report(a.root)
    except Exception as exc:
        data = {'record_only': True, 'activation_veto': False, 'fix': 'U14-BRIDGE-M6',
                'runs': [], 'status': 'unknown', 'error': str(exc)}
    destination = a.out.with_name(a.out.stem + '-m6.json')
    destination.write_text(json.dumps(data, indent=2) + '\n')
    if data['runs'] or data.get('error'):
        base.ack(plan, a.name + ' M6 record-only: ' + json.dumps(data, ensure_ascii=False))
    print(json.dumps(data, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
