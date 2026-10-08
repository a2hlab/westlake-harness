import argparse
import collections
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
WORKSPACES = Path(os.environ.get('WORKSPACES', HERE.parents[2]))
MASTER = WORKSPACES / 'westlake-harness'
ROOT = WORKSPACES / 'westlake-harness-u7-executor/benchmark/2026-10-03-u14-stage-a-plan'
SELECTION = 'window[1-6]/u14-A*/{board}/{runner,candidate[-rN]/runner}/**/record.json; physical candidate only'
sys.path.insert(0, str(MASTER / 'scripts/lab'))
import stage_a_selftest as aggregate


def load_module(name, source):
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


criteria = load_module('u14_decision_criteria', MASTER / 'benchmark/2026-10-03-u14-stage-b/retention_criteria.py')


def sha(source):
    return hashlib.sha256(Path(source).read_bytes()).hexdigest()


def portable(value):
    if isinstance(value, dict):
        return {portable(key): portable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, str):
        return value.replace(str(WORKSPACES) + '/', '$WORKSPACES/').replace(str(Path.home()) + '/', '$HOME/')
    return value


def expand(value):
    return Path(str(value).replace('$WORKSPACES/', str(WORKSPACES) + '/').replace('$HOME/', str(Path.home()) + '/'))


def write(folder, name, value):
    source = folder / name
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps(portable(value), ensure_ascii=False, indent=2) + '\n')
    return source


def record_class(root, source):
    relative = str(source.relative_to(root))
    if source.is_symlink() or any((root / parent).is_symlink() for parent in source.relative_to(root).parents if str(parent) != '.'):
        return 'symlink'
    if relative.startswith('evidence/'):
        return 'known-answer'
    if re.match(r'window[^/]*/(?:landing|evidence|contact-index[^/]*)/', relative):
        return 'evidence-copy'
    if '/recovery-smoke-' in relative:
        return 'recovery-smoke'
    if re.match(r'window[1-6](?:-[^/]*)?/u14-A[^/]*/(?:5ea|5cd|61b)/(?:runner/|candidate(?:-r\d+)?/runner/)', relative):
        return 'candidate'
    if '/control' in relative and '/runner/' in relative:
        return 'U13-control'
    if any('/' + part in relative for part in ['apply-device/', 'baseline/', 'post-apply/', 'final-', 'restored-', 'rollback-']):
        return 'executor-state'
    raise ValueError('unclassified record: ' + relative)


def select(root):
    selected, excluded = [], {name: [] for name in ['known-answer', 'recovery-smoke', 'evidence-copy', 'symlink', 'executor-state', 'U13-control']}
    for source in sorted(root.rglob('record.json')):
        kind = record_class(root, source)
        if kind == 'candidate':
            selected.append(source)
        else:
            excluded[kind].append(str(source.relative_to(root)))
    if not selected:
        raise ValueError('no physical candidate runner records')
    return selected, excluded


def interruption_reason(record, source):
    if (record.get('status') == 'batch_interrupted' and record.get('clicked') is False and
            record.get('error') == 'HDC lost remote status marker' and not record.get('screenshots') and
            not (source.parent / 'hilog.txt').exists()):
        return ('Interrupted before desktop click; HDC lost remote status marker, no hilog or screenshots. '
            'No probe observation: unknown, not crypto success. Window2 outer signoff attributes this attempt to 61b loss.')
    return None


def explain(run, pid):
    source = expand(run['record'])
    record = json.loads(source.read_text())
    reason = interruption_reason(record, source)
    if reason:
        return reason, source, 'pre-launch-board-loss'
    reason, evidence = aggregate.classify(run, pid)
    category = ('icon-locator' if 'icon-locator' in reason else 'icon-not-found' if 'icon of' in reason else
        'bound-then-left' if 'bound and logged' in reason else 'bind-failed' if 'bind FAILED' in reason else
        'pre-bind' if 'never completed' in reason or 'pre-bind init' in reason else 'spawned-after-dump')
    return reason, evidence, category


