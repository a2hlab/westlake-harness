#!/usr/bin/env python3
"""Narrow, receipt-backed placement of a new Toutiao control root and one init cfg."""
import argparse
import hashlib
import json
import re
import shlex
import subprocess
from pathlib import Path

SERIAL = '61b0657200000000000000000324012c'
CFG = '/system/etc/init/01_westlake_u13_toutiao.cfg'
OLD_ROOT = '/data/westlake-demo/toutiao/recovery-attempts/r1-9763171a-preview'
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

class Device:
    def __init__(self, out):
        self.out=out; self.n=0
    def run(self,args):
        self.n+=1; name=f'{self.n:03d}'
        r=subprocess.run(['hdc','-t',SERIAL]+args,capture_output=True,timeout=60)
        (self.out/(name+'.stdout.txt')).write_bytes(r.stdout)
        (self.out/(name+'.stderr.txt')).write_bytes(r.stderr)
        (self.out/(name+'.json')).write_text(json.dumps({'argv':['hdc','-t',SERIAL]+args,'rc':r.returncode},indent=2)+'\n')
        require(r.returncode==0, 'hdc failure '+name)
        return r.stdout.decode(errors='replace')
    def shell(self,script):
        # Subshell prevents an exit in the transaction from swallowing its receipt.
        result=self.run(['shell','( set -eu; '+script+'\n); icon_rc=$?; echo ICON_REMOTE_RC=$icon_rc'])
        require(re.findall(r'^ICON_REMOTE_RC=(\d+)\r?$', result,re.M)==['0'], 'remote failure')
        return result
    def send(self,src,target):
        text=self.run(['file','send',str(src),target])
        require('FileTransfer finish' in text, 'file transfer receipt')

def execute(plan,folder,out,rollback,boot,plan_sha,apply_receipt=None):
    validate(plan,folder); uuid(boot)
    root=plan['root']
    # Locate repository from the script rather than the caller's cwd.
    repo=Path(__file__).resolve().parents[2]
    held=subprocess.run(['bash',str(repo/'scripts/lab/board_note.sh'),'held',SERIAL],capture_output=True,text=True)
    require(held.returncode==0 and held.stdout.split()[0]=='outer(codex)','outer board lock missing')
    binding = {'serial':SERIAL,'cfg':CFG,'origin_boot':plan['boot'],'root':root,'before_sha256':plan['before_sha256'],'after_sha256':plan['after_sha256'],'plan_sha256':plan_sha}
    if rollback:
        require(apply_receipt is not None, 'original apply transaction receipt required')
        require(json.loads(apply_receipt.read_text()) == binding, 'apply receipt binding differs')
    out.mkdir(parents=True,exist_ok=False); dev=Device(out)
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
    p.add_argument('--rollback',action='store_true');p.add_argument('--boot');p.add_argument('--out',type=Path);p.add_argument('--apply-receipt',type=Path)
    a=p.parse_args(); folder=a.plan.resolve().parent;plan=json.loads(a.plan.read_text());validate(plan,folder)
    boot=a.boot or plan['boot'];uuid(boot)
    if a.execute:
        require(a.out is not None,'new output required');execute(plan,folder,a.out,a.rollback,boot,sha(a.plan),a.apply_receipt)
    else: print(cfg_script(plan,a.rollback,boot))
if __name__=='__main__':main()
