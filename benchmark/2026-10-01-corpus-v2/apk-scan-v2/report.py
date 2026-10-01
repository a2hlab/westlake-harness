"""Replay v2 static contracts separately from the late v1 scoring."""

import argparse
import base64
import collections
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys

import rules

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
V1=HERE.parent/'apk-scan-v1'
sys.path.insert(0,str(ROOT/'benchmark/2026-10-01-cv2-scoring'))
import score


def load(path):
    return json.loads(gzip.decompress(base64.b64decode(path.read_bytes())))


def generate():
    predictions=json.loads((V1/'results.json').read_text())
    freeze=json.loads((V1/'FREEZE.json').read_text())
    if score.digest((V1/'results.json').read_bytes())!=freeze['results_sha256'] or score.digest((V1/'PREDICTIONS.csv').read_bytes())!=score.CSV_SHA:
        raise ValueError('v1 freeze drift')
    precise=load(HERE/'precise-profile.json.gz.b64')
    facts=load(V1/'facts.json.gz.b64')
    scanned={app['package']:app for app in facts['apps']}
    indexed={app['package']:app for app in precise['apps']}
    if len(indexed)!=100 or len(precise['apps'])!=100 or set(indexed)!=set(scanned):
        raise ValueError('Incomplete precise profile')
    if precise['selection_sha256']!=score.digest((HERE.parent/'results.json').read_bytes()) or precise['tool_sha256']!=facts['tools']['dexdump']:
        raise ValueError('Selection or dexdump drift')
    for relative, digest in precise['scanner_dependencies'].items():
        if score.digest((ROOT/relative).read_bytes())!=digest:
            raise ValueError('Precise collector dependency drift: '+relative)
    for package, app in indexed.items():
        if [(dex['member'],dex['sha256']) for dex in app['dex']]!=[(dex['member'],dex['sha256']) for dex in scanned[package]['dex']]:
            raise ValueError('DEX identities differ from v1: '+package)
    rows=sorted([rules.revise(row,indexed[row['package']]) for row in predictions['rows']],key=lambda row:row['key'])
    return dict(schema='corpus-v2-apk-scan-v2', version='2-retrospective-precise-contract-candidates', rows=rows,
        t20_counts=dict(collections.Counter(row['t20'] for row in rows)),
        added_candidate_keys=[row['key'] for row in rows if row['change']!='unchanged'],
        abstention_experiment_counts=dict(collections.Counter(row['abstention_experiment_t20'] for row in rows)),
        classification_inputs='v1 frozen static results plus exact APK/DEX WebView content calls only; no runtime labels',
        limitations='No label-derived positive upgrades. Added candidates do not change t20. Blanket demotion is an unpromoted retrospective ablation, not a deploy gate. API references are not fatal chronology.',
        source=dict(v1_csv_sha256=score.CSV_SHA, v1_results_sha256=freeze['results_sha256'],
            precise_profile_sha256=score.digest((HERE/'precise-profile.json.gz.b64').read_bytes()),
            rules_sha256=score.digest((HERE/'rules.py').read_bytes()), report_sha256=score.digest(Path(__file__).read_bytes())))


def csv_text(result):
    stream=io.StringIO(newline='')
    fields=['key','package','apk_sha256','v1_t20','t20','abstention_experiment_t20','first_wall','checkpoint','change','candidates']
    writer=csv.DictWriter(stream,fields,lineterminator='\n')
    writer.writeheader()
    for row in result['rows']:
        writer.writerow({**{field:row[field] for field in fields if field!='candidates'},'candidates':';'.join(candidate['family'] for candidate in row['candidates'])})
    return stream.getvalue()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=generate()
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'results.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    (args.output/'PREDICTIONS.csv').write_text(csv_text(result))
    print(result['t20_counts'], 'added-candidate-apps',len(result['added_candidate_keys']))


if __name__=='__main__':
    main()
