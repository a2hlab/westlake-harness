#!/usr/bin/env python3
"""Apply the frozen J6/N4 rules to explicitly reviewed U5 first-attempt evidence."""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path

from collect import read, sha

HERE = Path(__file__).resolve().parent
SWEEP = HERE.parent
SPEC = importlib.util.spec_from_file_location('frozen_j6n4_predict', SWEEP / 'j6n4-predictions/predict.py')
FROZEN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FROZEN)


def references(log, needles):
    evidence = []
    for needle in needles:
        match = next((item for item in log if needle in item['text']), None)
        if not match:
            raise ValueError('review evidence missing: ' + needle)
        if match['line'] not in evidence:
            evidence.append(match['line'])
    return evidence


def build():
    FROZEN.verify_freeze(SWEEP, read(SWEEP / 'scoring-inputs/J6N4-predictions-reference.json'))
    forecast = read(SWEEP / 'j6n4-predictions/criteria.json')
    review = read(HERE / 'review.json')
    observations = {row['key']: row for row in read(HERE / 'evidence/observations.json')}
    if len(observations) != 66 or set(observations) != {row['key'] for row in forecast['rows']}:
        raise ValueError('incomplete or mixed cohort')
    rows = []
    checkpoint_rows = []
    for predicted in forecast['rows']:
        key = predicted['key']
        source = observations[key]
        log = read(HERE / 'evidence/logs' / (key + '.json'))
        ui = ('own-ui' if key in review['ui']['own_ui'] else
              'white' if key in review['ui']['white'] else
              'black' if key in review['ui']['black'] else
              'no-image' if key in review['ui']['no_image'] else 'desktop')
        observed = dict(identity_and_capture_valid=source['identity_and_capture_valid'],
            t20_sha256=source['t20_sha256'], outer_review=review['ui']['authority'],
            own_ui=(ui == 'own-ui') if source['t20_sha256'] else None,
            old_wall_evidence=source['old_exact_lines'][:1], checkpoints={})
        note = 'Exact normalized old wall reproduced in target PID.'
        if predicted['prediction'] == 'unknown':
            note = 'Frozen unknown remains outside the evaluable denominator; observed UI is still reported.'
        elif predicted['preservation_control']:
            note = 'First t20 preservation, not a new light.'
        elif not source['old_exact_lines']:
            note = 'No exact old-wall witness or reviewed positive crossing; unknown.'
        if key in review['special_cases']:
            note = review['special_cases'][key]['reason']
        for ident in predicted['fix_ids']:
            decision = dict(review['strict_checkpoint_states'][ident])
            partial = references(log, review['checkpoint_evidence_needles'][ident])
            decision['evidence'] = partial if decision['state'] == 'old-wall' else []
            decision['partial_evidence'] = partial
            observed['checkpoints'][ident] = decision
            single = dict(predicted, fix_ids=[ident])
            checkpoint_rows.append(dict(key=key, checkpoint=ident,
                verdict=FROZEN.score_reviewed(single, observed), **decision))
        if predicted['fix_ids']:
            note = ' '.join(observed['checkpoints'][ident]['reason'] for ident in predicted['fix_ids'])
        feedback = []
        for missed in review['missed_signatures']:
            if key in missed['keys']:
                feedback.append(dict(id=missed['id'], kind=missed['kind'], description=missed['description'],
                                     evidence=references(log, missed['needles'])))
        rechecks = []
        for ident in predicted['recheck_ids']:
            evidence = references(log, ['[B8-FETCH] alarm fetcher replaced'])
            rechecks.append(dict(checkpoint=ident, verdict='hit' if source['identity_and_capture_valid'] else 'unknown', evidence=evidence))
        rows.append(dict(key=key, prediction=predicted['prediction'], current_u4_wall=predicted['current_first_wall'],
            fix_ids=predicted['fix_ids'], preservation_control=predicted['preservation_control'],
            verdict=FROZEN.score_reviewed(predicted, observed), observed=observed, t20=ui,
            source=source, note=note, missed_signatures=feedback, auxiliary_rechecks=rechecks))
    counts = Counter(row['verdict'] for row in rows)
    checkpoint_counts = Counter(row['verdict'] for row in checkpoint_rows)
    groups = {prediction: dict(Counter(row['verdict'] for row in rows if row['prediction'] == prediction))
              for prediction in ('过墙', '不变', 'unknown')}
    pins = {str(path.relative_to(HERE)): sha(path.read_bytes()) for path in sorted(HERE.rglob('*'))
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.py', '.md')}
    return dict(schema=1, status='scored-under-unchanged-frozen-rules',
        prediction_sha256=sha((SWEEP / 'J6N4-PREDICTIONS.csv').read_bytes()),
        source_commit='d1f27274920ceea074f362082b82911e7f4561e4',
        metadata_update_commit=read(HERE / 'source-verification.json')['metadata_update_commit'],
        source_root='WORKSPACES/westlake-harness-bms-deploy/benchmark/2026-10-01-u5-sweep',
        source_note='Records, t20 and indices are committed in the source commit; only results.json uses the later acceptance annotation (7031131cc). Full hilogs remain in runs; pinned raw-line excerpts are vendored here. No later flaky-probe attempts are selected.',
        cohort=66, counts=dict(counts), evaluable=counts['hit'] + counts['false_positive'],
        hit_rate_evaluable=counts['hit'] / (counts['hit'] + counts['false_positive']),
        groups=groups, primary_checkpoints=dict(count=len(checkpoint_rows), verdicts=dict(checkpoint_counts)),
        own_ui=24, own_ui_note='Outer-reviewed first scheduled t20: 12 + 5 + 7; no unique-app or new-light claim.',
        missed_signature_families=len(review['missed_signatures']),
        missed_signature_keys=sum(bool(row['missed_signatures']) for row in rows),
        missed_signature_note='Observed unforecast signatures/new-to-key feedback, not an exhaustive binary wall-recall denominator. Known later bitmap/Immich VerifyError are not new misses.',
        input_pins=pins, checkpoint_rows=checkpoint_rows, rows=rows)


def render(report):
    lines = ['# U5 vs frozen J6/N4 predictions', '',
        'Previously, disappearance of an error was liable to be called a pass. This score requires the exact frozen positive witness; runtime progress and insufficient instrumentation are reported separately.', '',
        f"Frozen CSV SHA256: `{report['prediction_sha256']}` (unchanged).",
        f"U5 evidence commit: `{report['source_commit']}` in `westlake-harness-bms-deploy`.", '',
        f"The 135-file Git-byte audit is `j6n4-scoring/source-verification.json`; only the results summary uses acceptance annotation commit `{report['metadata_update_commit']}`. No later repeat records are imported.", '',
        '## Results', '',
        f"**66 keys: {report['counts']['hit']} hit / {report['counts']['false_positive']} false_positive / {report['counts']['unknown']} unknown.**",
        f"Evaluable: **{report['evaluable']}**, hit rate **{report['hit_rate_evaluable']:.1%}**; unknowns are excluded, not successes.",
        f"Primary repair checkpoints (18, because Element has two): `{report['primary_checkpoints']['verdicts']}`.",
        'Preservation controls: **23/24 hit**, AntennaPod first t20 is desktop (already flaky; not a deterministic regression claim).',
        'Unchanged-wall predictions: **15 hit / 1 unknown** (Jitsi now stops at native android_set_abort_message, so no proven crossing of its old iterator wall).',
        'Repair forecasts: **0 fully witnessed hits / 1 false_positive / 16 unknown keys**. Mindustry still fails slCreateEngine relocation.',
        'Unknown forecasts: **9 retained**, including all three host-input failures.',
        'Auxiliary alarm rechecks: **2/2 hit** (fd-android, fd-k9); not additional lights.',
        'Outer first-t20 UI: **24/66 keys** (5cd 12 + 5ea 5 + 61b 7), including restored fd-uhabits; no single-fix causal attribution.', '',
        '## Why progress is not automatically a frozen hit', '',
        '- **N4-owner, 11 unknown:** all publish the resident runtime, but no target PID logs the required `[N2-OWNER] ABI global ready`. Post-publication consumer failures are positive partial progress, not the full frozen conjunction. This does not negate the outer operational report of owner progress; it does refuse to change the scoring criterion after the run.',
        '- **N4-egl, 2 unknown:** fd-app and SPD fail in `SystemVibratorManager.getVibratorIds`; neither has an executed EGL initialization witness. OH_RegHook lists are registration, not execution. The outer shorthand “fd-app crossed EGL” is not independently supported by this first U5 attempt under the frozen rule.',
        '- **N4-megazord, 2 unknown:** both browsers fail `libmozglue.so: __gnu_strerror_r`; that is not evidence of libmegazord resolving `__get_h_errno`.',
        '- **J6-metadata, unknown:** Element has metadata count 6 and a later Realm/libz wall, but no self-query value `io.sentry.auto-init=false` as frozen.',
        '- **J6-service-query, unknown:** MusicPlayer logs `MediaLibraryService -> 1` and an actual PlaybackService bind attempt; the forecast required `MediaSessionService` plus successful SessionToken resolution. Preserve this useful partial evidence, not a post-hoc criterion rewrite. The bitmap wall was already known in U4.',
        '- **N4-opensles, false_positive:** Mindustry/libarc still says `slCreateEngine: symbol not found` (34309).', '',
        '## Missing-signature feedback', '',
        f"{report['missed_signature_families']} families / {report['missed_signature_keys']} keys, separate from key verdicts and not an exhaustive recall score:", '',
        '| Signature | Keys | Raw hilog lines |', '|---|---|---|']
    review = read(HERE / 'review.json')
    for missed in review['missed_signatures']:
        refs = []
        for row in report['rows']:
            for feedback in row['missed_signatures']:
                if feedback['id'] == missed['id']:
                    refs.append(row['key'] + ':' + ','.join(map(str, feedback['evidence'])))
        lines.append('| ' + missed['description'] + ' | ' + ', '.join(missed['keys']) + ' | ' + '; '.join(refs) + ' |')
    lines += ['', 'N2 never-inherit is a conservative policy, **not** proof of OH musl semantics. Private-load evidence includes Xpm/FDSAN; do not reduce it to an absent-file diagnosis.', '',
        '## All 66 first attempts', '',
        'Line numbers below refer to the full raw `source.log` path in JSON, not excerpt-array positions. `j6n4-scoring/evidence/logs/<key>.json` retains exact PID-scoped lines and SHA; source record/t20 SHA are in each JSON row.', '',
        '| Key | Frozen | Verdict | t20 | Evidence (raw line numbers) |', '|---|---|---|---|---|']
    for row in report['rows']:
        evidence = list(row['observed']['old_wall_evidence'])
        for checkpoint in row['observed']['checkpoints'].values():
            evidence += checkpoint['partial_evidence']
        for feedback in row['missed_signatures']:
            evidence += feedback['evidence']
        refs = ', '.join(map(str, sorted(set(evidence)))) or ('outer t20 SHA' if row['source']['t20_sha256'] else row['source']['error'] or 'unknown')
        lines.append(f"| {row['key']} | {row['prediction']} | {row['verdict']} | {row['t20']} | {refs} |")
    lines += ['', '## Identity and limitations', '',
        '- All 66 records match the frozen APK/package/entry/native-sidecar identity; three are declared prelaunch input rejections, not installed successes. 63 have target-PID binding and SHA-verified t20.',
        '- Candidate binding (`inputs.json`, planned 00:46) precedes clicks. Runtime `73ecf422dba2` (119 files), boot `0876029078e2` (36 files), N4-order package `7bc02de7…`, J6 `2488052f…`. No T7c image is included.',
        '- Shard indices select first attempts; Organic Maps retains its original timed interrupted-cleanup trial. The resume contains only remaining keys. Later zero-variable probes are excluded, never cherry-picked.',
        '- “t20” means the scheduled capture, not exactly 20.000 seconds; actual elapsed capture times remain in JSON. Survival/foreground-confirmation flags do not determine UI.',
        '- Unknowns distinguish a missing witness from a failed repair. Strict 0 complete advance hits is **not** a claim that all repairs had no effect. Future forecasts should bind the markers the deployed generation really emits; do not revise this frozen CSV.',
        '- New signatures are feedback only in this task; this report does not claim to have extended a static scanner or deployed fixes.', '',
        '## Landing dependencies', '',
        'The baseline master does not yet contain the frozen J6/N4 generator/forecast files. Copy the six existing branch files listed in `j6n4-scoring/landing-dependencies.json` unchanged, then the new scoring artifacts and Rust integration file. Do not replace master lib.rs or recalculate a freeze. The dependency manifest binds the source commit and each SHA.', '',
        '## Reproduce', '', '```sh',
        'python3 benchmark/2026-09-30-u4-sweep/j6n4-scoring/score.py --verify',
        'python3 benchmark/2026-09-30-u4-sweep/j6n4-scoring/test_scoring.py -v',
        '```', '',
        'For a fresh full-log collection use `collect.py --source <U5 directory> --out <new directory>`; it rejects changed record/image hashes, non-first selection, and pre-click binding violations. `test_scoring.py` runs offline from vendored evidence. Outer visual sign-off is copied verbatim in `outer-review.json`.']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    report = build()
    outputs = {SWEEP / 'J6N4-SCORING.json': json.dumps(report, ensure_ascii=False, indent=2) + '\n',
               SWEEP / 'J6N4-SCORING.md': render(report)}
    for path, contents in outputs.items():
        if args.verify:
            if path.read_text() != contents:
                raise ValueError('score output changed: ' + str(path))
        else:
            path.write_text(contents)
    print(json.dumps(report['counts']))
