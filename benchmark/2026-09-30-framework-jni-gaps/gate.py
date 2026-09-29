"""Fail closed on the strict worklist; only reviewed, inventory-bound exceptions apply."""
import argparse,json
from pathlib import Path

def evaluate(strict,exceptions):
    allowed={};invalid=[]
    for e in exceptions.get('exceptions',[]):
        if e.get('approval')!='approved':continue
        if (not all(e.get(k) for k in ['id','status','inventory_sha256','approved_by','reason','evidence'])
            or e['inventory_sha256']!=strict['inventory_sha256']):
            invalid.append(e.get('id','<missing>'));continue
        allowed[(e['id'],e['status'])]=e
    blockers=[m for m in strict['methods'] if (m['id'],m['status']) not in allowed]
    if not strict.get('declaration_count') or strict.get('covered_count',0)+len(strict['methods'])!=strict['declaration_count']:
        invalid.append('incomplete_strict_inventory')
    return {'pass':not blockers and not invalid,'blocked_count':len(blockers),'excepted_count':len(strict['methods'])-len(blockers),'invalid_approved_exceptions':invalid,'blockers':blockers}

def main():
    p=argparse.ArgumentParser();p.add_argument('--strict',type=Path,default=Path(__file__).with_name('jni-strict.json'));p.add_argument('--exceptions',type=Path,default=Path(__file__).with_name('jni-exceptions.json'));p.add_argument('--out',type=Path);a=p.parse_args()
    result=evaluate(json.loads(a.strict.read_text()),json.loads(a.exceptions.read_text()))
    if a.out:a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='blockers'}));return 0 if result['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
