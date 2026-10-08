import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORKSPACES = Path(os.environ.get('WORKSPACES', REPO.parent))
MASTER = WORKSPACES / 'westlake-harness'


def main():
    prefix = Path('benchmark/2026-10-03-u14-stage-b')
    for variant in ['common', '61b']:
        old = json.loads((MASTER / prefix / variant / 'composition.json').read_text())
        new = json.loads((REPO / prefix / variant / 'composition.json').read_text())
        old.pop('stage_a_selection')
        new.pop('stage_a_selection')
        if old != new:
            raise ValueError('Unrelated composition change: ' + variant)
    with tempfile.TemporaryDirectory() as directory:
        cold = Path(directory) / 'westlake-harness'
        shutil.copytree(MASTER / prefix, cold / prefix, ignore=shutil.ignore_patterns('.artifacts', '__pycache__'))
        for name in ['prepare.py', 'promotion_hook_u14_runtime.py', 'test_promotion_u14.py', 'README.md',
            'common/composition.json', '61b/composition.json', 'common/future-stage-a-decision-template.json',
            '61b/future-stage-a-decision-template.json', 'inputs/stage-a-selftest-source.txt', 'source-provenance.json']:
            shutil.copyfile(REPO / prefix / name, cold / prefix / name)
        for name, origin in [('scripts/lab/stage_a_selftest.py', REPO), ('scripts/lab/lab_paths.py', MASTER),
            ('benchmark/2026-10-03-u13-stage-a-plan/process_selftest.py', MASTER)]:
            target = cold / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin / name, target)
        task_path = Path('benchmark') / HERE.name
        shutil.copytree(HERE, cold / task_path, ignore=shutil.ignore_patterns('.artifacts', '__pycache__'))
        environment = dict(os.environ, WORKSPACES=str(WORKSPACES))
        for name in [prefix / 'test_promotion_u14.py', task_path / 'test_selector.py']:
            result = subprocess.run([sys.executable, str(cold / name), '-v'], cwd=cold, env=environment,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            print(result.stdout, end='')
            print('cold_' + name.name + '_exit=' + str(result.returncode))
            if result.returncode:
                return result.returncode
    print('composition_nonselection_fields_equal=2/2; cold_master_overlay_exit=0; no .artifacts dependency')
    return 0


if __name__ == '__main__':
    sys.exit(main())
