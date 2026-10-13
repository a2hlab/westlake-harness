#!/usr/bin/env python3
"""Offline automatic original-receipt binding. Preview by default; no fabricated evidence."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile

from collect_actual import WS, MAIN, SERIAL, MANIFEST, need, pin, read, sha, save, portable

HERE=Path(__file__).resolve().parent
COMPILER=HERE.parent/'installed-identity-5ea/compile_index.py'
COMPILER_SHA='5b2e4e38db6befbe35ad6be6f11417dbaaa1e1589e30b16ac6f43aa492968a53'
OUTER=MAIN/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer'
PREFLIGHT=OUTER/'smoke10-r4b/install-preflight'
MARKER=re.compile(r'\n__(?:BMS_REMOTE_RC|EXACT_READ_RC)_[a-fA-F0-9]+__([0-9]+)\s*$')


def expand(p):
    return Path(str(p).replace('$WORKSPACES',str(WS))).resolve()


def original_reading(receipt_path):
    receipt_path=Path(receipt_path)
    stem=receipt_path.with_suffix('')
    result={'receipt':pin(receipt_path)}
    for field in ['stdout','stderr']:
        files=[Path(str(stem)+'.'+field+suffix) for suffix in ['.txt','']]
        files=[p for p in files if p.is_file()]
        need(len(files)==1,'missing/ambiguous original '+field+': '+portable(receipt_path))
        result[field]=pin(files[0])
    return result


def original_command(p):
    binding=original_reading(p);d=read(p);argv=d['argv']
    need(argv.count('-t')==1,'missing serial in original command')
    n=argv.index('-t');need(argv[n+1:n+3]==[SERIAL,'shell'],'foreign original command serial')
    need(d.get('exit_code',d.get('rc',d.get('transport_rc')))==0,'failed original command')
    need(not expand(binding['stderr']['path']).read_text().strip(),'original command stderr nonempty')
    command=' '.join(argv[n+3:]);text=expand(binding['stdout']['path']).read_text()
    marker=MARKER.search(text)
    if '__BMS_REMOTE_RC_' in command or '__EXACT_READ_RC_' in command:
        need(marker is not None and int(marker[1])==0,'original remote marker missing/failed')
    if marker:
        need(int(marker[1])==0,'original remote failure');text=text[:marker.start()]
    need(d.get('remote_rc',0)==0,'original remote rc failure')
    t=d.get('finished',d.get('time',d.get('finished_at')))
    need(isinstance(t,(int,float)) and not isinstance(t,bool),'original numeric time required')
    return {'reading':binding,'text':text.strip(),'time':t,'command':command,'receipt_path':portable(p)}


def discover(roots,boot_id):
    initial=read(PREFLIGHT/'apk-identity.json')
    need(initial['serial']==SERIAL and initial['boot_id']==boot_id,'initial serial/boot mismatch')
    required={r['key'] for r in initial['rows'] if r['status']!='MATCH'}
    records={};duplicates=[]
    for root in roots:
        if not root.is_dir():continue
        for p in sorted(root.rglob('record.json')):
            r=read(p);key=r.get('key')
            if key not in required or r.get('status')!='installed' or r.get('install_only') is not True:continue
            if key in records:duplicates.append(key)
            records[key]=(p,r)
    need(not duplicates,'ambiguous actual install records: '+','.join(sorted(duplicates)))
    result=[];audit=[]
    for key,(p,r) in sorted(records.items()):
        need(r.get('serial')==SERIAL,'foreign actual installation record')
        output=expand(r['install']['output']);need(output.is_file(),'missing original install output')
        commands=p.parent.parent/'commands';need(commands.is_dir(),'original commands directory missing')
        installs=[];boots=[]
        for q in sorted(commands.glob('*.json')):
            raw=read(q);cmd=' '.join(raw.get('argv',[]))
            is_install='bm install' in cmd and '/'+key+'/' in cmd
            is_boot='cat /proc/sys/kernel/random/boot_id' in cmd
            if not (is_install or is_boot):continue
            c=original_command(q)
            if is_install and c['time']<=r['finished_at']:installs.append(c)
            if is_boot and c['text']==boot_id:boots.append(c)
        need(len(installs)==1,'unique key-addressed original bm install required: '+key)
        install=installs[0]
        need(install['text']==output.read_text().strip(),'original command/output mismatch: '+key)
        before=[b for b in boots if b['time']<=install['time']]
        after=[b for b in boots if install['time']<=b['time']<=r['finished_at']]
        need(bool(before) and bool(after),'actual install boot bookends missing: '+key)
        first=max(before,key=lambda b:b['time']);last=min(after,key=lambda b:b['time'])
        result.append({'key':key,'record':pin(p),'output':pin(output),'boot_before':first['reading'],
                       'install_command':install['reading'],'boot_after':last['reading']})
        audit.append({'key':key,'before':first['time'],'install':install['time'],'after':last['time'],
                      'record_finished_at':r['finished_at'],'record':pin(p),
                      'boot_before':first['receipt_path'],'install_command':install['receipt_path'],'boot_after':last['receipt_path']})
    return result,sorted(required-set(records)),audit


def build(final_path,roots,boot_id):
    installs,missing,audit=discover(roots,boot_id)
    need(not missing,'actual installation records pending: '+','.join(missing))
    need(final_path is not None and final_path.is_file(),'fresh final collection pending')
    final=read(final_path)
    # Require portable or absolute pins in final.json; collector produces those.
    for reading in [final['boot_before'],final['boot_after'],final['bundles'],*final['apk_reads']]:
        for b in reading.values():need(str(b['path']).startswith(('$WORKSPACES/','/')),'final pins must be portable/absolute')
    req={'schema':'verified-installed-identity-request/v1','serial':SERIAL,'boot_id':boot_id,
         'manifest':pin(MANIFEST),'initial':{'identity':pin(PREFLIGHT/'apk-identity.json'),
         'bundles':original_reading(PREFLIGHT/'bundles.json')},'final':final,'installations':installs}
    need(sha(COMPILER)==COMPILER_SHA,'reviewed compiler drift')
    spec=importlib.util.spec_from_file_location('reviewed_index_compiler',COMPILER)
    compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
    # Validate with the unchanged compiler; temporary products are removed, never presented as final admission.
    with tempfile.TemporaryDirectory(prefix='actual-request-validation-') as tmp:
        p=Path(tmp)/'request.json';save(p,req);compiler.compile_index(p,Path(tmp)/'index')
    return req,audit


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--boot-id',required=True);ap.add_argument('--final',type=Path)
    ap.add_argument('--install-root',action='append',type=Path,default=[])
    ap.add_argument('--out',type=Path);ap.add_argument('--write',action='store_true');a=ap.parse_args()
    roots=[OUTER/'pain-control-completion/install',OUTER/'missing-nine-install',*a.install_root]
    try:
        installs,missing,audit=discover(roots,a.boot_id)
        if not a.write:
            print(json.dumps({'status':'PREVIEW_NO_DEVICE_CALLS','bound_actual_installations':len(installs),
                'pending_installations':missing,'final_supplied':a.final is not None,'audit':audit,
                'initial_bundles_receipt':pin(PREFLIGHT/'bundles.json'),'admission':False},indent=2))
            return 0
        need(a.out is not None and not a.out.exists(),'fresh --out request file required')
        req,audit=build(a.final,roots,a.boot_id)
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('x') as f:f.write(json.dumps(req,indent=2)+'\n')
        print(json.dumps({'status':'REQUEST_ASSEMBLED_AND_COMPILER_VALIDATED','request':pin(a.out),
                         'installations':len(audit),'device_calls':0,'index_published':False}))
        return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'PENDING_OR_REJECTED','error':str(exc),'device_calls':0}));return 2


if __name__=='__main__':raise SystemExit(main())
