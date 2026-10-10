#!/usr/bin/env python3
"""Verify retained dexdump stdout completeness against all APK DEX headers."""
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import zipfile

import collect_impact as impact


def check(item):
    key, data = item
    result = []
    with zipfile.ZipFile(impact.expand(data['static']['apk']['path'])) as archive:
        for dex in data['static']['dex']:
            payload = archive.read(dex['member'])
            expected = int.from_bytes(payload[96:100], 'little')
            seen = 0
            digest = hashlib.sha256()
            with gzip.open(impact.expand(dex['raw_stdout']), 'rb') as stream:
                for line in stream:
                    digest.update(line)
                    seen += b"Class descriptor  : '" in line
            if seen != expected or digest.hexdigest() != dex['stdout_sha256'] or dex['exit'] != 0 or \
                    impact.sha(impact.expand(dex['stderr']['path'])) != dex['stderr']['sha256']:
                raise ValueError('incomplete/drifted dexdump: ' + key + '/' + dex['member'])
            result.append(dict(key=key, member=dex['member'], class_defs_header=expected,
                               class_defs_stdout=seen, stdout_sha256=digest.hexdigest(), exit=0))
    return result


def main():
    report = impact.read(impact.HERE / 'impact-evidence.json')
    with ThreadPoolExecutor(max_workers=2) as executor:
        rows = [row for group in executor.map(check, sorted(report['keys'].items())) for row in group]
    result = dict(apks=len(report['keys']), dex_members=len(rows), class_defs_header=sum(row['class_defs_header'] for row in rows),
                  class_defs_stdout=sum(row['class_defs_stdout'] for row in rows), complete=True, rows=rows)
    (impact.HERE / 'evidence/dexdump-completeness.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'rows'}, sort_keys=True))


if __name__ == '__main__':
    main()
