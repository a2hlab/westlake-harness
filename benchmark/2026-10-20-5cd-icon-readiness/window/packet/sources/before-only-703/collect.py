#!/usr/bin/env python3
"""Only reads 5cd. UI/screenshot/lock acquisition belong to the outer."""
import argparse,json,os,re,shlex,subprocess,time,uuid
from pathlib import Path
from core import *

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--profile',type=Path,default=Path(__file__).with_name('profile.json'))
    ap.add_argument('--serial',default=SERIAL);ap.add_argument('--boot',default=BOOT)
    ap.add_argument('--phase',choices=['before-icon','after-ui'],default='before-icon')
    ap.add_argument('--before',type=Path);ap.add_argument('--player-elf',type=Path)
    ap.add_argument('--identity-receipt',type=Path)
    ap.add_argument('--hdc',type=Path);ap.add_argument('--holder');ap.add_argument('--window-start',type=float)
    ap.add_argument('--repo',type=Path,default=Path.cwd());ap.add_argument('--out',type=Path)
    ap.add_argument('--execute',action='store_true');a=ap.parse_args()
    p=profile_check(json.loads(a.profile.read_text()),a.serial,a.boot)
    if a.player_elf:elf_player(a.player_elf)
    if a.phase=='after-ui':
        need(a.before is not None,'before receipt required')
        before=json.loads((a.before/'result.json').read_text());receipt_check(before)
        need(before['phase']=='before-icon' and before.get('child') is None and before['status']=='NO_BUSINESS_CHILD','before must show no business child')
    expected=None
    if a.identity_receipt:
        need(a.phase=='after-ui','identity receipt only after-ui')
        expected=json.loads(a.identity_receipt.read_text());receipt_check(expected)
        need(expected['phase']=='after-ui' and expected['status']=='EVIDENCE_ONLY_PENDING_REVIEW','valid first after-ui receipt required')
        need(expected.get('child') and expected.get('parent'),'receipt has no business identity')
    if not a.execute:
        print(json.dumps({'execution':False,'device_calls':0,'serial':SERIAL,'phase':a.phase,'uid':UID,'player_got':'exact ELF imports only' if a.player_elf else 'unknown without exact local ELF','UI':'outer only'}));return 0
    need(a.hdc is not None and a.hdc.is_file() and a.holder and a.window_start is not None and a.out is not None,'explicit tool/holder/window-start/out required')
    need(0<=time.time()-a.window_start<600,'window deadline')
    if a.phase=='after-ui':
        need(before['window_start']==a.window_start and before['source_profile_sha256']==digest(a.profile),'before receipt window/profile drift')
    if expected:need(expected['window_start']==a.window_start,'identity receipt window drift')
    out=a.out.resolve();need(not str(out).startswith('/tmp/'),'persistent output required');out.mkdir(parents=True,exist_ok=False)
    result={'serial':SERIAL,'boot':BOOT,'uid':UID,'phase':a.phase,'window_start':a.window_start,'status':'UNKNOWN','child':None,'parent':None,'wid':'unknown; outer must correlate windows.txt and snapshot','visual_verdict':'pending_review','playback':'unknown','audio':'unknown','device_mutations':0,'app_starts':0,'attach':0,'source_profile_sha256':digest(a.profile),'modules':{},'got':'unknown'}
    count=0;identity={}
    lock=a.repo.resolve()/'scripts/lab/board_note.sh'
    def remaining():
        n=600-(time.time()-a.window_start);need(n>0,'window deadline');return n
    def run(argv,label):
        nonlocal count
        count+=1;f=out/('%03d-%s'%(count,label))
        f.with_suffix('.command.json').write_text(json.dumps({'argv':argv,'started':time.time()})+'\n')
        try:r=subprocess.run(argv,capture_output=True,timeout=min(10,remaining()))
        except subprocess.TimeoutExpired as ex:
            f.with_suffix('.stdout.txt').write_bytes(ex.stdout or b'');f.with_suffix('.stderr.txt').write_bytes(ex.stderr or b'');f.with_suffix('.rc.json').write_text('{"timeout":true}\n');raise
        f.with_suffix('.stdout.txt').write_bytes(r.stdout);f.with_suffix('.stderr.txt').write_bytes(r.stderr);f.with_suffix('.rc.json').write_text(json.dumps({'rc':r.returncode,'finished':time.time()})+'\n')
        need(r.returncode==0,'command rc '+label);return r.stdout.decode('utf8','replace')
    def read(command,label):
        held=run(['bash',str(lock),'held',SERIAL],'held');need(held.strip()==a.holder,'lock owner drift')
        guard='test "$(cat /proc/sys/kernel/random/boot_id)" = '+shlex.quote(BOOT)+'; '
        for pid,expected in identity.items():
            guard+='r=$(cat /proc/%d/stat); z=${r##*) }; set -- $z; test "${20}" = %d; test "$2" = %d; '%(pid,expected['birth'],expected['ppid'])
        marker='T11_RC_'+uuid.uuid4().hex
        script='( set -eu; '+guard+command+'; '+guard+'printf "\\n'+marker+'=0\\n" )'
        text=run([str(a.hdc.resolve()),'-t',SERIAL,'shell',script],label)
        need(text.rstrip().endswith(marker+'=0'),'remote guard/command failed '+label)
        return text.rsplit(marker+'=0',1)[0].rstrip()
    try:
        for name in ('cfg_path','run_path'):
            path=p[name];need(read('sha256sum '+shlex.quote(path),name).split()[0]==p['files'][path],'baseline '+name)
        ps=read('ps -A -o PID,PPID,UID,NAME','ps');(out/'ps.txt').write_text(ps+'\n');child=select(ps)
        (out/'windows.txt').write_text(read("hidumper -s WindowManagerService -a '-a'",'windows')+'\n')
        if child is None:result['status']='NO_BUSINESS_CHILD';return 2 if a.phase=='after-ui' else 0
        need(a.phase=='after-ui','business child existed before icon; new window not admitted')
        if expected:need(child['pid']==expected['child']['pid'] and child['ppid']==expected['parent']['pid'],'selected child changed')
        for role,pid in [('parent',child['ppid']),('child',child['pid'])]:
            st=stat(read('cat /proc/%d/stat'%pid,role+'-stat'),pid)
            uid=status(read('cat /proc/%d/status'%pid,role+'-status'),UID if role=='child' else None)
            need(read('sha256sum /proc/%d/exe'%pid,role+'-exe').split()[0]==EXE,'not business executable '+role)
            if expected:
                same_stat(expected[role],st);need(uid==expected[role]['uid'],'receipt UID drift')
            identity[pid]=st;result[role]={**st,'uid':uid,'exe_sha256':EXE}
        need(result['child']['ppid']==result['parent']['pid'],'parent relation')
        raw=read('cat /proc/%d/maps'%child['pid'],'maps');(out/'maps.txt').write_text(raw+'\n');rows=maps(raw)
        names={'player':'libttmplayer.so','android':'libandroid.so','shim':'libwebview_bionic_shim.so','bridge':'liboh_adapter_bridge.so','hwui':'libhwui.so'}
        for role,name in names.items():
            paths=sorted({r['path'] for r in rows if r['path'].endswith('/'+name)})
            records=[]
            for path in paths:
                need(not path.endswith(' (deleted)'),'deleted mapped module')
                remote='/proc/%d/root%s'%(child['pid'],path)
                sha=read('sha256sum '+shlex.quote(remote),role+'-sha').split()[0]
                meta=read("stat -L -c '%d:%i' "+shlex.quote(remote),role+'-inode')
                dev,ino=map(int,meta.split(':'));major=((dev>>8)&4095)|((dev>>32)&~4095);minor=(dev&255)|((dev>>12)&~255)
                rr=[r for r in rows if r['path']==path]
                need(all(r['inode']==ino and tuple(int(x,16) for x in r['dev'].split(':'))==(major,minor) for r in rr),'mapped file inode drift')
                records.append({'path':path,'sha256':sha,'device':dev,'inode':ino,'maps':rr})
            result['modules'][role]=records or 'unknown: not mapped'
        player=result['modules']['player']
        if a.player_elf and isinstance(player,list) and len(player)==1 and player[0]['sha256']==PLAYER:
            loads,slots=elf_player(a.player_elf);bias=load_bias(rows,player[0]['path'],loads);got={}
            for name,offset in sorted(slots.items()):
                address=bias+offset;readable_slot(rows,address)
                text=read('dd if=/proc/%d/mem bs=8 skip=%d count=1 | od -An -tx8'%(child['pid'],address//8),'got-'+name)
                need(re.fullmatch(r'\s*[0-9a-fA-F]{16}\s*',text) is not None,'short GOT read')
                value=int(text,16);got[name]={'elf_slot':hex(offset),'address':hex(address),'value':hex(value),'value_maps':[r for r in rows if r['lo']<=value<r['hi']],'object_dereferenced':False}
            result['got']=got
        for role in ('parent','child'):
            old=result[role];same_stat(old,stat(read('cat /proc/%d/stat'%old['pid'],role+'-end'),old['pid']))
        result['status']='EVIDENCE_ONLY_PENDING_REVIEW';return 0
    except Exception as ex:
        result['status']='UNKNOWN_STOPPED';result['error']=str(ex);return 2
    finally:
        result['finished']=time.time();result['command_count']=count
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'status':result['status'],'out':str(out),'visual_verdict':'pending_review'}))
if __name__=='__main__':raise SystemExit(main())