def aggregate_records(root, folder):
    selected, excluded = select(root)
    report = aggregate.ps.report(aggregate.Selected(selected))
    for run in report['runs']:
        run['processes'] = dict(sorted(run['processes'].items(), key=lambda pair: int(pair[0])))
    explanation_rows, failure_rows, source_rows = [], [], []
    issue_records = {run['record'] for run, _ in aggregate.issues(report)}
    log_cache = {}
    for run in report['runs']:
        source = Path(run['record'])
        log = source.parent / 'hilog.txt'
        text = log.read_text(errors='replace') if log.exists() else ''
        lines = text.splitlines()
        if run['record'] in issue_records:
            log_cache[run['record']] = lines
        for number in aggregate.failure_lines_any_pid(lines):
            line = lines[number - 1]
            failure_rows.append(dict(record=run['record'], key=run['key'], source=str(log), line_number=number,
                text=line, line_sha256=hashlib.sha256(line.encode()).hexdigest()))
        process_files = [dict(path=str(item), sha256=sha(item)) for item in sorted(source.parent.glob('processes-t*.txt'))]
        source_rows.append(dict(record=str(source), record_sha256=sha(source), key=run['key'],
            window=source.relative_to(root).parts[0], hilog=str(log), hilog_sha256=sha(log) if log.exists() else None,
            process_files=process_files))
    for run, pid in aggregate.issues(report):
        reason, evidence, category = explain(run, pid)
        relevant = []
        for number, line in enumerate(log_cache[run['record']], 1):
            match = aggregate.ROW.match(line)
            if (pid == '*' or match and match[2] == pid) and any(marker in line for marker in
                    ['FilterAppTrace', aggregate.BOUND, aggregate.BIND_FAILED, '[WL-KS-PROBE]', 'Caused by:']):
                relevant.append(dict(source=str(evidence), line_number=number, text=line,
                    line_sha256=hashlib.sha256(line.encode()).hexdigest()))
        if not relevant:
            lines = evidence.read_text(errors='replace').splitlines()
            indices = [number for number, line in enumerate(lines, 1) if any(field in line for field in
                ['"status":', '"clicked":', '"error":', '"screenshots":'])] if evidence.name == 'record.json' else [len(lines)]
            for number in indices:
                if number:
                    line = lines[number - 1]
                    relevant.append(dict(source=str(evidence), line_number=number, text=line,
                        line_sha256=hashlib.sha256(line.encode()).hexdigest()))
        process_evidence = []
        for source in sorted(expand(run['record']).parent.glob('processes-t*.txt')):
            for number, line in enumerate(source.read_text(errors='replace').splitlines(), 1):
                fields = line.split()
                if fields and fields[0] == pid:
                    process_evidence.append(dict(source=str(source), sha256=sha(source), line_number=number,
                        text=line, line_sha256=hashlib.sha256(line.encode()).hexdigest()))
        explanation_rows.append(dict(record=run['record'], key=run['key'], pid=pid, line_sha256='unknown',
            line_number=None, reason=reason, evidence=str(evidence), evidence_sha256=sha(evidence),
            category=category, evidence_lines=relevant[:12], process_evidence=process_evidence, decision='pending'))
    report_path = write(folder, 'selftest-u14-stage-a.json', report)
    summary = dict(root=str(root), pattern=SELECTION, records=len(selected),
        PASS=sum(run['status'] == 'PASS' for run in report['runs']), unknown=report['unknown_runs'],
        REJECT=sum(run['status'] == 'REJECT' for run in report['runs']),
        error_count=report['error_count'], validateAead_OK_count=report['validateAead_OK_count'],
        hilog_records_scanned=sum(row['hilog_sha256'] is not None for row in source_rows),
        hilog_records_missing=sum(row['hilog_sha256'] is None for row in source_rows),
        failure_lines_any_pid=len(failure_rows), explanations=len(explanation_rows), report_sha256=sha(report_path),
        excluded={key: len(value) for key, value in excluded.items()},
        windows=dict(collections.Counter(source.relative_to(root).parts[0] for source in selected)))
    write(folder, 'selftest-summary.json', summary)
    write(folder, 'record-selection.json', dict(root=str(root), pattern=SELECTION,
        selected=[str(source) for source in selected], excluded=excluded,
        legacy_direct_runner_count=len(list(root.glob('window*/u14-A*/*/runner/**/record.json'))),
        complete_candidate_count=len(selected)))
    write(folder, 'source-receipts.json', dict(records=source_rows))
    write(folder, 'any-pid-failures.json', dict(failure_count=len(failure_rows), failures=failure_rows))
    return report_path, summary, explanation_rows


