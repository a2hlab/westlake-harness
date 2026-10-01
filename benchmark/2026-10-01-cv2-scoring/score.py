"""Score an immutable late freeze with explicit abstentions and six visual classes."""

import argparse
import collections
import csv
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V1 = ROOT/'benchmark/2026-10-01-corpus-v2/apk-scan-v1'
CSV_SHA = 'ab51ab2df4fa6d8e66989d8713da71b79ef5e9c9e6b473f6c54a4bd1d1bc21b1'
SIGNOFF_COMMIT = '5641749091f0a12f084494f8e173ce75c04e05ee'
SIGNOFF_SHA = '7a90099dde7be440513b979f02d37259d941a7dfcf14187ef961d8ec20c82d84'
SIGNOFF_MASTER_SHA = '01a25763077dff2d57e1cb90d8d8480c417efe7578be1b0509e3129592a42cf1'
VERDICTS = ['lit', 'lit-webview-fallback', 'alive-launcher-foreground', 'alive-blank-window', 'dead', 'app_failed']


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def unique(rows, count=100):
    indexed = {row['key']:row for row in rows}
    if len(rows)!=count or len(indexed)!=count:
        raise ValueError('Incomplete/duplicate cohort')
    return indexed


def confusion(rows):
    matrix = {label:{verdict:0 for verdict in VERDICTS} for label in ['own-ui','unknown']}
    for row in rows:
        if row['predicted_t20'] not in matrix or row['observed_t20'] not in VERDICTS:
            raise ValueError('Unknown prediction or verdict class')
        matrix[row['predicted_t20']][row['observed_t20']]+=1
    return matrix


def attribution(prediction, observed):
    profile = prediction['profile']
    abstention = []
    if prediction['native_member_count']:
        abstention.append('any-packaged-native-member-conservative-abstention')
    if prediction['phase'] in {'compose','webview','gl'}:
        abstention.append('coverage-selection-group-abstention')
    if any(profile['startup_invoked'].get(name,0) for name in ['compose','webview','gl','flutter','unity']):
        abstention.append('bounded-startup-special-rendering-abstention')
    if any(candidate['family'] in {'framework-jni:missing','framework-jni:stub'} and candidate['startup_occurrences'] for candidate in prediction['first_wall_candidates']):
        abstention.append('bounded-startup-missing-or-stub-jni-abstention')
    if prediction['t20']=='unknown':
        mechanism = 'conservative-abstention-lit' if observed=='lit' else 'abstention-not-negative'
        explanation = 'Coverage-group/native/startup guards abstain; signed success does not prove every referenced API works.'
    elif observed=='lit':
        mechanism = 'positive-own-ui-match'
        explanation = 'Low-confidence native-free View transfer hypothesis matches the outer functional-UI verdict.'
    elif observed=='lit-webview-fallback':
        mechanism = 'functional-overprediction-webview-prefix-and-bounded-graph-blindspot'
        explanation = 'App-owned fallback satisfies own-UI literal target, not functional UI. v1 pooled webkit APIs and a three-hop graph did not guard t20.'
    elif observed=='alive-launcher-foreground':
        mechanism = 'overprediction-startup-window-contract-not-enforced'
        explanation = 'Native-free is not sufficient: transition candidate does not constrain v1 t20; absent transition evidence remains an unobserved callback/window blindspot.'
    else:
        mechanism = 'overprediction-lightweight-not-runtime-safety'
        explanation = 'v1 service/context/JNI requirements are conditional alerts, not hard admission guards. A dead label alone cannot identify a missing runtime wall.'
    return dict(mechanism=mechanism, explanation=explanation, abstention_guards=abstention,
                v1_candidate_families=[candidate['family'] for candidate in prediction['first_wall_candidates']],
                runtime_root_cause='unknown; delegated target-PID evidence not yet available',
                fatal_candidate_match='unknown; no terminal-chain evidence in this signoff')


