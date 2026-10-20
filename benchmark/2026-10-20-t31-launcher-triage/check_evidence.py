#!/usr/bin/env python3
"""Read-only source/provenance checks; no HAP, device or timing performance verdict."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main', type=Path, required=True)
    p.add_argument('--vm-copy', type=Path, required=True)
    a = p.parse_args()
    here = Path(__file__).resolve().parent
    index = json.loads((here/'source-index.json').read_text())
    roots = {'MAIN': a.main, 'VM_COPY': a.vm_copy}
    for row in index:
        if 'git_commit' in row:
            repo = roots[row['alias']]
            object_name = row['git_commit'] + ':' + row['path']
            blob = subprocess.check_output(
                ['git', '-C', str(repo), 'rev-parse', '--verify', object_name],
                text=True).strip()
            assert blob == row['git_blob'], row['path']
            raw = subprocess.check_output(
                ['git', '-C', str(repo), 'cat-file', 'blob', blob])
            assert hashlib.sha256(raw.splitlines()[196]).hexdigest() == row['line197_sha256'], row['path']
        else:
            raw = (roots[row['alias']]/row['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row['sha256'], row['path']
        assert 1 <= row['lines'][0] <= row['lines'][1] <= len(raw.splitlines()), row['path']
    old = (a.vm_copy/'apps/imehost/Index.js').read_text()
    new = (a.main/'sources/api-implementations/source-build-host/westlake-java/apps/imehost/Index.js').read_text()
    assert "Text.create('Westlake IME host')" in old and 'Native OHOS keyboard control' in old
    assert 'Text.create(' not in new and 'TextInput.create(' not in new and "#ff000000" in new
    result = json.loads((here/'results.json').read_text())
    assert result['timeline']['first_frame_latency_seconds'] is None
    assert not result['retained_candidate_modified'] and not result['deployment_authorized']
    assert result['device_commands'] == result['builds'] == result['rea_calls'] == 0
    assert len(json.loads((here/'component-matches.json').read_text())) == 3
    print(json.dumps({'status':'PASS','sources_checked':len(index),'scope':'read-only pinned sources; human/device acceptance not executed'}))
if __name__ == '__main__':
    main()
