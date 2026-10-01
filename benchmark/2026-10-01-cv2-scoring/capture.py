"""Bind the outer signoff to offline run records and scheduled screenshot bytes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V1 = ROOT/'benchmark/2026-10-01-corpus-v2/apk-scan-v1'
sys.path.insert(0, str(V1))
import report as static_report


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def capture(sweep, signoff):
    frozen = json.loads((V1/'FREEZE.json').read_text())
    manifest = static_report.load_evidence(V1/'input-manifest.json.gz.b64')
    inputs = {row['key']:row for row in manifest['apps']}
    predictions = {row['key']:row for row in json.loads((V1/'results.json').read_text())['rows']}
    records = {}
    for path in sorted(sweep.glob('**/record.json')):
        key = path.parent.name
        if key not in predictions:
            continue
        if key in records:
            raise ValueError('Duplicate run record: '+key)
        records[key] = path
    if set(records) != set(predictions):
        raise ValueError('Missing run records')
    facts = {}
    rows = []
    for signed in signoff['keys']:
        key = signed['key']
        path = records[key]
        record = json.loads(path.read_text())
        expected = predictions[key]
        admitted = inputs[key]
        for field in ['package', 'apk_sha256', 'version_code', 'version_name']:
            if str(record.get(field)) != str(expected[field]):
                raise ValueError('Run identity mismatch '+key+':'+field)
        if record.get('native_sidecars') != admitted.get('native_sidecars', []):
            raise ValueError('Sidecar identity mismatch: '+key)
        if sorted(record.get('signer_sha256', [])) != sorted(admitted['signer_sha256']):
            raise ValueError('Signer receipt mismatch: '+key)
        if record['key'] != key or path.relative_to(sweep).parts[0] != signed['board']:
            raise ValueError('Board/key mismatch: '+key)
        fact_path = path.parent.parent/'facts.txt'
        if str(fact_path) not in facts:
            lines = fact_path.read_text().splitlines()[:4]
            required = ['RUNTIME fingerprint='+signoff['state']['RUNTIME'], 'FROZEN checked=4 violations=0',
                        'BOOTIMAGE fingerprint='+signoff['state']['BOOTIMAGE']]
            if any(not any(line.startswith(value) for line in lines) for value in required):
                raise ValueError('Run fingerprint mismatch')
            if not any('manifest='+frozen['input_manifest_raw_sha256'][:8] in line for line in lines):
                raise ValueError('Run manifest mismatch')
            facts[str(fact_path)] = dict(file=str(fact_path.relative_to(sweep)), sha256=digest(fact_path.read_bytes()), lines=lines,
                identity_level='Recorded short fingerprints and manifest prefix; not a fresh device-byte audit')
        scheduled = [shot for shot in record.get('screenshots', []) if shot.get('scheduled_seconds')==20]
        if signed['verdict']=='app_failed':
            if scheduled or record['status']!='app_failed':
                raise ValueError('Unexpected app_failed screenshot/status')
            screenshot = None
        else:
            if len(scheduled)!=1 or not scheduled[0].get('captured'):
                raise ValueError('Missing/duplicate scheduled t20 screenshot: '+key)
            shot = scheduled[0]
            image = path.parent/Path(shot['path']).name
            if digest(image.read_bytes()) != shot['sha256']:
                raise ValueError('Screenshot SHA mismatch: '+key)
            screenshot = dict(file=str(image.relative_to(sweep)), sha256=shot['sha256'],
                scheduled_seconds=20, elapsed_seconds=shot.get('elapsed_seconds'),
                visual_authority=signoff['board_entry'])
        rows.append(dict(key=key, board=signed['board'], package=expected['package'], apk_sha256=expected['apk_sha256'],
            version_code=record['version_code'], version_name=record['version_name'], native_sidecars=record.get('native_sidecars'),
            record_file=str(path.relative_to(sweep)), record_sha256=digest(path.read_bytes()),
            facts_file=str(fact_path.relative_to(sweep)), screenshot=screenshot,
            hilog_available=(path.parent/'hilog.txt').is_file(),
            diagnostic_receipt_available=bool(record.get('diagnostics')),
            signer_sha256=record['signer_sha256'],
            observed_status=record['status'], identity_status='offline-record-input-and-screenshot-match'))
    return dict(schema='cv2-offline-signoff-binding-v1', rows=rows, facts=list(facts.values()),
                input_manifest_sha256=frozen['input_manifest_raw_sha256'],
                source_root='$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-cv2-sweep',
                limits='Input identity from run records; screenshot SHA independently read; outer owns visual verdict. No fresh per-file device runtime attestation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sweep', type=Path, default=Path(os.environ.get('WORKSPACES', ROOT.parent))/'westlake-harness-t4/benchmark/2026-10-01-cv2-sweep')
    parser.add_argument('--signoff', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = capture(args.sweep, json.loads(args.signoff.read_text()))
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2)+'\n')
    print('bound',len(result['rows']),'scheduled-t20',sum(bool(row['screenshot']) for row in result['rows']), 'hilog',sum(row['hilog_available'] for row in result['rows']))


if __name__=='__main__':
    main()