def visual_inputs(folder):
    reference_path = MASTER / 'benchmark/2026-10-03-u14-stage-b/inputs/reference.json'
    reference = json.loads(reference_path.read_text())
    lit = {key for key, row in reference['keys'].items() if row['verdict'] == 'lit'}
    signed_lit, signed_rows, gains, lottery, receipts = set(), {}, {}, {}, []
    for window in range(1, 6):
        source = MASTER / f'benchmark/2026-10-03-u14-stage-a-plan/window{window}-signoff/outer-signoff.json'
        signoff = json.loads(source.read_text())
        if signoff['signer'] != 'outer(claude)':
            raise ValueError('unexpected signoff signer')
        receipts.append(dict(path=str(source), sha256=sha(source), signed_at=signoff['signed_at']))
        write(folder, f'inputs/window{window}-outer-signoff.json', signoff)
        for key, row in signoff['keys'].items():
            signed_rows.setdefault(key, []).append(dict(window=window, signoff=str(source), **row))
            if row.get('lit_runs', 0) > 0 and key in lit:
                signed_lit.add(key)
            if row.get('runs', 0) > 1 or row.get('unmeasured'):
                entry = lottery.setdefault(key, dict(k=0, n=0, unmeasured=[], windows=[]))
                entry['k'] += row['lit_runs']
                entry['n'] += row['runs']
                entry['unmeasured'] += row.get('unmeasured', [])
                entry['windows'].append(window)
        gains.update(signoff.get('summary', {}).get('gains', {}))
    board = MASTER / '.octos/boards/app-lighting.md'
    lines = board.read_text(errors='backslashreplace').splitlines()
    matched = [(number, line) for number, line in enumerate(lines, 1)
        if line.startswith('ACK(90 observed): 外环') and '补签 U14 窗6 OrganicMaps' in line and '板相关白窗、未定' in line]
    if len(matched) != 1:
        raise ValueError('window6 outer verdict not uniquely identified')
    number, line = matched[0]
    window6 = dict(source=str(board), line_number=number, text=line,
        line_sha256=hashlib.sha256(line.encode()).hexdigest(), verdict='板相关白窗、未定',
        confirmed_regression=False, candidate=dict(k=0, n=4), U13_control=dict(k=1, n=2),
        prior_window5_candidate=dict(k=0, n=1), candidate_all_observed=dict(k=0, n=5),
        note='5ea U13 t20 splash becomes blank at t40; 5cd U13 control also blank; await same-reference-board 61b comparison.')
    missing = sorted(lit - signed_lit)
    if len(lit) != 126 or len(signed_lit) != 124 or missing != ['fd-organicmaps', 'fd-seal']:
        raise ValueError('signed visual coverage drift: ' + str((len(lit), len(signed_lit), missing)))
    observed = sorted(key for key in lit if any(row.get('runs', 0) > 0 for row in signed_rows.get(key, [])))
    body = dict(reference_total=len(lit), observed_reference_keys=len(observed), observed_reference_key_list=observed,
        measured_lit=len(signed_lit), measured_lit_keys=sorted(signed_lit), candidate_signed_lit_keys=len(signed_lit) + len(gains),
        pending_keys=missing, signed_rows=signed_rows, lottery=lottery, gains=gains, window6=window6,
        confirmed_regressions=[], signoff_receipts=receipts, reference_source=str(reference_path), reference_sha256=sha(reference_path))
    write(folder, 'visual-summary.json', body)
    reference_snapshot = folder / 'inputs/reference.json'
    reference_snapshot.parent.mkdir(parents=True, exist_ok=True)
    reference_snapshot.write_bytes(reference_path.read_bytes())
    write(folder, 'inputs/window6-outer-verdict.json', window6)
    return body, reference_path


def packet_reason(decision, composition, reference, folder):
    if decision.get('bundle_sha256') != composition['bundle_sha256']:
        return 'signoff belongs to another bundle'
    gate = decision['process_selftest_gate']
    report_path = folder / 'selftest-u14-stage-a.json'
    explanation_path = folder / decision['explanations_file']
    summary_path = folder / 'selftest-summary.json'
    if sha(report_path) != gate['report_sha256']:
        return 'process selftest report not bound by outer'
    if sha(explanation_path) != gate['explanations_sha256'] or sha(summary_path) != gate['summary_sha256']:
        return 'selftest explanations/summary binding drift'
    summary = json.loads(summary_path.read_text())
    if summary['failure_lines_any_pid']:
        return 'any-pid selftest failure unconditionally rejects promotion'
    if summary['report_sha256'] != sha(report_path):
        return 'selftest summary report binding drift'
    review = json.loads(explanation_path.read_text())
    for row in review['explanations']:
        row['evidence'] = str(expand(row['evidence']))
    with tempfile.TemporaryDirectory() as temporary:
        expanded = Path(temporary) / 'explanations.json'
        expanded.write_text(json.dumps(review))
        reason = criteria.retention_reason(decision, composition, reference, {'passed': True}, report_path, expanded)
    if reason:
        return reason
    if not decision.get('signed_at') or decision.get('promotion_authorized') is not True:
        return 'promotion not authorized by outer'
    return None


