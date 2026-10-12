#!/usr/bin/env python3
"""Read immutable Git blobs only; never import or execute candidate code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
WORKSPACES = HERE.parents[2]
REPOSITORY = WORKSPACES / 'westlake-harness-t0'
BASE = 'b093d8599aeffac5e4830bd2dc7f6c15806b8a28'
PREFIX = 'benchmark/2026-10-12-recovery-executor/'
REVIEWED_EXTERNAL_CODE = {
    'tools/spec-checks/tests/recovery_executor.rs': '9ad762e1af30d0031abe6e1116fb35a73dd2946521bc7b159e51f505b4be260e'
}


def git(*arguments):
    return subprocess.check_output(['git', '-C', str(REPOSITORY), *arguments])


def blob(commit, path):
    return git('show', commit + ':' + path)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def tree(commit, scope=PREFIX):
    result = {}
    for record in git('ls-tree', '-rz', commit, '--', scope).split(b'\0'):
        if not record:
            continue
        attributes, path = record.split(b'\t', 1)
        mode, kind, object_id = attributes.decode().split()
        result[path.decode()] = {'mode': mode, 'kind': kind, 'git_object': object_id}
    return result


def protected(path):
    return path.startswith(PREFIX + 'payload/') or path in [PREFIX + 'executor.py', PREFIX + 'prepare.py']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--out', required=True)
    arguments = parser.parse_args()
    assert re.fullmatch('[0-9a-f]{40}', arguments.commit), 'full immutable commit required'
    out = Path(arguments.out).resolve()
    assert out.is_relative_to(HERE), 'output must stay within review directory'
    assert not out.exists(), 'preserve earlier metadata receipt'
    assert subprocess.run(['git', '-C', str(REPOSITORY), 'merge-base', '--is-ancestor', BASE, arguments.commit]).returncode == 0
    baseline = tree(BASE)
    candidate = tree(arguments.commit)
    failures = []
    protected_rows = []
    changed = []
    code_changes = []
    for path in sorted(set(baseline) | set(candidate)):
        before = blob(BASE, path) if path in baseline else None
        after = blob(arguments.commit, path) if path in candidate else None
        same = before == after and baseline.get(path) == candidate.get(path)
        row = {'path': path, 'base_sha256': digest(before) if before is not None else None,
               'release_sha256': digest(after) if after is not None else None, 'identical': same}
        if protected(path):
            protected_rows.append(row)
            if not same:
                failures.append('protected byte/mode/member changed: ' + path)
        if not same:
            changed.append(row)
            suffix = Path(path).suffix
            if protected(path) or suffix in {'.py', '.sh', '.rs', '.c', '.cpp', '.h', '.so', '.jar', '.dex'} or (
                    after is not None and after.startswith(b'\x7fELF')):
                code_changes.append(row)
                failures.append('new/changed code cannot inherit b093 review: ' + path)
    manifest_bytes = blob(arguments.commit, PREFIX + 'checkpoint-manifest.json')
    external_changes = []
    for path in git('diff', '--name-only', BASE, arguments.commit).decode().splitlines():
        if not path.startswith(PREFIX):
            row = {'path': path, 'requires_separate_review': Path(path).suffix in {'.py', '.sh', '.rs', '.c', '.cpp', '.h', '.so', '.jar', '.dex'}}
            actual = blob(arguments.commit, path)
            row['sha256'] = digest(actual)
            row['independently_reviewed'] = REVIEWED_EXTERNAL_CODE.get(path) == row['sha256']
            if row['independently_reviewed']:
                row['review'] = 'Exact Rust wrapper: unchanged run/root and four selector names; adds CFGTests, FailureTests, StopTests from unchanged b093 test sources. No deployment behavior. Static review only, no rerun.'
            external_changes.append(row)
            if row['requires_separate_review'] and not row['independently_reviewed']:
                failures.append('code outside package changed; explicit review required: ' + path)
    manifest = json.loads(manifest_bytes)
    manifest_rows = []
    seen = set()
    for declared in manifest['files']:
        path = declared['path']
        if path in seen or not (path.startswith(PREFIX) or path in REVIEWED_EXTERNAL_CODE) or '..' in Path(path).parts:
            failures.append('duplicate/unsafe manifest path: ' + path)
            continue
        seen.add(path)
        entry = candidate.get(path) or tree(arguments.commit, path).get(path)
        actual = blob(arguments.commit, path) if entry is not None else None
        matches = actual is not None and digest(actual) == declared['sha256'] and len(actual) == declared['bytes']
        manifest_rows.append({'path': path, 'declared_sha256': declared['sha256'],
                              'git_sha256': digest(actual) if actual is not None else None, 'matches': matches})
        if not matches:
            failures.append('manifest mismatch/missing Git object: ' + path)
        if entry is not None and entry['mode'] not in {'100644', '100755'}:
            failures.append('manifest member not regular file: ' + path)
    final_manifest_bytes = blob(arguments.commit, PREFIX + 'final-manifest.json') if PREFIX + 'final-manifest.json' in candidate else None
    final_manifest = json.loads(final_manifest_bytes) if final_manifest_bytes is not None else {}
    if final_manifest_bytes is None:
        failures.append('release final manifest missing')
    if final_manifest.get('program_commit') != BASE:
        failures.append('final manifest program commit not reviewed b093')
    final_rows = []
    final_seen = set()
    for declared in final_manifest.get('files', []):
        path = declared['path']
        if path in final_seen or not (path.startswith(PREFIX) or path in REVIEWED_EXTERNAL_CODE) or '..' in Path(path).parts:
            failures.append('duplicate/unsafe final manifest path: ' + path)
            continue
        final_seen.add(path)
        entry = candidate.get(path) or tree(arguments.commit, path).get(path)
        actual = blob(arguments.commit, path) if entry is not None else None
        matches = actual is not None and digest(actual) == declared['sha256'] and len(actual) == declared['bytes']
        final_rows.append({'path': path, 'declared_sha256': declared['sha256'],
                           'git_sha256': digest(actual) if actual is not None else None, 'matches': matches})
        if not matches:
            failures.append('final manifest mismatch/missing Git object: ' + path)
        if entry is not None and entry['mode'] not in {'100644', '100755'}:
            failures.append('final manifest member not regular file: ' + path)
    required = {path for path in candidate if protected(path) or Path(path).suffix in {'.py', '.sh', '.rs', '.c', '.cpp', '.h'}}
    missing = sorted(required - seen)
    failures.extend('code omitted from manifest: ' + path for path in missing)
    failures.extend('code omitted from final manifest: ' + path for path in sorted(required - final_seen))
    plan_bytes = blob(arguments.commit, PREFIX + 'plan.disabled.json')
    plan = json.loads(plan_bytes)
    base_plan = json.loads(blob(BASE, PREFIX + 'plan.disabled.json'))
    if plan != base_plan:
        failures.append('plan semantics differ from reviewed b093; explicit review required')
    if plan['execution_enabled'] is not False:
        failures.append('release plan not disabled')
    members = []
    for row in plan['members']:
        source = row['source']
        if not source.startswith('$PACKAGE/'):
            failures.append('external member source requires separate binding: ' + source)
            continue
        path = PREFIX + source.removeprefix('$PACKAGE/')
        actual = blob(arguments.commit, path)
        matches = digest(actual) == row['sha256']
        members.append({'target': row['target'], 'source': path, 'sha256': digest(actual), 'matches': matches})
        if not matches:
            failures.append('plan member digest mismatch: ' + path)
    result = dict(schema='t5-metadata-only-release-review/v1', base_commit=BASE, release_commit=arguments.commit,
                  executor_sha256=digest(blob(arguments.commit, PREFIX + 'executor.py')),
                  manifest_sha256=digest(manifest_bytes), plan_sha256=digest(plan_bytes),
                  final_manifest_sha256=digest(final_manifest_bytes) if final_manifest_bytes is not None else None, final_manifest_rows=final_rows,
                  protected_files=protected_rows, manifest_rows=manifest_rows, plan_members=members,
                  changed_files=changed, code_changes=code_changes, missing_code_from_manifest=missing,
                  external_changes=external_changes,
                  failures=failures, offline_inheritance_pass=not failures,
                  recommendation='offline metadata closure permits outer-controlled admission checks' if not failures else 'BLOCK release inheritance',
                  board_approval=False, ui_accepted=False, seal_signed=False, candidate_executions=0)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'commit': arguments.commit, 'protected': len(protected_rows),
                      'manifest': len(manifest_rows), 'plan_members': len(members),
                      'final_manifest': len(final_rows),
                      'code_changes': len(code_changes), 'failures': failures, 'exit': 0 if not failures else 2}))
    return 0 if not failures else 2


if __name__ == '__main__':
    raise SystemExit(main())
