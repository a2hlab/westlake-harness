#!/usr/bin/env python3
"""Narrow, receipt-backed placement of a new Toutiao control root and one init cfg."""
import argparse
import hashlib
import json
import re
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path

SERIAL = '61b0657200000000000000000324012c'
CFG = '/system/etc/init/01_westlake_u13_toutiao.cfg'
OLD_ROOT = '/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261021-r3'
q = shlex.quote

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def require(ok, why):
    if not ok:
        raise ValueError(why)

def uuid(s):
    require(bool(re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', s)), 'invalid boot')

def local_file(folder, path):
    require(path.resolve().is_relative_to(folder.resolve()), 'source outside package')
    walk = path
    while walk != folder:
        require(not walk.is_symlink(), 'source symlink')
        walk = walk.parent
    require(path.is_file(), 'source missing')
    return path

def validate(plan, folder):
    require(plan['serial'] == SERIAL and plan['cfg'] == CFG, 'target scope')
    uuid(plan['boot'])
    root = plan['root']
    require(bool(re.fullmatch(re.escape('/data/westlake-demo/toutiao/recovery-attempts/icon-manual-') + r'[a-z0-9-]+', root)), 'new root scope')
    names = set()
    for row in plan['files']:
        name = row['name']
        require(bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name)), 'file name')
        require(name not in ('before.cfg','after.cfg','plan.json','transaction.json'), 'reserved member')
        require(name not in names, 'duplicate member')
        names.add(name)
        require(row['mode'] in ('440', '550'), 'member mode')
        p = local_file(folder, folder / 'payload' / name)
        require(p.is_file() and not p.is_symlink() and sha(p) == row['sha256'], 'source SHA ' + name)
    require({'boot-entry.sh','entry.sh','watchdog.sh','startup.env','startup.expected.sha256','members.tsv','config-common.sh'} <= names, 'missing controls')
    old = local_file(folder, folder / 'before.cfg'); new = local_file(folder, folder / 'after.cfg')
    require(sha(old) == plan['before_sha256'] and sha(new) == plan['after_sha256'], 'cfg SHA')
    a = json.loads(old.read_text()); b = json.loads(new.read_text())
    require(len(a['services']) == 1 and a['services'][0]['path'] == ['/system/bin/sh', OLD_ROOT + '/boot-entry.sh'], 'unexpected original service')
    a['services'][0]['path'][1] = root + '/boot-entry.sh'
    require(a == b, 'cfg change beyond entry path')
    require(re.findall(r'^ROOT=[\"\']?([^\"\'\s]+)[\"\']?$', (folder/'payload/config-common.sh').read_text(), re.M) == [root], 'config root mismatch')
    require(sha(folder/'payload/startup.env') == (folder/'payload/startup.expected.sha256').read_text().strip(), 'startup signature')
    startup = dict(re.findall(r"^([A-Z0-9_]+)='([^']*)'$", (folder/'payload/startup.env').read_text(), re.M))
    require(startup.get('STARTUP_APPROVED_BY') == 'outer(codex)' and startup.get('STARTUP_ENABLED') == '1' and startup.get('STARTUP_SERIAL') == SERIAL, 'startup authority')
    require(startup.get('STARTUP_MEMBERS_SHA') == sha(folder/'payload/members.tsv'), 'member manifest binding')
    by_name = {r['name']:r for r in plan['files']}
    seen = set()
    for line in (folder/'payload/members.tsv').read_text().splitlines():
        digest, name, mode = line.split()
        require(name in by_name and name not in seen, 'manifest member')
        seen.add(name)
        require(by_name[name]['sha256'] == digest and by_name[name]['mode'] == mode, 'manifest hash or mode')
    required_members={'entry.sh','watchdog.sh','config-common.sh','route-b-owner.sh','launch-common.sh','real-start-parent.sh','real-spawn.sh','start-parent.sh','spawn.sh','screen-gate','decoder-probe.jpeg','real-start-parent-bounded.sh','readiness-probe.sh','reentry-common.sh','reentry-seams.sh','exit-verdict.sh'}
    require(required_members <= seen,'missing boot-copy member')
    for key,name in [('STARTUP_DECODER_SHA','screen-gate'),('STARTUP_PROBE_SHA','decoder-probe.jpeg')]:
        require(startup.get(key)==by_name[name]['sha256'],'startup leaf '+name)
    entry=(folder/'payload/entry.sh').read_text()
    for name in ('watchdog.sh','route-b-owner.sh'):
        pins=re.findall(r'sha256sum "\$HERE/'+re.escape(name)+r'"[^\n]*?= ([0-9a-f]{64}) \]',entry)
        require(pins==[by_name[name]['sha256']],'entry leaf '+name)
    for name in seen:
        if not name.endswith('.sh'):continue
        body=(folder/'payload'/name).read_text()
        dependencies=re.findall(r'^\s*\. "\$(?:HERE|F)/([A-Za-z0-9._-]+)"',body,re.M)
        require(all(dep in seen for dep in dependencies),'uncopied source dependency '+name)
    require(root!=OLD_ROOT,'new root equals before root')
    return plan

