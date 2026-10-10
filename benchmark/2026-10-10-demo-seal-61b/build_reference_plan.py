#!/usr/bin/env python3
"""Pin the original 61b t3 reference and partial 5cd Enforcing annotations, offline."""
import argparse
import importlib.util
import json
import os
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get('WORKSPACES', REPO.parent)).resolve()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', type=Path, default=HERE / 'plan-template.json')
    parser.add_argument('--out', type=Path, default=HERE / 'plan-reference-61b-t3.json')
    args = parser.parse_args()
    os.environ.setdefault('WORKSPACES', str(WS))
    seal = load('seal_reference_builder', REPO / 'scripts/lab/demo_seal_61b.py')
    comparator = load('regression_reference_builder', WS / 'westlake-harness/benchmark/2026-10-09-demo-baseline/t4/regress_vs_signoff.py')

    def resolve(value):
        return Path(str(value).replace('$WORKSPACES', str(WS)))

    def pin(path):
        path = Path(path)
        try:
            portable = '$REPO/' + path.relative_to(REPO).as_posix()
        except ValueError:
            portable = str(path).replace(str(WS) + '/', '$WORKSPACES/')
        return dict(path=portable, sha256=seal.sha(path))

    def write(path, value):
        path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n')

    signoff = WS / 'westlake-harness' / seal.T3_SIGNOFF_SUFFIX
    seal.require(seal.sha(signoff) == seal.T3_SIGNOFF_SHA, 'canonical t3 signoff drift')
    baseline = WS / 'westlake-harness/benchmark/2026-10-09-demo-baseline/t3'
    records = comparator.references(seal.read(signoff), baseline)
    index = dict(signoff_sha256=seal.sha(signoff), records={})
    for key, row in sorted(records.items()):
        record = resolve(row['record'])
        seal.require(seal.read(record).get('serial') == seal.SERIAL, 't3 record serial mismatch')
        index['records'][key] = dict(record=pin(record), image=pin(resolve(row['image'])), batch=row['batch'])
    source_repo = WS / 'westlake-harness-tools-inventory'
    source_root = source_repo / 'benchmark/2026-10-10-5cd-demo-regression'
    report_path = source_root / 'resume-organicmaps/compare-observed-89/comparison.json'
    report = seal.read(report_path)
    notes = dict(serial=seal.BASELINE_SERIAL, signoff_sha256=report['signoff_sha256'],
                 comparison=pin(report_path), enforce=pin(source_root / 'enforce-at-capture.txt'), keys={},
                 automatic_exemptions=0, caveat='Enforce=1 capture evidence is not a continuous per-key trace; changed is not a UI verdict.')
    for row in report['keys']:
        if row['category'] == 'missing':
            continue
        record = resolve(row['record'])
        if not record.is_absolute():
            record = source_repo / record
        record = record.resolve()
        metadata = seal.read(record)
        signature, image = comparator.signature(record)
        seal.require(metadata.get('serial') == seal.BASELINE_SERIAL and metadata.get('key') == row['key'] and
                     bool(metadata.get('finished_at')) and signature == row['signature'], '5cd observation drift: ' + row['key'])
        notes['keys'][row['key']] = dict(record=pin(record), category=row['category'], signature=signature,
                                        reason=row['reason'], semantic=row['semantic'])
    seal.require(len(index['records']) == 128 and len(notes['keys']) == 89, 'reference membership drift')
    index_path = HERE / 'evidence/reference-t3-index.json'
    notes_path = HERE / 'evidence/enforcing-prerun-89.json'
    write(index_path, index)
    write(notes_path, notes)
    plan = seal.read(args.template)
    plan.update(mode='v1', execution_enabled=False, driver_sha256=seal.sha(REPO / 'scripts/lab/demo_seal_61b.py'))
    plan['reference'] = dict(kind='61b-t3', signoff=pin(signoff), baseline_t3=str(baseline).replace(str(WS) + '/', '$WORKSPACES/'),
                             record_index=pin(index_path), enforcing_prerun=pin(notes_path))
    plan['pending'] = [item for item in plan['pending'] if 'fresh healthy 5cd' not in item]
    seal.validate_reference(plan, '61b-t3', index['records'])
    write(args.out, plan)
    print('REFERENCE_PINNED t3=128 enforcing_notes=89 execution_enabled=false plan_sha256=' + seal.sha(args.out))


if __name__ == '__main__':
    main()
