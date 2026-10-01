"""Describe retrospective rule coverage and its cost without feeding labels to rules."""

import argparse
import collections
import importlib.util
import json
from pathlib import Path
import sys

import score

HERE=Path(__file__).resolve().parent
V2=score.ROOT/'benchmark/2026-10-01-corpus-v2/apk-scan-v2'
sys.path.insert(0,str(V2))


def generate():
    spec=importlib.util.spec_from_file_location('precise_v2_report',V2/'report.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    static=module.generate()
    observed=score.generate()
    observations={row['key']:row for row in observed['rows']}
    rules={}
    for row in static['rows']:
        for family in {candidate['family'] for candidate in row['candidates']}:
            item=rules.setdefault(family,dict(keys=[],observed_counts={}))
            item['keys'].append(row['key'])
    for item in rules.values():
        item['observed_counts']=dict(collections.Counter(observations[key]['observed_t20'] for key in item['keys']))
    experiment=score.confusion([dict(predicted_t20=row['abstention_experiment_t20'],observed_t20=observations[row['key']]['observed_t20']) for row in static['rows']])
    changed=[dict(key=row['key'],observed_t20=observations[row['key']]['observed_t20'],
                  candidates=sorted({candidate['family'] for candidate in row['candidates']}))
             for row in static['rows'] if row['abstention_experiment_t20']!=row['v1_t20']]
    return dict(schema='cv2-rule-feedback-v2',rules=rules,
        original=observed['confusion'], default_v2_confusion=observed['confusion'],
        abstention_experiment=dict(promoted=False,confusion=experiment,changed_keys=changed,
            functional_precision=dict(numerator=experiment['own-ui']['lit'],denominator=sum(experiment['own-ui'].values())),
            lost_positive_functional_ui=sum(row['observed_t20']=='lit' for row in changed),
            interpretation='Blanket abstention worsens precision and removes valid positives; keep candidate reporting only.'),
        remaining_positive_unlit=[row['key'] for row in static['rows'] if row['abstention_experiment_t20']=='own-ui' and observations[row['key']]['observed_t20']!='lit'],
        negative_controls=dict(utility_only_webkit_not_content='cv2-org-secuso-privacyfriendlymemory',
            signed_lit_no_added_contract='cv2-com-page-bizzle',
            signed_lit_with_optional_content=['cv2-com-omgodse-notally','cv2-com-benny-pxerstudio','cv2-com-asdoi-timetable'],
            signed_lit_with_startup_transition='cv2-org-secuso-privacyfriendly2048'),
        missing_runtime_evidence=dict(original_run_hilog_count=sum(row['run_evidence']['hilog_available'] for row in observed['rows']),
            first_fatal_result='unknown; all original run directories lack hilog.txt and diagnostic receipts',
            later_reprobe_policy='oc-t4 delegated reruns are separate observations, not replacements for frozen t20 or original first walls'),
        source=dict(scoring_sha256=score.digest((HERE/'SCORING.json').read_bytes()),
            scanner_results_sha256=score.digest((V2/'results.json').read_bytes()),
            generator_sha256=score.digest(Path(__file__).read_bytes())))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=generate()
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print('rule cohorts',len(result['rules']),'experiment lost lit',result['abstention_experiment']['lost_positive_functional_ui'])


if __name__=='__main__':
    main()