def path_guard(path):
    return 'walk='+q(path)+'; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done\n'

def file_guard(path, digest, mode, label):
    return path_guard(path) + f'''test -f {q(path)}
test "$(sha256sum {q(path)} | cut -d' ' -f1)" = {q(digest)}
test "$(stat -c %a:%u:%g {q(path)})" = {q(mode+':0:0')}
ls -ldnZ {q(path)} | grep -F {q(label)} >/dev/null
'''

def cfg_script(plan, rollback=False, boot=None):
    root = plan['root']; boot = boot or plan['boot']; uuid(boot)
    expected = plan['after_sha256'] if rollback else plan['before_sha256']
    wanted = plan['before_sha256'] if rollback else plan['after_sha256']
    source = root + ('/before.cfg' if rollback else '/after.cfg')
    temp = CFG + '.icon-' + wanted[:16]
    return f'''#!/system/bin/sh
set -eu
reseal=0
finish() {{
 rc=$?
 trap - EXIT
 if [ "$reseal" = 1 ]; then
  mount -o ro,remount / || rc=1
  opts=$(grep ' / ' /proc/mounts | head -n1 | cut -d' ' -f4)
  case ,$opts, in *,ro,*) :;; *) rc=1;; esac
 fi
 if [ "$rc" = 0 ]; then printf 'ICON_CFG_OK {wanted}\\n'; fi
 exit "$rc"
}}
trap finish EXIT
test "$(cat /proc/sys/kernel/random/boot_id)" = {q(boot)}
''' + file_guard(CFG, expected, '550','u:object_r:system_etc_file:s0') + file_guard(source,wanted,'440','u:object_r:data_file:s0') + path_guard(temp) + f'''test ! -e {q(temp)}
opts=$(grep ' / ' /proc/mounts | head -n1 | cut -d' ' -f4)
case ,$opts, in *,ro,*) reseal=1; mount -o rw,remount /;; *) echo REFUSE_ORIGINAL_ROOT_NOT_RO >&2; exit 2;; esac
''' + file_guard(CFG, expected, '550','u:object_r:system_etc_file:s0') + f'''cp {q(source)} {q(temp)}
chown 0:0 {q(temp)}
chmod 550 {q(temp)}
chcon u:object_r:system_etc_file:s0 {q(temp)}
''' + file_guard(temp,wanted,'550','u:object_r:system_etc_file:s0') + f'''test "$(cat /proc/sys/kernel/random/boot_id)" = {q(boot)}
mv {q(temp)} {q(CFG)}
''' + file_guard(CFG,wanted,'550','u:object_r:system_etc_file:s0')

def check_session(session, plan_sha, repo):
    require(isinstance(session,dict),'signed session required')
    require(session.get('approved_by')=='outer(codex)' and session.get('serial')==SERIAL,'session authority')
    require(session.get('plan_sha256')==plan_sha,'session plan SHA')
    holder=session.get('holder',''); parts=holder.split()
    require(len(parts)==3 and parts[0]=='inner(cc-video)' and parts[1].isdigit(),'full CC holder')
    start=session.get('start')
    require(type(start) in (int,float) and abs(datetime.fromisoformat(parts[2]).timestamp()-start)<1,'holder start mismatch')
    require(start<=time.time(),'future window start')
    require(datetime.fromisoformat(parts[2]).tzinfo is not None,'holder timezone required')
    require(session.get('source_pins')=={ 'deploy.py':sha(Path(__file__)), 'prepare.py':sha(Path(__file__).with_name('prepare.py')), 'board_note.sh':sha(repo/'scripts/lab/board_note.sh')},'source pins mismatch')
    return session