def build(folder, root):
    folder.mkdir(parents=True, exist_ok=True)
    report_path, summary, rows = aggregate_records(root, folder)
    visual, reference_path = visual_inputs(folder)
    reference = json.loads(reference_path.read_text())
    results = {}
    for tag in ['common', '61b']:
        composition_path = MASTER / f'benchmark/2026-10-03-u14-stage-b/{tag}/composition.json'
        composition = json.loads(composition_path.read_text())
        write(folder, f'inputs/composition-{tag}.json', composition)
        explanations = dict(schema='outer-selftest-explanations/v1', approved_by=None, approved_at=None,
            bundle_sha256=composition['approved_unarmed_bundle_sha256'], armed_bundle_sha256=composition['bundle_sha256'],
            native_manifest_sha256=composition['native_manifest_sha256'], report_sha256=sha(report_path), explanations=rows)
        explanation_name = f'selftest-explanations-{tag}.json'
        explanation_path = write(folder, explanation_name, explanations)
        decision = dict(schema='outer-stage-a/v1', release='U14', phase='A', signed_by=None, signed_at=None,
            promotion_authorized=None, execution_enabled=False,
            bundle_sha256=composition['approved_unarmed_bundle_sha256'], armed_bundle_sha256=composition['bundle_sha256'],
            native_manifest_sha256=composition['native_manifest_sha256'], native_inputs_sha256=composition['native_inputs_sha256'],
            effective_baseline_bundle_sha256=composition['base_bundle_sha256'], reference_sha256=sha(reference_path),
            explanations_file=explanation_name, confirmed_regressions=[],
            stage_A_regression_verdict=dict(u14_reference_lit_total=126, measured=visual['observed_reference_keys'],
                same_or_lit_within_k_of_n=124, confirmed_regressions=0),
            gains=visual['gains'], lottery=visual['lottery'], unresolved=visual['pending_keys'],
            process_selftest_gate=dict(report=str(report_path), report_sha256=sha(report_path),
                explanations=str(explanation_path), explanations_sha256=sha(explanation_path),
                summary=str(folder / 'selftest-summary.json'), summary_sha256=sha(folder / 'selftest-summary.json'),
                root=str(root), pattern=SELECTION, measured_records=[run['record'] for run in json.loads(report_path.read_text())['runs']],
                tool=dict(path=str(MASTER / 'scripts/lab/stage_a_selftest.py'), sha256=sha(MASTER / 'scripts/lab/stage_a_selftest.py'),
                    exit_code=None, mode='library primitives; extended selector and board-loss explanation in build_decision.py'),
                aggregation_tool=dict(path=str(HERE / 'build_decision.py'), sha256=sha(HERE / 'build_decision.py'), exit_code=0)),
            pending=dict(fd_seal=dict(board='61b', candidate_record=None, outer_signoff=None, k=None, n=None,
                    candidate_record_sha256=None, candidate_t20=None, candidate_t20_sha256=None,
                    reference_t20=reference['keys']['fd-seal']['t20'], reference_t20_sha256=reference['keys']['fd-seal']['t20_sha256'],
                    criterion='After restoration, a fresh U14 candidate fd-seal run on61b, exact record/shot hashes and outer lit signature; never reuse U13 reference as U14 evidence.'),
                fd_organicmaps=dict(board='61b reference board', verdict='板相关白窗、未定', candidate_k=0, candidate_n=4,
                    criterion='Fresh same-board U13 control vs U14 candidate k/n and outer decision; current white does not mean confirmed regression.')),
            outer_todo=['Complete fd-seal and resolve OrganicMaps; regenerate all report/explanation/SHA bindings.',
                f'Review{len(rows)} individual explanations; sign both package variants separately.',
                'StageB legacy direct-runner selector omits40 window6 candidate records: bind this extended domain before admission; original CLI exit is intentionally null, not fabricated.',
                'Fresh StageB controls, native tickets, identity and window signature remain mandatory; this draft is not permission to deploy.'],
            source_composition=dict(path=str(composition_path), sha256=sha(composition_path)))
        write(folder, f'decision-draft-{tag}.json', decision)
        comp = dict(bundle_sha256=decision['bundle_sha256'], native_manifest_sha256=decision['native_manifest_sha256'])
        results[tag] = packet_reason(decision, comp, json.loads(reference_path.read_text()), folder)
    result = dict(offline_only=True, execution_enabled=False, promotion_authorized=None,
        process_selftest=summary, explanation_categories=dict(collections.Counter(row['category'] for row in rows)),
        reference_lit=126, observed_reference_keys=visual['observed_reference_keys'], measured_lit=124,
        pending=visual['pending_keys'], readiness=results,
        source_tools=[dict(path=str(source), sha256=sha(source)) for source in [MASTER / 'scripts/lab/stage_a_selftest.py',
            MASTER / 'benchmark/2026-10-03-u13-stage-a-plan/process_selftest.py',
            MASTER / 'benchmark/2026-10-03-u14-stage-b/retention_criteria.py']])
    write(folder, 'results.json', result)
    print(json.dumps(portable(result), ensure_ascii=False, indent=2))
    return 1 if summary['error_count'] or summary['failure_lines_any_pid'] else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path, default=HERE)
    args = parser.parse_args()
    return build(args.out, args.root)


if __name__ == '__main__':
    raise SystemExit(main())
