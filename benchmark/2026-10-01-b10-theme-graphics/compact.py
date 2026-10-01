"""Deduplicate repeated style-chain witnesses without discarding calls or counts."""

import argparse
import base64
import gzip
import json
from pathlib import Path

import collect


def project(document):
    for app in document['apps']:
        for activity in app['manifest']['activities']:
            theme=activity['resolved_theme']
            unique={json.dumps(item,sort_keys=True):item for item in theme['evidence']}
            theme['raw_evidence_occurrences']=len(theme['evidence'])
            theme['evidence']=list(unique.values())
    document['projection']='All original callsites and lifecycle contexts retained; repeated identical style-parent/config evidence deduplicated, raw occurrence counts explicit'
    return document


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    raw=args.input.read_bytes()
    document=project(json.loads(raw))
    document['raw_document']=dict(sha256=collect.digest(raw),bytes=len(raw),storage='Reproducible private scratch; not committed')
    document['scanner_dependencies'][str(Path(__file__).relative_to(collect.ROOT))]=collect.digest(Path(__file__).read_bytes())
    payload=json.dumps(document,sort_keys=True).encode()
    args.output.write_bytes(base64.b64encode(gzip.compress(payload,mtime=0))+b'\n')
    print('projection bytes',len(payload),'encoded',args.output.stat().st_size)


if __name__=='__main__':
    main()
