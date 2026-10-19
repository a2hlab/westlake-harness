#!/usr/bin/env python3
"""Outer-only one-shot readiness/attach/observe. No UI, launch, polling or retry."""
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path
from identity_selection import select_exact, check_stat

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',type=Path,default=Path.cwd())
    ap.add_argument('--identity',nargs=5,metavar=('BOOT','PARENT','PARENT_BIRTH','CHILD','CHILD_BIRTH'),required=True)
    ap.add_argument('--execute',action='store_true')
    a=ap.parse_args();repo=a.repo.resolve();here=Path(__file__).resolve().parent
    base=Path.home()/'.local/share/westlake/toutiao-resume-20261020'
    boot=a.identity[0];parent,pbirth,child,cbirth=map(int,a.identity[1:])
    sys.path.insert(0,str(repo/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r13'))
    import core
    template=json.loads((base/'r13-admission-template.json').read_text())
    index=json.loads((here/'source-index.json').read_text());pins=index['repo_source_pins']
    for name,digest in index['plan_source_pins'].items():core.need(core.sha(here/name)==digest,'plan source drift '+name)
    for rel,digest in pins.items():core.need(core.sha(repo/rel)==digest,'source drift '+rel)
    for role,pin in core.PINS.items():
        m=template['modules'][role];core.need(m['sha256']==pin and core.sha(core.path(m['local_path']))==pin,'local module '+role)
    for role in ('host','hdc','lock_script'):
        m=template[role];core.need(core.sha(core.path(m['path']))==m['sha256'],'local tool '+role)
    core.need(template['host']['sha256']==core.HOST_SHA,'host pin')
    core.need(min(parent,pbirth,child,cbirth)>0 and parent!=child,'identity arguments')
    if not a.execute:
        print(json.dumps({'status':'LOCAL_PREFLIGHT_ONLY','device_calls':0,'identity':a.identity}));return 0
    out=base/'r13-video-readiness';out.mkdir(exist_ok=False)
    sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'))
    import bms_batch as b
    import shlex
    board=b.Board(core.SERIAL,str(core.path(template['hdc']['path'])),'bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands');board.boot=boot
    deadline=time.monotonic()+30
    def read(command):
        remaining=deadline-time.monotonic();core.need(remaining>0,'readiness deadline')
        value=board.shell(command,timeout=remaining)[1]
        core.need(time.monotonic()<deadline,'readiness deadline after guarded read')
        return value
    try:
        select_exact(read('ps -A -o PID,PPID,UID,NAME'),parent,child)
        def identity():
            core.need(read('cat /proc/sys/kernel/random/boot_id')==boot,'boot mismatch')
            check_stat(read('cat /proc/%d/stat'%parent),parent,pbirth)
            check_stat(read('cat /proc/%d/stat'%child),child,cbirth,parent)
            status=read('cat /proc/%d/status'%child)
            fields={x.split(':',1)[0]:x.split(':',1)[1].strip() for x in status.splitlines() if ':' in x}
            core.need(fields['Uid'].split()==['20011206']*4 and fields['TracerPid']=='0','UID/tracer')
        identity()
        for pid in (parent,child):core.need(read('sha256sum /proc/%d/exe'%pid).split()[0]==core.EXE_SHA,'exe mismatch')
        maps=core.parse_maps(read('cat /proc/%d/maps'%child));instances={}
        for role,m in template['modules'].items():
            core.need(any(r['path']==m['remote_path'] for r in maps),'missing module '+role+'; stop for outer decision, no attach')
            remote='/proc/%d/root%s'%(child,m['remote_path'])
            core.need(read('sha256sum '+remote).split()[0]==m['sha256'],'module SHA '+role)
            m['device'],m['inode']=map(int,read('stat -L -c %d:%i '+remote).split(':'))
            instances[role]=core.biases(maps,m)
        core.need(len(instances['player'])==1,'ambiguous player')
        identity();core.need(time.monotonic()<deadline,'deadline before attach')
        (out/'ready.json').write_text(json.dumps({'identity':a.identity,'instances':instances},indent=2)+'\n')
        cmd=[sys.executable,str(here/'video_outer.py'),'attach',*a.identity]
        with (out/'attach.stdout').open('wb') as so,(out/'attach.stderr').open('wb') as se:
            r=subprocess.run(cmd,cwd=repo,stdout=so,stderr=se,timeout=35)
        (out/'attach.rc').write_text(str(r.returncode));core.need(r.returncode==0,'attach failed')
        cmd=[sys.executable,str(repo/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r13/observe.py'),'--admission',str(base/'r13-video-admission.json'),'--port','5039','--out',str(base/'r13-video-observer'),'--execute']
        with (out/'observe.stdout').open('wb') as so,(out/'observe.stderr').open('wb') as se:
            r=subprocess.run(cmd,cwd=repo,stdout=so,stderr=se,timeout=165)
        (out/'observe.rc').write_text(str(r.returncode));core.need(r.returncode==0,'observer incomplete; restore')
        return 0
    except Exception as ex:
        (out/'failure.json').write_text(json.dumps({'error':str(ex),'identity':a.identity,'requires_outer_restore':True},indent=2)+'\n')
        raise
if __name__=='__main__':sys.exit(main())
