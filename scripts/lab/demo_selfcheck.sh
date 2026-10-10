#!/bin/bash
# Read-only demo-seal verification. No lock, install, start, settings or board writes.
# bash demo_selfcheck.sh --seal seal.json --serial <full-key>
# --observed fixture.json performs an explicitly OFFLINE comparison (never live PASS).
set -euo pipefail
SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
exec python3 - "$SELF_DIR" "$@" <<'PY'
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import uuid

HERE=Path(sys.argv.pop(1))
sys.path.insert(0,str(HERE))
import lab_paths

PATH_RE=re.compile(r'/[A-Za-z0-9_./:+@-]+\Z')
PATTERN_RE=re.compile(r'/[A-Za-z0-9_./:+@*?-]+\Z')
IDENT=re.compile(r'[A-Za-z_][A-Za-z0-9_.]*\Z')
SHA=re.compile(r'[0-9a-f]{64}\Z')

def board_path(p,pattern=False):
    if not isinstance(p,str) or not (PATTERN_RE if pattern else PATH_RE).fullmatch(p) or '..' in p.split('/'):
        raise ValueError('unsafe board path: '+str(p))
    return p

def seal_check(s,serial):
    if not isinstance(s,dict): raise ValueError('seal must be an object')
    if s.get('schema')!='demo-seal/v1': raise ValueError('schema must be demo-seal/v1')
    if serial not in lab_paths.boards('oh') or s.get('serial')!=serial: raise ValueError('wrong or non-whitelisted serial')
    groups=s.get('files')
    if not isinstance(groups,dict) or set(groups)!={'runtime','boot','overlays','installation'}:
        raise ValueError('files must contain runtime,boot,overlays,installation')
    all_files={}
    for group,files in groups.items():
        if not isinstance(files,dict) or (group!='overlays' and not files): raise ValueError('empty or invalid files.'+group)
        for p,h in files.items():
            board_path(p)
            if not isinstance(h,str) or not SHA.fullmatch(h): raise ValueError('invalid SHA: '+p)
            if p in all_files and all_files[p]!=h: raise ValueError('conflicting duplicate path: '+p)
            all_files[p]=h
    system=s.get('system_params')
    if not isinstance(system,dict) or not system: raise ValueError('system_params required')
    for k,v in system.items():
        if not IDENT.fullmatch(k) or not isinstance(v,str) or not v: raise ValueError('invalid system parameter')
    packages=s.get('packages');seen=set()
    if not isinstance(packages,list) or not packages: raise ValueError('nonempty packages required')
    for p in packages:
        name=p.get('package')
        if not isinstance(name,str) or not IDENT.fullmatch(name) or name in seen: raise ValueError('invalid or duplicate package')
        seen.add(name);board_path(p.get('apk_path'))
        if not SHA.fullmatch(str(p.get('apk_sha256',''))) or not str(p.get('version_code','')).isdigit(): raise ValueError('invalid package identity: '+name)
    inventories=s.get('inventories',[])
    if not isinstance(inventories,list): raise ValueError('invalid inventories')
    for i in inventories:
        if not isinstance(i.get('patterns'),list) or not i['patterns']:raise ValueError('empty inventory patterns')
        for p in i['patterns']:board_path(p,True)
        paths=i.get('paths')
        if not isinstance(paths,list) or not paths or len(paths)!=len(set(paths)):raise ValueError('inventory requires exact unique paths')
        for p in paths:
            if board_path(p) not in all_files:raise ValueError('inventory path has no sealed SHA: '+p)
    return all_files

def walk(obj):
    if isinstance(obj,dict):
        yield obj
        for v in obj.values():yield from walk(v)
    elif isinstance(obj,list):
        for v in obj:yield from walk(v)

