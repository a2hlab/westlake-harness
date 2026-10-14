#!/usr/bin/env python3
"""Only renders explicit 5cd argv. Outer holds lock and executes, never this tool."""
import argparse,hashlib,json,re,shlex
from pathlib import Path
H=Path(__file__).resolve().parent
SERIAL='5cd1e3dd00000000000000000923012c'
OLD='ea5d8b277f1207c928d289196876ad69505d73ab586815daccbda7080169523e'
NEW='ae82e987b708441b3d6069ad04cb81e7846401a09fc9f34a84e854cc79783c33'
def render(action,parent,birth,child,child_birth,audit,want,hdc):
 if action not in ['preflight','stop','apply','rollback','start','ready','spawn']:raise ValueError('action')
 if parent<=1 or birth<=0 or child<0 or child_birth<0 or (child==0)!=(child_birth==0):raise ValueError('identity')
 if not re.fullmatch(r'/data/local/tmp/back51-[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)?',audit):raise ValueError('audit')
 if want not in [OLD,NEW]:raise ValueError('want')
 src=(H/'window_remote.sh').read_text()
 body='set -- '+shlex.join([action,str(parent),str(birth),str(child),str(child_birth),audit,want])+'\n'+src
 cmd='/system/bin/sh -c '+shlex.quote(body)+'; back51_rc=$?; printf "\\nBACK51_REMOTE_RC=%s\\n" "$back51_rc"'
 return {'schema':'back51-command/v1','execution_enabled':False,'serial':SERIAL,'action':action,'source_sha256':hashlib.sha256(src.encode()).hexdigest(),'argv':[hdc,'-t',SERIAL,'shell',cmd],'requires':'outer lock/current authorization/raw receipts; require transport rc0 AND BACK51_REMOTE_RC=0 AND BACK51_VERIFIED; no automatic retry','identity':{'parent':parent,'parent_birth':birth,'child':child,'child_birth':child_birth},'expected_jar':want}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action');p.add_argument('--parent',type=int,required=True);p.add_argument('--birth',type=int,required=True);p.add_argument('--child',type=int,default=0);p.add_argument('--child-birth',type=int,default=0);p.add_argument('--audit',required=True);p.add_argument('--want',choices=['old','new'],required=True);p.add_argument('--hdc',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 d=render(a.action,a.parent,a.birth,a.child,a.child_birth,a.audit,OLD if a.want=='old' else NEW,a.hdc)
 with a.out.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
