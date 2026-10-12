#!/usr/bin/env python3
"""Guarded place-only recovery transaction. Preview never creates a transport."""
import argparse, hashlib, importlib.util, json, os, re, shlex, sys, time
from pathlib import Path

SERIAL='61b0657200000000000000000324012c'
HERE=Path(__file__).resolve().parent
ROOT='/data/westlake-demo/toutiao/recovery-attempts/r1-9763171a-preview'
CFG='/system/etc/init/01_westlake_u13_toutiao.cfg'
EXTERNAL_CONTROLS={CFG, '/data/westlake-demo/toutiao/scripts/watchdog.sh','/data/westlake-demo/toutiao/scripts/route-b-owner.sh','/data/local/tmp/operator45/selfheal48/watchdog.sh','/data/local/tmp/operator45/selfheal48/route-b-owner.sh'}
SHA=re.compile(r'[0-9a-f]{64}\Z')
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok, why):
    if not ok: raise ValueError(why)
def read(p): return json.loads(Path(p).read_text())
def q(v): return shlex.quote(str(v))
def resolve(v):
    return Path(os.path.expandvars(str(v).replace('$PACKAGE',str(HERE))))
def metadata(value,why):
    require(isinstance(value,dict),why+' missing metadata')
    require(isinstance(value.get('mode'),str) and re.fullmatch(r'[0-7]{3,4}',value['mode']) is not None,why+' mode')
    for key in ('uid','gid'):
        require(type(value.get(key)) is int and 0<=value[key]<2**31,why+' '+key)
    require(isinstance(value.get('label'),str) and re.fullmatch(r'u:object_r:[A-Za-z0-9_]+:s0',value['label']) is not None,why+' label')