class Device:
    def __init__(self,out,session,repo,boot,rollback=False,hdc='hdc'):
        self.out=out; self.n=0; self.session=session; self.repo=repo; self.boot=boot; self.hdc=hdc
        # Wall-clock start is bound to the holder; subsequent budget is monotonic.
        self.deadline=time.monotonic()+session['start']+(1800 if rollback else 1200)-time.time()
    def raw(self,argv):
        remain=self.deadline-time.monotonic();require(remain>0,'window budget exhausted')
        self.n+=1;name=f'{self.n:03d}'
        (self.out/(name+'.argv.json')).write_text(json.dumps(argv,indent=2)+'\n')
        timed=False
        try:
            r=subprocess.run(argv,capture_output=True,timeout=min(60,remain));out=r.stdout;err=r.stderr;rc=r.returncode
        except subprocess.TimeoutExpired as e:
            out=e.stdout or b'';err=e.stderr or b'';rc=124;timed=True
        (self.out/(name+'.stdout.txt')).write_bytes(out)
        (self.out/(name+'.stderr.txt')).write_bytes(err)
        (self.out/(name+'.rc')).write_text(str(rc)+'\n')
        (self.out/(name+'.json')).write_text(json.dumps({'argv':argv,'rc':rc,'timeout':timed})+'\n')
        require(rc==0,'command failed/unknown '+name)
        return out.decode(errors='replace')
    def ready(self):
        got=self.raw(['bash',str(self.repo/'scripts/lab/board_note.sh'),'held',SERIAL])
        require(got.strip()==self.session['holder'],'exact holder drift')
        got=self.raw([self.hdc,'-t',SERIAL,'shell','cat /proc/sys/kernel/random/boot_id'])
        require(got.strip()==self.boot,'boot drift')
    def run(self,args):
        self.ready()
        return self.raw([self.hdc,'-t',SERIAL]+args)
    def shell(self,script):
        require(len(script.encode())<=32768,'shell exceeds bounded transport size')
        # Fixed remote frame must survive HDC transport reporting local rc0.
        result=self.run(['shell','( set -eu; '+script+'\n); icon_rc=$?; echo ICON_REMOTE_RC=$icon_rc'])
        require(re.findall(r'^ICON_REMOTE_RC=(\d+)\r?$',result,re.M)==['0'],'remote failure')
        return result
    def send(self,src,target):
        text=self.run(['file','send',str(src),target])
        require('FileTransfer finish' in text,'file transfer receipt')

