"""Offline compatibility gate for a proposed board framework report; never deploys."""
import argparse
import json
from pathlib import Path


def validate(candidate, reference, frozen):
    files = candidate.get('files', candidate.get('source_files', {}))
    mismatches = []
    for name, expected in frozen.items():
        if files.get(name, {}).get('sha256') != expected['sha256']:
            mismatches.append(name)
    name = 'libart.so'
    if files.get(name, {}).get('sha256') != reference['source_files'][name]['sha256']:
        mismatches.append(name)
    if mismatches:
        raise ValueError('Rebuild AOT for changed/missing inputs: ' + ', '.join(mismatches))
    return {'framework_hashes_match': True, 'device_accepted': False,
            'note': 'Report comparison only; verify actual device files before launch.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('framework_report', type=Path)
    args = parser.parse_args()
    evidence = Path(__file__).parent / 'evidence'
    result = validate(json.loads(args.framework_report.read_text()),
                      json.loads((evidence / 'reference-device-report.json').read_text()),
                      json.loads((evidence / 'input-files.json').read_text()))
    print(json.dumps(result, indent=2))