def validate(plan, authorization=None, now=None, authorization_sha256=None):
    require(plan['serial']==SERIAL,'wrong serial')
    require(plan['scope']=={'61b':20,'5cd_existing_reference':128,'boat':False},'wrong scope')
    require(plan['execution_enabled'] is True,'execution disabled')
    require(authorization is not None,'missing outer authorization')
    require(SHA.fullmatch(authorization_sha256 or '') and digest(authorization)==authorization_sha256,'authorization SHA')
    auth=read(authorization)
    require(auth['approved_by']=='outer(codex)' and auth['plan_sha256']==plan['_sha'],'outer plan binding')
    require(auth['serial']==SERIAL,'authorization serial')
    require(auth.get('origin_boot_id',plan['boot_id'])==plan['boot_id'],'authorization origin')
    require(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',auth['boot_id']) is not None,'authorization boot invalid')
    require(auth['expires_epoch']>(time.time() if now is None else now),'expired')
    require(auth['actions']==['place-only','one-reboot','rollback-safe'],'wrong action set')
    require(len(plan['members'])>0 and len({r['target'] for r in plan['members']})==len(plan['members']),'empty/duplicate members')
    for r in plan['members']:
        target=r['target']
        require(target.startswith(ROOT+'/') or target in EXTERNAL_CONTROLS,'target outside controls')
        require('/..' not in target and '\n' not in target,'unsafe target')
        require(SHA.fullmatch(r['sha256']) and digest(resolve(r['source']))==r['sha256'],'member SHA '+target)
        metadata(r['after'],'after '+target)
        before=r['before']; require(isinstance(before['exists'],bool),'unknown preimage')
        if before['exists']:
            metadata(before,'before '+target)
            require(isinstance(before.get('sha256'),str) and SHA.fullmatch(before['sha256']),'unknown preimage SHA')
            require(digest(resolve(before['source']))==before['sha256'],'local preimage SHA')
        else: require(before.get('proof'),'unproven absence')
    for ref in plan['prerequisites']:
        require(SHA.fullmatch(ref['sha256']),'unknown prerequisite SHA')
    for directory in plan.get('directories',[]):
        require(directory['target'] in {ROOT, str(Path(ROOT).parent)} and directory['before']['exists'] is False,'unapproved directory')
        metadata(directory['after'],'directory')
    for tool in plan['tools'].values():
        require(digest(resolve(tool['path']))==tool['sha256'],'tool drift')
    return auth

class Device:
    """Reuse the seal driver's numbered raw transport; never run its installer/overlay."""
    def __init__(self, plan,out):
        tool=resolve(plan['tools']['driver']['path'])
        spec=importlib.util.spec_from_file_location('reviewed_seal_driver',tool)
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        self.transport=mod.Transport(out,40); self.hdc=plan['hdc']; self.serial=plan['serial']
    def command(self,name,argv):
        rc,out=self.transport.run(name,argv); require(rc==0,name+' transport rc='+str(rc)); return out
    def shell(self,name,script):
        # HDC host rc alone is not a remote exit status. Missing marker is failure.
        command='/system/bin/sh -c '+q(script)+'; re_rc=$?; printf "\\nRE_REMOTE_RC=%s\\n" "$re_rc"'
        out=self.command(name,[self.hdc,'-t',self.serial,'shell',command]).replace('\r','')
        m=re.search(r'\nRE_REMOTE_RC=(\d+)\n?\Z',out)
        require(m is not None and m.group(1)=='0',name+' remote status missing/nonzero')
        return out[:m.start()].rstrip('\n')
    def send(self,name,source,target): self.command(name,[self.hdc,'-t',self.serial,'file','send',str(source),target])
    def recv(self,name,target,dest): self.command(name,[self.hdc,'-t',self.serial,'file','recv',target,str(dest)])
    def probe(self,target):
        script='''set -eu
p=%s
walk="$p"; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
if [ -e "$p" ]; then
 test -f "$p"; echo EXISTS
 stat -c '%%a %%u %%g' "$p"
 sha256sum "$p"
 ls -ldnZ "$p"
else
 walk=$(dirname "$p"); while [ ! -e "$walk" ]; do walk=$(dirname "$walk"); done
 test -d "$walk"; test -r "$walk"; test -x "$walk"; echo ABSENT
fi''' % q(target)
        lines=self.shell('probe',script).splitlines()
        if lines==['ABSENT']: return {'exists':False}
        require(len(lines)==4 and lines[0]=='EXISTS','bad metadata '+target)
        mode,uid,gid=lines[1].split(); labels=[x for x in lines[3].split() if x.startswith('u:object_r:')]
        require(len(labels)==1,'unknown label')
        return dict(exists=True,mode=mode,uid=int(uid),gid=int(gid),sha256=lines[2].split()[0],label=labels[0])

def equal(actual,expected):
    return all(actual.get(k)==expected[k] for k in ('exists','sha256','mode','uid','gid','label') if k in expected)
def check_identity(dev,plan):
    require(dev.shell('boot','cat /proc/sys/kernel/random/boot_id')==plan.get('_active_boot',plan['boot_id']),'boot changed')
def fresh(dev,plan):
    check_identity(dev,plan)
    for directory in plan.get('directories',[]):
        dev.shell('directory-absence','test ! -e '+q(directory['target'])+' && test ! -L '+q(directory['target']))
    for r in plan['members']+plan['preserved']:
        require(equal(dev.probe(r['target']),r['before']),'preimage drift '+r['target'])
    for r in plan['prerequisites']:
        require(dev.probe(r['target']).get('sha256')==r['sha256'],'prerequisite drift '+r['target'])
def save(path,obj):
    # Receipts are never overwritten silently. Every transition has a new file.
    with Path(path).open('x') as f: json.dump(obj,f,indent=2); f.write('\n')
def place(dev,row):
    target=row['target']; meta=row['after']
    if target == CFG:
        # Adapted from demo_toutiao_slot.py:103-110. Exact control-file scope,
        # root remount iff originally ro, trap restores ro even after failure.
        stage=ROOT+'/cfg-stage-'+row['sha256']
        staged=dev.probe(stage)
        if staged['exists']: require(staged.get('sha256')==row['sha256'] and staged.get('uid')==0,'foreign cfg staging file')
        else: dev.send('cfg-stage',resolve(row['source']),stage)
        require(dev.probe(stage).get('sha256')==row['sha256'],'cfg staging SHA')
        temp=CFG+'.recovery-'+row['sha256']
        script=("set -eu; reseal=0; trap 'rc=$?; if [ \"$reseal\" = 1 ]; then mount -o ro,remount / || rc=1; fi; exit \"$rc\"' EXIT; "
                "opts=$(grep ' / ' /proc/mounts | head -n1 | cut -d' ' -f4); "
                "case ,$opts, in *,rw,*) ;; *,ro,*) mount -o rw,remount /; reseal=1;; *) exit 2;; esac; "
                "test ! -e "+q(temp)+"; test ! -L "+q(temp)+"; cp "+q(stage)+" "+q(temp)+"; "
                "chown "+q(str(meta['uid'])+':'+str(meta['gid']))+' '+q(temp)+'; chmod '+q(meta['mode'])+' '+q(temp)+'; chcon '+q(meta['label'])+' '+q(temp)+'; '
                'cmp '+q(stage)+' '+q(temp)+'; mv '+q(temp)+' '+q(CFG))
        dev.shell('cfg-atomic-remount',script)
        # The reviewed stage is retained for audit; never overwrite an unknown temp.
    else:
        dev.shell('mkdir-control','set -eu; mkdir -p '+q(str(Path(target).parent)))
        dev.send('place-control',resolve(row['source']),target)
        dev.shell('control-metadata','set -eu; chown '+q(str(meta['uid'])+':'+str(meta['gid']))+' '+q(target)+'; chmod '+q(meta['mode'])+' '+q(target)+'; chcon '+q(meta['label'])+' '+q(target))
    expected=dict(exists=True,sha256=row['sha256'],**meta)
    require(equal(dev.probe(target),expected),'candidate readback '+target)

def apply(plan,dev,out):
    fresh(dev,plan)
    backups=[]
    for n,row in enumerate(plan['members']):
        before=row['before']; local=out/('backup-%03d'%n)
        if before['exists']:
            dev.recv('backup',row['target'],local)
            require(digest(local)==before['sha256'],'backup SHA')
        backups.append(dict(target=row['target'],before=before,backup=str(local.name) if before['exists'] else None,candidate_sha256=row['sha256']))
    save(out/'transaction.json',dict(plan_sha256=plan['_sha'],serial=plan['serial'],boot_id=plan['boot_id'],backups=backups))
    fresh(dev,plan) # all backups complete before ANY controls are written
    for directory in plan.get('directories',[]):
        meta=directory['after'];target=directory['target'];check_identity(dev,plan)
        dev.shell('directory-create','set -eu; mkdir '+q(target)+'; chown '+q(str(meta['uid'])+':'+str(meta['gid']))+' '+q(target)+'; chmod '+q(meta['mode'])+' '+q(target)+'; chcon '+q(meta['label'])+' '+q(target))
        got=dev.shell('directory-readback','set -eu; test -d '+q(target)+'; test ! -L '+q(target)+"; stat -c '%a:%u:%g' "+q(target)+'; ls -ldnZ '+q(target))
        require(got.splitlines()[0]==meta['mode']+':'+str(meta['uid'])+':'+str(meta['gid']) and meta['label'] in got.splitlines()[1].split(),'directory metadata readback')
    for index,row in enumerate(plan['members']):
        check_identity(dev,plan)
        intent=out/('intent-%03d.json'%index)
        save(intent,{'plan_sha256':plan['_sha'],'serial':plan['serial'],'boot_id':plan['boot_id'],'target':row['target'],'candidate_sha256':row['sha256'],'before':row['before']})
        try:
            place(dev,row)
        except (OSError,ValueError,KeyError,TypeError) as error:
            failure={'plan_sha256':plan['_sha'],'target':row['target'],'intent_sha256':digest(intent),'error':str(error),'observation':None}
            # Collect only read-only after a failed send/mode/readback. The exact
            # observed partial bytes can later be restored, never guessed.
            try:failure['observation']=dev.probe(row['target'])
            except (OSError,ValueError,KeyError,TypeError) as probe_error:failure['observation_error']=str(probe_error)
            save(out/('failed-%03d.json'%index),failure)
            raise ValueError('placement failed; exact read-only observation recorded; '+str(error))
        save(out/('placed-%03d.json'%index),{'target':row['target'],'sha256':row['sha256']})
    for row in plan['preserved']: require(equal(dev.probe(row['target']),row['before']),'preserved object drift')
    save(out/'placed.json',{'state':'PLACED_ONLY','ui_accepted':False,'seal_signed':False,'reboots':0})

def request_cooperative_stop(dev,plan):
    """No signals or argv strings parsing. A candidate's persistent stop is new,
    not the historical stop. Exact NUL argv SHA + birth guards own lock owner."""
    boot=plan.get('_active_boot',plan['boot_id']); state=ROOT+'/boots/'+boot
    lock=state+'/lock/owner'
    owner=dev.probe(lock)
    guardian=None
    if owner['exists']:
        line=dev.shell('guardian-lock-read','cat '+q(lock)).split()
        require(len(line)==3 and line[0].isdecimal() and line[1].isdecimal() and line[2]==boot,'guardian lock identity unknown')
        pid,birth,_=line; require(int(pid)>1,'unsafe guardian PID')
        require(dev.shell('guardian-lock-exact','cat '+q(lock))==' '.join(line),'guardian owner format mismatch')
        # Exact bytes, including NUL boundaries; never use strings for argv.
        argv_sha=hashlib.sha256(('/system/bin/sh\0'+state+'/watchdog.sh\0').encode()).hexdigest()
        guard=('set -eu; p='+pid+'; row=$(cat /proc/$p/stat); rest=${row##*) }; set -- $rest; '
               'test "${20}" = '+q(birth)+'; test "$(sha256sum /proc/$p/cmdline | cut -d\' \' -f1)" = '+q(argv_sha)+'; '
               'test "$(readlink /proc/$p/exe)" = /system/bin/sh; '
               'uid=$(sed -n \'s/^Uid:[[:space:]]*//p\' /proc/$p/status); set -- $uid; '
               'test "$1:$2:$3:$4" = 0:0:0:0; '
               'row=$(cat /proc/$p/stat); rest=${row##*) }; set -- $rest; test "${20}" = '+q(birth))
        dev.shell('guardian-exact-argv-birth',guard);guardian=(pid,birth)
    # Root stop prevents next-boot restart. No old stop is removed or overwritten.
    for target in [ROOT+'/stop']+([state+'/stop'] if guardian else []):
        if not dev.probe(target)['exists']:
            dev.shell('rollback-stop-create','set -eu; set -C; umask 077; : > '+q(target)+'; test "$(wc -c < '+q(target)+')" -eq 0')
    if guardian:
        pid,birth=guardian
        for _ in range(20):
            status=dev.shell('guardian-exit-read','if [ ! -e /proc/'+pid+'/stat ]; then echo GONE; else row=$(cat /proc/'+pid+'/stat); rest=${row##*) }; set -- $rest; if [ "${20}" != '+q(birth)+' ]; then echo GONE; else echo ALIVE; fi; fi')
            if status=='GONE':break
            require(status=='ALIVE','unknown guardian exit status');time.sleep(.5)
        else:raise ValueError('candidate supervisor did not cooperatively stop; app retained, no signals')
    return guardian

def rollback(plan,dev,out):
    tx=read(out/'transaction.json')
    require(tx['plan_sha256']==plan['_sha'] and tx['serial']==SERIAL,'wrong rollback transaction')
    expected=[dict(target=r['target'],before=r['before'],backup='backup-%03d'%i if r['before']['exists'] else None,candidate_sha256=r['sha256']) for i,r in enumerate(plan['members'])]
    require(tx['backups']==expected,'rollback transaction does not match signed plan')
    check_identity(dev,plan)
    # Verify EVERY backup BEFORE any stop/CFG/control write, not one-at-a-time.
    for row in tx['backups']:
        if row['before']['exists']:
            backup=out/row['backup'];require(backup.is_file() and digest(backup)==row['before']['sha256'],'missing/corrupt backup')
    quarantine_sha=digest(HERE/'payload/rollback-inert.cfg')
    current={}
    for index,row in enumerate(tx['backups']):
        observed=dev.probe(row['target']);current[row['target']]=observed
        known_partial=False
        failure_file=out/('failed-%03d.json'%index)
        if failure_file.exists():
            failure=read(failure_file); intent_file=out/('intent-%03d.json'%index)
            expected_intent={'plan_sha256':plan['_sha'],'serial':plan['serial'],'boot_id':plan['boot_id'],'target':row['target'],'candidate_sha256':row['candidate_sha256'],'before':row['before']}
            require(intent_file.is_file() and read(intent_file)==expected_intent and failure.get('intent_sha256')==digest(intent_file),'failed operation intent mismatch')
            require(failure.get('plan_sha256')==plan['_sha'] and failure.get('target')==row['target'],'failed operation binding')
            known_partial=failure.get('observation') is not None and equal(observed,failure['observation'])
        require(equal(observed,row['before']) or observed.get('sha256')==row['candidate_sha256'] or known_partial or
                (row['target']==CFG and observed.get('sha256')==quarantine_sha),'foreign/unobserved partial replacement: '+row['target'])
    if all(equal(current[r['target']],r['before']) for r in tx['backups']):
        if not (out/'rollback.json').exists():save(out/'rollback.json',{'state':'NO_MEMBER_CHANGES_NO_DONOR_RESTART','app_signals':0})
        return
    request_cooperative_stop(dev,plan)
    for row in reversed(tx['backups']):
        observed=current[row['target']];before=row['before']
        require(equal(dev.probe(row['target']),observed),'rollback target changed after guard')
        if row['target']==CFG:
            # Always quarantine, even if apply stopped before cfg activation.
            # Exact unsafe cfg preimage retained in backups; never auto-enable.
            if observed.get('sha256')!=quarantine_sha:
                safe=HERE/'payload/rollback-inert.cfg'
                place(dev,dict(target=CFG,source=str(safe),sha256=quarantine_sha,after={k:before[k] for k in ('mode','uid','gid','label')}))
            continue
        if equal(observed,before):continue
        if before['exists']:
            backup=out/row['backup']
            place(dev,dict(target=row['target'],source=str(backup),sha256=before['sha256'],after={k:before[k] for k in ('mode','uid','gid','label')}))
        else:
            dev.shell('remove-own-addition','set -eu; ! grep -F '+q(' '+row['target']+' ')+' /proc/self/mountinfo; rm '+q(row['target']))
            require(not dev.probe(row['target'])['exists'],'addition removal')
    # Evidence/stop directories are intentionally retained, never rmtree.
    receipt=out/'rollback.json'
    if not receipt.exists():save(receipt,{'state':'ROLLED_BACK_CONTROLS_BOOT_TRIGGER_QUARANTINED','unsafe_donor_restarted':False,'app_signals':0})

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',default=str(HERE/'plan.disabled.json'));p.add_argument('--execute',action='store_true');p.add_argument('--authorization');p.add_argument('--authorization-sha256');p.add_argument('--out');p.add_argument('--action',choices=['apply','rollback'],default='apply');a=p.parse_args(argv)
    plan=read(a.plan);plan['_sha']=digest(a.plan)
    if not a.execute:
        print(json.dumps({'status':'PREVIEW','device_calls':0,'execution_enabled':False,'members':len(plan['members']),'plan_sha256':plan['_sha'],'action':a.action}));return 0
    try:
        auth=validate(plan,a.authorization,authorization_sha256=a.authorization_sha256);
        if a.action=='apply': require(auth['boot_id']==plan['boot_id'],'apply boot changed')
        plan['_active_boot']=auth['boot_id']
        require(a.out,'output required');out=Path(a.out)
        if a.action=='apply':out.mkdir(exist_ok=False)
        else:require(out.is_dir(),'missing backups')
        dev=Device(plan,out);globals()[a.action](plan,dev,out);return 0
    except (OSError,ValueError,KeyError,TypeError) as e:
        print('RECOVERY-EXECUTOR REJECT: '+str(e),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
