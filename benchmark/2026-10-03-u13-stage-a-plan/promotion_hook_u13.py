"""DESIGN-ONLY U13 criteria, derived from promotion_hook_u12.retention_reason.

Keep U12 SHA/smoke/fresh outer review/identity checks at final binding. Change the
signed visual reference to U13's 122-key overlay; restoration remains U10.1T8.
Add process crypto selftests. This file has no apply/finish or device operations.
"""
import hashlib
import json
from pathlib import Path

def retention_reason(decision, composition, signed_reference, smoke, selftest_path, explanation_path=None):
    if not smoke or smoke.get('passed') is not True:
        return 'activation smoke did not pass'
    if not isinstance(decision, dict) or decision.get('signed_by') != 'outer(claude)':
        return 'outer screenshot signoff absent'
    if not composition.get('bundle_sha256') or not composition.get('native_manifest_sha256'):
        return 'final U13 package binding pending'
    if decision.get('bundle_sha256') != composition['bundle_sha256']:
        return 'signoff belongs to another bundle'
    if decision.get('native_manifest_sha256') != composition['native_manifest_sha256']:
        return 'signoff manifest mismatch'
    expected_lit = sum(row['verdict'] == 'lit' for row in signed_reference['keys'].values())
    if expected_lit != signed_reference['total_lit']:
        return 'signed reference count mismatch'
    verdict = decision.get('stage_A_regression_verdict', {})
    if verdict.get('u13_reference_lit_total') != expected_lit or verdict.get('measured') != expected_lit:
        return 'all signed U13-reference-lit keys must be measured'
    if verdict.get('same_or_lit_within_k_of_n') != expected_lit or verdict.get('confirmed_regressions') != 0:
        return 'Stage A k/n regression gate not passed'
    if decision.get('confirmed_regressions') != []:
        return 'outer confirmed a regression'
    if not selftest_path or not Path(selftest_path).is_file():
        return 'process selftest report absent'
    body = Path(selftest_path).read_bytes()
    data = json.loads(body)
    gate = decision.get('process_selftest_gate') or {}
    if gate.get('report_sha256') != hashlib.sha256(body).hexdigest():
        return 'process selftest report not bound by outer'
    if not data.get('runs') or len(data['runs']) != data.get('run_count'):
        return 'process selftest coverage absent'
    if set(gate.get('measured_records', [])) != {r['record'] for r in data['runs']}:
        return 'process selftest measured-record coverage mismatch'
    problems = [r for r in data['runs'] if r.get('status') != 'PASS' or
                r.get('validateAead_OK_count', 0) <= 0 or
                any(v.get('selftest_errors') for v in r.get('processes', {}).values())]
    if not problems:
        return None
    # Zero errors is the default. Nonzero/silent runs require individual exact
    # evidence-bound outer explanations; no wildcard or counter-only exception.
    if not explanation_path or not Path(explanation_path).is_file():
        return 'process selftest errors/unknowns require individual outer explanations'
    review = json.loads(Path(explanation_path).read_text())
    if (review.get('approved_by') != 'outer(claude)' or
        review.get('bundle_sha256') != composition['bundle_sha256'] or
        review.get('native_manifest_sha256') != composition['native_manifest_sha256'] or
        review.get('report_sha256') != gate.get('report_sha256')):
        return 'selftest explanations belong to another report/package'
    issues = {(r['record'], pid, e['line_sha256'], e.get('line_number')) for r in problems
              for pid, v in r.get('processes', {}).items() for e in v.get('selftest_errors', [])}
    issues |= {(r['record'], '*', 'unknown', None) for r in problems
               if not any(v.get('selftest_errors') for v in r.get('processes', {}).values())}
    explained = set()
    for row in review.get('explanations', []):
        evidence = Path(row.get('evidence', ''))
        if not row.get('reason') or not evidence.is_file():
            return 'selftest explanation evidence missing'
        if hashlib.sha256(evidence.read_bytes()).hexdigest() != row.get('evidence_sha256'):
            return 'selftest explanation evidence drift'
        explained.add((row.get('record'), row.get('pid'), row.get('line_sha256'), row.get('line_number')))
    if explained != issues:
        return 'not every selftest error/unknown has an exact outer explanation'
    return None
