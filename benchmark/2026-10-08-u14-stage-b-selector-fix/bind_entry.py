import collections
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORKSPACES = Path(os.environ.get('WORKSPACES', REPO.parent))
STAGE_B = REPO / 'benchmark/2026-10-03-u14-stage-b'
TAG = '2026-10-03-u14-stage-a-plan'
sys.path.insert(0, str(STAGE_B))
import promotion_hook_u14_runtime as hook


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


def save(name, value):
    target = HERE / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(portable(value), indent=2, ensure_ascii=False) + '\n')


def main():
    folder = HERE / '.artifacts/cli'
    files = {kind: folder / (TAG + '-' + kind + '.json') for kind in ['selftest', 'explanations', 'summary', 'selection']}
    values = {kind: json.loads(source.read_text()) for kind, source in files.items()}
    exits = json.loads((HERE / '.artifacts/exit-codes.json').read_text())
    if exits != dict(union_cli_exit=0, legacy_cli_exit=1, mixed_control_cli_exit=1):
        raise ValueError('Fresh expected CLI exits changed')
    summary = values['summary']
    if summary['records'] != 348 or summary['excluded'] != dict(zip(
            ['known-answer', 'recovery-smoke', 'evidence-copy', 'symlink', 'executor-state', 'U13-control'], [0, 72, 6, 0, 125, 14])):
        raise ValueError('Reviewed windows 1–6 domain changed; request a new selection receipt')
    if summary['report_sha256'] != sha(files['selftest']) or summary['failure_lines_any_pid'] != 0:
        raise ValueError('Fresh report binding or any-PID rescan failed')
    tool = REPO / 'scripts/lab/stage_a_selftest.py'
    entry_checks = {}
    for variant in ['common', '61b']:
        template = json.loads((STAGE_B / variant / 'future-stage-a-decision-template.json').read_text())
        template.update(signed_by=None, signed_at=None, promotion_authorized=None)
        template['process_selftest_gate'] = dict(report=str(files['selftest']), report_sha256=sha(files['selftest']),
            explanations=str(files['explanations']), explanations_sha256=sha(files['explanations']),
            summary=str(files['summary']), summary_sha256=sha(files['summary']), root=summary['root'],
            pattern=summary['pattern'], selector=summary['selector'],
            measured_records=[row['record'] for row in values['selftest']['runs']],
            tool=dict(path='$WORKSPACES/westlake-harness/scripts/lab/stage_a_selftest.py', sha256=sha(tool), exit_code=0))
        template['binding_status'] = 'Unsigned entry preview; operational absolute-path outputs remain in lane .artifacts; outer must sign separately after landing this exact tool'
        save('entry-' + variant + '.json', template)
        preview = json.loads((HERE / ('entry-' + variant + '.json')).read_text())
        composition = json.loads((STAGE_B / variant / 'composition.json').read_text())
        reference = json.loads((STAGE_B / 'inputs/reference.json').read_text())
        reason = hook.retention_reason(preview, composition, reference, dict(passed=True))
        if reason != 'outer screenshot signoff absent':
            raise ValueError('Unsigned entry wiring failed for ' + variant + ': ' + str(reason))
        entry_checks[variant] = reason
    missing = []
    by_window = collections.Counter()
    for run in values['selftest']['runs']:
        relative = Path(run['record']).relative_to(summary['root'])
        by_window[relative.parts[0]] += 1
        if run['hilog_sha256'] is None:
            missing.append(dict(record=run['record'], key=run['key'], status=run['status']))
    save('selection.json', values['selection'])
    save('summary.json', summary)
    save('results.json', dict(execution_enabled=False, board_access=False, promotion_authorized=None,
        **exits, selected=summary['records'],
        excluded=summary['excluded'], excluded_total=sum(summary['excluded'].values()), by_window=dict(by_window),
        PASS=summary['PASS'], unknown=summary['unknown'], REJECT=summary['REJECT'], explanations=summary['explanations'],
        all_pid_failure_records=summary['failure_lines_any_pid'], missing_hilog=missing,
        unsigned_entry_checks=entry_checks,
        report_sha256=sha(files['selftest']), selection_sha256=summary['selection_sha256'], tool_sha256=sha(tool),
        outputs={kind: dict(path=str(source), sha256=sha(source)) for kind, source in files.items()},
        raw_outputs={name: dict(path=str(HERE / '.artifacts' / name), sha256=sha(HERE / '.artifacts' / name))
            for name in ['cli-stdout.txt', 'cli-stderr.txt', 'legacy-stdout.txt', 'legacy-stderr.txt', 'control-stdout.txt', 'control-stderr.txt']}))
    print('entry_rebind_exit=0; common/61b unsigned; gates and promotion authority unchanged')


if __name__ == '__main__':
    main()
