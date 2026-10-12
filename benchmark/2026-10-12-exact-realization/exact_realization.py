#!/usr/bin/env python3
"""Explicit offline realization and separately admitted restoration entrypoint."""
import argparse,json,sys
from pathlib import Path
import realization as r
import restore

def main():
    if len(sys.argv)>1 and sys.argv[1] in {'compile','verify','window'}:return r.main()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',nargs='?',choices=['restore-preview','restore'])
    p.add_argument('--realization',type=Path,required=True)
    p.add_argument('--prepared',type=Path)
    p.add_argument('--admission',type=Path);p.add_argument('--admission-sha256')
    p.add_argument('--authorization',type=Path);p.add_argument('--authorization-sha256')
    p.add_argument('--lock-tool',type=Path);p.add_argument('--lock-tool-sha256')
    p.add_argument('--transaction-action',choices=['apply','rollback'],default='apply')
    p.add_argument('--execute',action='store_true');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    a.action=a.action or ('restore' if a.execute else 'restore-preview')
    try:
        proof=r.verify(a.realization)
        if a.action=='restore-preview':
            r.need(not a.execute,'preview cannot execute');result=restore.prepare(proof,a.out);rc=0
            if a.admission:
                r.need(a.authorization is not None,'admission check also needs executor authorization')
                restore.guard(proof,a.out,{'path':str(a.admission),'sha256':a.admission_sha256},
                    {'path':str(a.authorization),'sha256':a.authorization_sha256},Path.cwd())
            r.write(a.out/'preview-receipt.json',result)
        else:
            r.need(a.execute and all([a.prepared,a.admission,a.authorization,a.lock_tool]),'restore requires explicit execute plus independent pins')
            r.need((not a.out.exists()) if a.transaction_action=='apply' else (a.out/'transaction.json').is_file(),'apply needs fresh output; rollback needs original transaction directory')
            result,rc=restore.execute(proof,a.prepared,{'path':str(a.admission),'sha256':a.admission_sha256},
                {'path':str(a.authorization),'sha256':a.authorization_sha256},
                {'path':str(a.lock_tool),'sha256':a.lock_tool_sha256},Path.cwd(),a.out,action=a.transaction_action)
            r.write(str(a.out)+'.realization-receipt.json',result)
        print(json.dumps(result,indent=2));return rc
    except (ValueError,KeyError,TypeError,OSError) as e:print('REJECT '+str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
