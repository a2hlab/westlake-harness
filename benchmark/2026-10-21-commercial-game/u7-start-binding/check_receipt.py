#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    result=json.loads((HERE/'results.json').read_text());assert result['check_rc']==[0,0,0]
    assert sha(ROOT/'scripts/lab/u7_executor.py')==result['production_source_sha256']
    for name,row in json.loads((HERE/'source-before.json').read_text()).items():
        if name!='u7_executor.py':assert sha(ROOT/'scripts/lab'/name)==row['lane_sha256']
    assert not any(result[k] for k in ['device_io','runtime_build','label_recipe_modified','deployment_start_modified','label_bypass_enabled','execution_enabled'])
    for row in json.loads((HERE/'evidence-index.json').read_text()):assert sha(HERE/row['sanitized'])==row['sanitized_sha256']
    assert "AttributeError: 'DeviceIO' object has no attribute 'a'" in (HERE/'evidence/reproduce.stderr.txt').read_text()
    for name,h in json.loads((HERE/'manifest.json').read_text())['files'].items():assert sha(ROOT/name)==h,name
    print('PASS: G22 source/evidence fixed; original start/label code unchanged; offline only')
if __name__=='__main__':main()
