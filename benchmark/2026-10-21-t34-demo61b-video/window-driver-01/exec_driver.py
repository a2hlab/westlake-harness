#!/usr/bin/env python3
"""Reviewed T34 apply orchestration. Default preview; no automatic re-open/retry."""
import json,subprocess
from common import *
def execute(d):
 pre=d.boot();assert pre==d.origin['boot'];d.held()
 rc,out,_=d.raw('apply',d.op,300);assert b'VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED' in out
 plan=json.loads((d.w/'apply/result.json').read_text());assert plan.get('status')=='VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED'
 new=d.reboot(pre)
 # One normal icon; collect the new process view before waiting for a gray-screen outcome.
 d.ui(new,'first-icon','launch',0)
 parent,host,child,wid,init=d.discover(new)
 run=d.w/'apply/after.run.sh';assert run.is_file(),'Use the actual applied run, not a data template'
 p=json.loads((d.repo/REL/'candidate-view-01/profile.template.json').read_text())
 p.update(boot=new,before_boot=pre,parent=parent,host=host,child=child,wid=wid,init_mnt=init)
 p['expected_sha256']['run.sh']=digest(run);profile=d.out/'candidate-profile.json';dump(profile,p)
 outdir=d.out/'candidate-collect';assert not outdir.exists()
 argv=['python3',str(d.repo/REL/'candidate-view-01/prepare.py'),'--profile',str(profile),'--candidate-run',str(run),'--hdc',str(d.a.hdc),'--out',str(outdir)]
 d.raw('prepare',argv,30);d.raw('shell-syntax',['sh','-n',str(outdir/'collect.sh')],15)
 a=json.loads((outdir/'collect.argv.json').read_text());d.held()
 rc,body,err=d.raw('candidate-collect',a,90,True)
 parsed=d.readout.decode(body.decode(errors='replace'),rc);dump(outdir/'report.json',parsed)
 assert parsed['status']=='COLLECTED_IDENTITY_GUARDED','Collection failed/unknown; stop, preserve partial bytes'
 d.ui(new,'feed-observation','capture',70)
 dump(d.out/'result.json',{'status':'COLLECTED_PENDING_VISUAL_REVIEW','boot':new,'parent':parent,'child':child,'wid':wid,'retained':False})
if __name__=='__main__':entry(execute,False)
