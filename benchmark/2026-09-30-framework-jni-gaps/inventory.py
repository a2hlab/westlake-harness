"""Reuse the established v3 ELF/source attribution with exact v3a JARs (no overlay)."""
import gzip,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'2026-09-29-static-wall-prediction'
sys.path.insert(0,str(OLD))
import scan_jni
PACKAGE=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-v3a-74d1d6d4-r8b')
if __name__=='__main__':
    result=scan_jni.scan(PACKAGE,overlay=None)
    with gzip.open(HERE/'evidence/native-inventory.json.gz','wt') as f:json.dump(result,f)
    print('unique native methods',len(result['methods']),result['counts'],flush=True)