def score(csv_bytes, freeze, signoff, evidence, predictions):
    if digest(csv_bytes)!=CSV_SHA or freeze['csv_sha256']!=CSV_SHA:
        raise ValueError('Frozen CSV SHA mismatch')
    csv_rows = list(csv.DictReader(io.StringIO(csv_bytes.decode())))
    frozen = unique(csv_rows)
    signed = unique(signoff['keys'])
    runs = unique(evidence['rows'])
    static = unique(predictions['rows'])
    if not set(frozen)==set(signed)==set(runs)==set(static):
        raise ValueError('Cohort key mismatch')
    if predictions['t20_counts']!={'own-ui':73,'unknown':27}:
        raise ValueError('Frozen class counts mismatch')
    if evidence['input_manifest_sha256']!=freeze['input_manifest_raw_sha256']:
        raise ValueError('Frozen input manifest mismatch')
    counts = dict(collections.Counter(row['verdict'] for row in signed.values()))
    if counts!=signoff['counts']:
        raise ValueError('Signed totals mismatch')
    rows = []
    for key in sorted(frozen):
        prediction, run, observed = static[key], runs[key], signed[key]
        for field in ['package','apk_sha256','version_code','version_name']:
            if str(run[field])!=str(prediction[field]) or str(frozen[key][field])!=str(prediction[field]):
                raise ValueError('Identity mismatch: '+key+':'+field)
        if run['board']!=observed['board'] or run['identity_status']!='offline-record-input-and-screenshot-match':
            raise ValueError('Run binding mismatch: '+key)
        if bool(run['screenshot'])!=(observed['verdict']!='app_failed'):
            raise ValueError('Screenshot coverage mismatch: '+key)
        if frozen[key]['t20']!=prediction['t20']:
            raise ValueError('Static prediction changed: '+key)
        positive = prediction['t20']=='own-ui'
        rows.append(dict(key=key, package=prediction['package'], apk_sha256=prediction['apk_sha256'],
            board=observed['board'], predicted_t20=prediction['t20'], observed_t20=observed['verdict'],
            functional_score='hit' if positive and observed['verdict']=='lit' else 'overprediction' if positive else 'abstention',
            own_ui_score='hit' if positive and observed['verdict'] in {'lit','lit-webview-fallback'} else 'overprediction' if positive else 'abstention',
            first_wall_score='abstention', checkpoint_score='abstention',
            attribution=attribution(prediction, observed['verdict']), run_evidence=run))
    matrix = confusion(rows)
    positives = sum(matrix['own-ui'].values())
    inclusive_hits = matrix['own-ui']['lit']+matrix['own-ui']['lit-webview-fallback']
    late = datetime.fromisoformat(freeze['frozen_at'])>datetime.fromisoformat(freeze['first_device_window'])
    return dict(schema='corpus-v2-scoring-v1', rows=rows, confusion=matrix,
        observed_counts=counts, late_freeze=late, frozen_at=freeze['frozen_at'], first_device_window=freeze['first_device_window'],
        timing='late; not held-out' if late else 'pre-run',
        metrics=dict(coverage=dict(numerator=positives,denominator=100),
            functional_positive_precision=dict(numerator=matrix['own-ui']['lit'],denominator=positives),
            own_ui_positive_precision=dict(numerator=inclusive_hits,denominator=positives),
            abstention_count=100-positives, abstention_functional_lit=matrix['unknown']['lit'],
            functional_overprediction=positives-matrix['own-ui']['lit'],
            own_ui_overprediction=positives-inclusive_hits,
            true_negative=None, false_negative=None, binary_accuracy=None,
            explanation='Unknown is abstention; no predicted-negative class. No invented TN/FN or binary accuracy.'),
        first_wall_and_checkpoint='100 unknown predictions each; no terminal/crossing truth supplied by visual signoff',
        provenance=dict(csv_sha256=CSV_SHA, signoff_master_commit=SIGNOFF_COMMIT, signoff_board_entry=signoff['board_entry'],
            signoff_sha256=digest(json.dumps(signoff,sort_keys=True).encode()),
            limits=evidence['limits']))


def csv_text(result):
    stream=io.StringIO(newline='')
    fields=['key','package','board','predicted_t20','observed_t20','functional_score','own_ui_score','first_wall_score','checkpoint_score','mechanism']
    writer=csv.DictWriter(stream,fields,lineterminator='\n')
    writer.writeheader()
    for row in result['rows']:
        writer.writerow({**{field:row[field] for field in fields if field!='mechanism'}, 'mechanism':row['attribution']['mechanism']})
    return stream.getvalue()


def generate(directory=HERE):
    frozen_bytes=(V1/'PREDICTIONS.csv').read_bytes()
    freeze=json.loads((V1/'FREEZE.json').read_text())
    prediction_bytes=(V1/'results.json').read_bytes()
    if digest(prediction_bytes)!=freeze['results_sha256']:
        raise ValueError('Frozen results SHA mismatch')
    signoff_bytes=(directory/'outer-signoff.json').read_bytes()
    if digest(signoff_bytes)!=SIGNOFF_SHA or digest(signoff_bytes.removesuffix(b'\n'))!=SIGNOFF_MASTER_SHA:
        raise ValueError('Master signoff SHA mismatch')
    evidence_bytes=(directory/'run-evidence.json').read_bytes()
    result=score(frozen_bytes,freeze,json.loads(signoff_bytes),json.loads(evidence_bytes),json.loads(prediction_bytes))
    result['provenance'].update(signoff_file_sha256=digest(signoff_bytes),signoff_master_file_sha256=SIGNOFF_MASTER_SHA,
                                signoff_snapshot_normalization='One final newline added; JSON otherwise byte-identical to master',run_evidence_sha256=digest(evidence_bytes),
                                scorer_sha256=digest(Path(__file__).read_bytes()))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=generate()
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'SCORING.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    (args.output/'SCORING.csv').write_text(csv_text(result))
    print(json.dumps(result['confusion'],sort_keys=True))


if __name__=='__main__':
    main()
