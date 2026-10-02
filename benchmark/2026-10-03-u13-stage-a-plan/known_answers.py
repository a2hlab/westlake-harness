"""Known answers against the original two captured records, not a synthetic status."""
import hashlib
import json
from pathlib import Path
import process_selftest

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
provenance=json.loads((HERE/'evidence/known-answer/provenance.json').read_text())
for name,p in provenance.items():
    rec=REPO/p['source_record']
    assert rec.is_file(),f'actual capture missing: {rec}'
    assert hashlib.sha256(rec.read_bytes()).hexdigest()==p['source_hashes']['record.json']
    assert hashlib.sha256((rec.parent/'hilog.txt').read_bytes()).hexdigest()==p['original_hilog_sha256']
    r=process_selftest.run_row(rec)
    assert r['selftest_error_count']==p['expected_error_count'],r
    assert r['status']==('REJECT' if p['expected_error_count'] else 'unknown'),r
    print(f'{name}: actual_record={p["source_record"]} error={r["selftest_error_count"]} validateAead_OK={r["validateAead_OK_count"]} status={r["status"]} original_sha_verified=true')
print('KNOWN_ANSWERS PASS: U12 error detected; U10.1T8 zero errors (unknown is not PASS)')