def read_live(seal,serial,files):
    commands=[];errors=[]
    tool=lab_paths.tools()/'hdc_mac.sh'
    prefix=([str(tool)] if shutil.which('mac') else ['orb','-m','a2hlab','bash',str(tool)])
    def read(command):
        marker='__DEMO_READ_RC_'+uuid.uuid4().hex+'__'
        wrapped=command+'; demo_rc=$?; printf "\\n'+marker+'%s\\n" "$demo_rc"'
        env=dict(os.environ)
        if sys.platform=='darwin':env.setdefault('MAC_HOME',str(Path.home()))
        try:
            r=subprocess.run(prefix+['-t',serial,'shell',wrapped],text=True,capture_output=True,timeout=45,env=env)
            match=re.search(re.escape(marker)+r'(\d+)\s*$',r.stdout)
            rc=int(match.group(1)) if r.returncode==0 and match else None
            text=r.stdout[:match.start()].rstrip() if match else r.stdout
            commands.append({'command':command,'transport_rc':r.returncode,'remote_rc':rc})
            if rc is None:errors.append('transport/status marker unavailable: '+command)
            elif rc!=0:errors.append('read rc='+str(rc)+': '+command)
            return text if rc==0 else ''
        except (OSError,subprocess.TimeoutExpired) as e:
            errors.append('transport: '+str(e));commands.append({'command':command,'error':type(e).__name__});return ''
    observation={'serial':serial,'files':{},'system_params':{},'packages':{},'inventories':[], 'commands':commands,'errors':errors}
    observation['boot_before']=read('cat /proc/sys/kernel/random/boot_id').strip()
    paths=list(files)+[p['apk_path'] for p in seal['packages']]
    for start in range(0,len(paths),24):
        text=read('sha256sum '+' '.join(shlex.quote(p) for p in paths[start:start+24]))
        for h,p in re.findall(r'^([0-9a-f]{64})\s+(/\S+)$',text,re.M):observation['files'][p]=h
    for k in seal['system_params']:observation['system_params'][k]=read('param get '+k).strip()
    for p in seal['packages']:
        name=p['package'];text=read('bm dump -n '+name)
        try:
            data,_=json.JSONDecoder().raw_decode(text[text.index('{'):])
            codes={str(n['versionCode']) for n in walk(data) if (n.get('name')==name or n.get('bundleName')==name) and 'versionCode' in n}
            if len(codes)!=1:raise ValueError('missing/ambiguous matching bundle versionCode')
            observation['packages'][name]={'version_code':codes.pop()}
        except (ValueError,KeyError) as e:errors.append('bm identity '+name+': '+str(e))
    for i in seal.get('inventories',[]):
        text=read('sha256sum '+' '.join(i['patterns']))
        observation['inventories'].append(sorted(p for _,p in re.findall(r'^([0-9a-f]{64})\s+(/\S+)$',text,re.M)))
    observation['boot_after']=read('cat /proc/sys/kernel/random/boot_id').strip()
    return observation

def compare(seal,serial,files,obs,offline):
    checks=[]
    def check(path,expected,actual):
        ok=actual==expected;checks.append({'path':path,'expected':expected,'actual':actual,'equal':ok})
        print(('EQUAL ' if ok else 'DRIFT ')+path+' expected='+str(expected)+' actual='+str(actual))
    check('serial',serial,obs.get('serial'))
    stable=bool(obs.get('boot_before')) and obs.get('boot_before')==obs.get('boot_after')
    check('stable-boot',True,stable)
    check('read-errors',[],obs.get('errors',[]))
    for p,h in sorted(files.items()):check(p,h,obs.get('files',{}).get(p))
    for k,v in seal['system_params'].items():check('param:'+k,v,obs.get('system_params',{}).get(k))
    for p in seal['packages']:
        name=p['package'];check('package:'+name+':versionCode',str(p['version_code']),str(obs.get('packages',{}).get(name,{}).get('version_code','<absent>')))
        check(p['apk_path'],p['apk_sha256'],obs.get('files',{}).get(p['apk_path']))
    for n,i in enumerate(seal.get('inventories',[])):
        observed=obs.get('inventories',[]);check('inventory:'+str(n),sorted(i['paths']),observed[n] if n<len(observed) else None)
    passed=all(c['equal'] for c in checks)
    return {'schema':'demo-selfcheck/v1','mode':'offline-comparison' if offline else 'live-readonly',
            'status':('OFFLINE_MATCH' if offline else 'PASS') if passed else 'FAIL',
            'passed':passed,'remote_write_operations':0,'lock_operations':0,'checks':checks,
            'boot_before':obs.get('boot_before'),'boot_after':obs.get('boot_after'),
            'commands':obs.get('commands',[])}

def main():
    ap=argparse.ArgumentParser(description='Read-only sealed demo identity comparison')
    ap.add_argument('--seal',type=Path,required=True);ap.add_argument('--serial',required=True)
    ap.add_argument('--observed',type=Path,help='offline recorded comparison only; no HDC')
    ap.add_argument('--out',type=Path,help='fresh host-side JSON receipt; never a board file')
    a=ap.parse_args()
    try:
        if a.out and a.out.exists():raise ValueError('fresh output required')
        seal=json.loads(a.seal.read_text());files=seal_check(seal,a.serial)
        obs=json.loads(a.observed.read_text()) if a.observed else read_live(seal,a.serial,files)
        if not isinstance(obs,dict):raise ValueError('observation must be an object')
        result=compare(seal,a.serial,files,obs,bool(a.observed))
        if a.out:a.out.write_text(json.dumps(result,indent=2)+'\n')
        print(result['status']);return 0 if result['passed'] else 1
    except (OSError,ValueError,KeyError,TypeError) as e:
        print('REJECT '+str(e),file=sys.stderr);return 2
raise SystemExit(main())
PY
