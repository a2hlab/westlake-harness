"""Known answers against the original two captured records plus explicitly synthetic v3 success."""
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
    counts={'selftest_error':r['selftest_error_count'],'badtag':r['badtag_count'],'probe_error':r['probe_error_count']}
    assert counts==p['expected_counts'],r
    assert r['status']==p['expected_status'],r
    print(f'{name}: selftest_error={counts["selftest_error"]} badtag={counts["badtag"]} probe_error={counts["probe_error"]} status={r["status"]} original_sha_verified=true')
success='10-03 02:23:00.000 123 124 I C00f00/AppSpawnXJava: [stderr] [WL-KS-PROBE] validateAead round-trip=OK'
r=process_selftest.scan_text(success,['123'])['123']
assert r['status']=='PASS' and not process_selftest.errors(r)
print('synthetic-v3-success: validateAead round-trip=OK status=PASS (synthetic, not board evidence)')
print('KNOWN_ANSWERS PASS: U12=selftest_error; U10.1T8=badtag; synthetic v3=PASS')
