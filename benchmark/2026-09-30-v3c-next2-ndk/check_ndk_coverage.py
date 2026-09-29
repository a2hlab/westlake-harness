#!/usr/bin/env python3
"""ELF-derived NDK policy coverage gate, including the rejected b66 control."""
import argparse,hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('--negative',type=Path,required=True);a=p.parse_args()
audit=json.loads((R/'needed-closure.json').read_text());required=set(audit['ndk_sonames'])
def check(path):
 data=path.read_bytes()
 strings=[x.decode('ascii','ignore') for x in data.split(b'\0')]
 policy=next((x for x in strings if x.startswith('%s:libbionic_compat.so:')), '')
 names=set(policy.split(':'))
 has_search=any('/system/lib64/chipset-sdk-sp:/system/lib64/ndk' in x for x in strings)
 missing=sorted(required-names)
 return {'file':str(path),'sha256':hashlib.sha256(data).hexdigest(),'shared_sonames':sorted(names-{'%s'}),'required_ndk_sonames':sorted(required),'missing_ndk_sonames':missing,'ndk_dependency_root_present':has_search,'passed':not missing and has_search}
new=check(a.candidate);old=check(a.negative)
result={'candidate':new,'negative_control':old,'negative_rejected':not old['passed'],'scope':'Coverage of ELF-derived public NDK names only; does not execute OH musl or prove rendering.','unresolved_other_names':audit['missing']}
(R/'ndk-coverage.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'candidate_passed':new['passed'],'negative_rejected':not old['passed'],'negative_missing':old['missing_ndk_sonames']},indent=2))
if not new['passed'] or old['passed']:raise SystemExit(1)
