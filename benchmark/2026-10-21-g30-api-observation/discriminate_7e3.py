#!/usr/bin/env python3
"""Show the G33 revision's positive case discriminates: the original 7e3c3e6cbc checker (with its own card
files and observations) refuses a source root that only adds a later genuine-shaped G30 remote receipt;
the revised checker accepts the same root. Offline; uses git archive/show; no device, REA or build."""
import importlib.util, io, json, shutil, subprocess, sys, tarfile, tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = '7e3c3e6cbc61f3114296acc6ee16e85da153f860'
CARD = 'benchmark/2026-10-21-g30-api-observation'

def git(*a):
    return subprocess.run(['git', '-C', str(ROOT), *a], capture_output=True, check=True).stdout

def main():
    spec = importlib.util.spec_from_file_location('g33_new', HERE / 'check_observation.py')
    new = importlib.util.module_from_spec(spec); spec.loader.exec_module(new)
    with tempfile.TemporaryDirectory(prefix='g33-7e3-') as t:
        tarfile.open(fileobj=io.BytesIO(git('archive', OLD, CARD))).extractall(t, filter='data')
        od = Path(t) / CARD
        src = (od / 'check_observation.py').read_text()
        src = src.replace('HERE = Path(__file__).resolve().parent', f'HERE = Path({str(od)!r})').replace('ROOT = HERE.parents[1]', f'ROOT = Path({str(ROOT)!r})')
        old = type(sys)('g33_7e3'); exec(compile(src, 'g33_7e3', 'exec'), old.__dict__)
        data_old = json.loads(git('show', f'{OLD}:benchmark/2026-10-19-api-progress-update/observations.json'))
        data_new = new.old.read(new.API / 'observations.json')
        later = new.later_receipt_root(ROOT)
        out = {'old_commit': OLD}
        try:
            out['old_checker_current_root'] = old.check(data_old, ROOT, False)
            try: old.check(data_old, later, False); out['old_checker_later_receipt_root'] = 'ACCEPTED'
            except ValueError as e: out['old_checker_later_receipt_root'] = f'REFUSED: {e}'
            out['new_checker_later_receipt_root'] = new.check(data_new, later, False)
        finally:
            shutil.rmtree(later)
    assert out['old_checker_later_receipt_root'].startswith('REFUSED') and out['new_checker_later_receipt_root'] == out['old_checker_current_root']
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