def execute(plan,folder,out,rollback,boot,plan_sha,apply_receipt=None,session=None,repo=None,hdc='hdc'):
    validate(plan,folder); uuid(boot)
    root=plan['root']
    repo=Path(repo).resolve() if repo else next(p for p in Path(__file__).resolve().parents if (p/'scripts/lab/board_note.sh').is_file())
    check_session(session,plan_sha,repo)
    binding = {'serial':SERIAL,'cfg':CFG,'origin_boot':plan['boot'],'root':root,'before_sha256':plan['before_sha256'],'after_sha256':plan['after_sha256'],'plan_sha256':plan_sha,'holder':session['holder'],'start':session['start'],'source_pins':session['source_pins']}
    if rollback:
        require(apply_receipt is not None, 'original apply transaction receipt required')
        require(json.loads(apply_receipt.read_text()) == binding, 'apply receipt binding differs')
    out.mkdir(parents=True,exist_ok=False); dev=Device(out,session,repo,boot,rollback,hdc)
    (out/'transaction.json').write_text(json.dumps(binding,indent=2)+'\n')
    dev.shell('test "$(cat /proc/sys/kernel/random/boot_id)" = '+q(boot))
    if not rollback:
        require(boot==plan['boot'],'apply boot differs from plan')
        dev.shell(file_guard(CFG,plan['before_sha256'],'550','u:object_r:system_etc_file:s0')+path_guard(root)+f'test ! -e {q(root)}\nmkdir {q(root)}\nchown 0:0 {q(root)}\nchmod 750 {q(root)}\nchcon u:object_r:data_file:s0 {q(root)}')
        owned = dev.shell('stat -c %d:%i '+q(root)).splitlines()[0].strip()
        require(bool(re.fullmatch(r'[0-9]+:[0-9]+', owned)), 'root inode receipt')
        members=[(folder/'payload'/r['name'],root+'/'+r['name'],r['sha256'],r['mode']) for r in plan['files']]
        members += [(folder/'before.cfg',root+'/before.cfg',plan['before_sha256'],'440'),(folder/'after.cfg',root+'/after.cfg',plan['after_sha256'],'440')]
        for src,dest,digest,mode in members:
            dev.shell(path_guard(root)+f'test -d {q(root)}\ntest \"$(stat -c %d:%i {q(root)})\" = {q(owned)}\ntest ! -e {q(dest)}\ntest ! -L {q(dest)}')
            dev.send(src,dest)
            dev.shell(f'chown 0:0 {q(dest)}\nchmod {mode} {q(dest)}\nchcon u:object_r:data_file:s0 {q(dest)}\n'+file_guard(dest,digest,mode,'u:object_r:data_file:s0'))
        # All controls verified once more immediately before switching cfg.
        dev.shell(''.join(file_guard(dest,digest,mode,'u:object_r:data_file:s0') for _,dest,digest,mode in members))
    if rollback:
        observed = dev.shell('sha256sum '+q(CFG)).splitlines()[0].split()[0]
        require(observed in (plan['before_sha256'],plan['after_sha256']), 'foreign cfg, rollback refused')
        # A previous remount failure may leave rw. A bound rollback first repairs ro,
        # recording that operation independently; ordinary apply still refuses rw.
        dev.shell(file_guard(CFG,observed,'550','u:object_r:system_etc_file:s0') + \
            "opts=$(grep ' / ' /proc/mounts | head -n1 | cut -d' ' -f4)\ncase ,$opts, in *,rw,*) mount -o ro,remount /;; *,ro,*) :;; *) exit 2;; esac\nopts=$(grep ' / ' /proc/mounts | head -n1 | cut -d' ' -f4)\ncase ,$opts, in *,ro,*) :;; *) exit 2;; esac")
        if observed == plan['before_sha256']:
            (out/'result.json').write_text(json.dumps(dict(binding,status='ORIGINAL_CFG_UNCHANGED',boot=boot),indent=2)+'\n')
            return
    script=cfg_script(plan,rollback,boot)
    (out/'cfg-transaction.sh').write_text(script)
    result=dev.shell(script)
    wanted=plan['before_sha256'] if rollback else plan['after_sha256']
    require('ICON_CFG_OK '+wanted in result,'cfg success receipt absent')
    (out/'result.json').write_text(json.dumps({'status':'CFG_RESTORED' if rollback else 'PLACED_REQUIRES_NEW_BOOT','boot':boot,'serial':SERIAL,'cfg_sha256':wanted,'plan_sha256':plan_sha,'runtime_changed':False},indent=2)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True);p.add_argument('--execute',action='store_true')
    p.add_argument('--session',type=Path);p.add_argument('--repo',type=Path);p.add_argument('--hdc',default='hdc')
    p.add_argument('--rollback',action='store_true');p.add_argument('--boot');p.add_argument('--out',type=Path);p.add_argument('--apply-receipt',type=Path)
    a=p.parse_args(); folder=a.plan.resolve().parent;plan=json.loads(a.plan.read_text());validate(plan,folder)
    boot=a.boot or plan['boot'];uuid(boot)
    if a.execute:
        require(a.out is not None,'new output required');execute(plan,folder,a.out,a.rollback,boot,sha(a.plan),a.apply_receipt,json.loads(a.session.read_text()) if a.session else None,a.repo,a.hdc)
    else: print(cfg_script(plan,a.rollback,boot))
if __name__=='__main__':main()
