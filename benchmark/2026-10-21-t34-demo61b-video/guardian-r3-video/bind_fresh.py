#!/usr/bin/env python3
"""Consume actual cc-video receipts locally; produce an unsigned, provenance-bound package."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

D=Path(__file__).resolve().parent
sys.path.insert(0,str(D/'deployment'))
import prepare_data as pd
import render_supplement as rs
sha=lambda b:hashlib.sha256(b).hexdigest()

def stat(line):
    m=re.fullmatch(r'(\d+) \((.*)\) (.*)',line)
    assert m,'malformed proc stat'
    fields=m[3].split()
    return {'pid':int(m[1]),'state':fields[0],'ppid':int(fields[1]),'birth':int(fields[19])}

def assemble(intake,supplement):
    refs={};fields={}
    def source(path):
        folder='intake-01' if path.parent==intake or path.parent==intake/'before-image' else 'supplement-01'
        rel=path.relative_to(intake if folder=='intake-01' else supplement).as_posix()
        alias='$T34_PRIVATE/'+folder+'/'+rel
        b=path.read_bytes();refs[alias]={'path':alias,'sha256':sha(b),'bytes':len(b)}
        return b.decode(),alias
    def receipt(folder,stem):
        rc=int((folder/(stem+'.rc')).read_text());assert rc==0,(stem,rc)
        source(folder/(stem+'.rc'))
        return source(folder/(stem+'.stdout'))
    def bind(key,value,*aliases):
        fields[key]=[dict(refs[x]) for x in aliases]
        return value
    text,sup=receipt(supplement,'run')
    script,scriptref=source(supplement/'supplement.sh')
    argv,argvref=source(supplement/'run.argv.json')
    av=json.loads(argv);assert av[1:4]==['-t',pd.SERIAL,'shell']
    assert av[4]==script or av[4]+'\n'==script,'only final LF may differ in shell argv'
    lines=text.splitlines()
    after=lambda marker:lines[lines.index(marker)+1]
    boot=re.findall(r'^T34_BOOT_BEFORE=(.*)$',text,re.M);end=re.findall(r'^T34_BOOT_AFTER=(.*)$',text,re.M)
    assert len(boot)==len(end)==1 and boot==end
    parent=stat(after('P_STAT_BEFORE'));host=stat(after('H_STAT_BEFORE'))
    for prefix,obj in [('P',parent),('H',host)]:
        assert stat(after(prefix+'_STAT_AFTER'))==obj,'identity drift'
    assert script==rs.render(boot[0],parent['pid'],parent['birth'],host['pid'],host['birth'])
    # Completion of this exact set-eu script proves both UID/Tracer guards ran.
    parent.update(uid=0,tracer=0);host.update(uid=20011206,tracer=0)
    for role,obj in [('parent',parent),('host',host)]:
        ex,eref=receipt(intake,f"10-{role}-{obj['pid']}-exe")
        hashes=re.findall(r'^([0-9a-f]{64})  /proc/\d+/exe$',ex,re.M);assert len(hashes)==1
        obj['exe_sha256']=hashes[0];fields[role]=[refs[sup],refs[scriptref],refs[argvref],refs[eref]]
    rawrun= intake/'before-image/run.sh';run=rawrun.read_bytes()
    _,runref=source(rawrun);receipt(intake,'19-recv-run')
    _,wid=pd.run_wid(run,33)
    wm,wmref=receipt(intake,'05-wms')
    rows=[l.split() for l in wm.splitlines() if l.split() and l.split()[0]=='imehost0']
    assert len(rows)==1 and int(rows[0][2])==host['pid'] and int(rows[0][3])==wid
    bundle,bref=receipt(intake,'07-bm-dump-host')
    bundle=json.loads(bundle[bundle.index('{'):])
    power,pref=receipt(intake,'06-power')
    pm=re.search(r'ScreenOffTime: Timeout=(\d+)ms  OverrideTimeout=(\d+)ms',power);assert pm
    runtime,rref=receipt(intake,'15-runtime-before')
    hashes={path:digest for digest,path in re.findall(r'^([0-9a-f]{64})  (\S+)$',runtime,re.M)}
    assert hashes[pd.RT+'/run.sh']==sha(run)
    controls,cref=receipt(intake,'17-guardian18-sha')
    controls={p:h for h,p in re.findall(r'^([0-9a-f]{64})  (\S+)$',controls,re.M)}
    hap,href=receipt(intake,'08-hap-sha-stat')
    hapsha=re.findall(r'^([0-9a-f]{64})  /data/app/el1/bundle/public/org.westlake.imehost/entry.hap$',hap,re.M)
    assert len(hapsha)==1
    absent,aref=receipt(intake,'16-compat-absence')
    expected=pd.RT+'/libopensles_android_compat.so'
    assert f'ls: {expected}: No such file or directory' in absent
    dirs={};protected={};private={}
    for i,line in enumerate(lines):
        if line.startswith('DIRECTORY='):
            path=line.split('=',1)[1];value=lines[i+1]
            if value!='ABSENT':
                assert re.fullmatch(r'\d+:\d+',value) and lines[i+2]==path,'directory alias/canonical path'
            (dirs if path==pd.RT or path.startswith(pd.RT+'/') else protected)[path]=None if value=='ABSENT' else value
        if line.startswith('PRIVATE='):
            rel=line.split('=',1)[1]
            assert lines[i+1]==lines[i+2] and re.fullmatch(r'\d+:\d+',lines[i+1])
            digest=lines[i+3].split()[0];assert hashes[pd.RT+'/'+rel]==digest
            private[rel]={'dev_inode':lines[i+1],'sha256':digest}
    assert len(private)==5
    shas={p:h for h,p in re.findall(r'^([0-9a-f]{64})  (\S+)$',text,re.M)}
    err=re.fullmatch(r'Get parameter "debug.ttplayer.log.enable" fail! errNum is:(\d+)!',after('DEBUG_GET_BEGIN'))
    assert err and int(err[1])==106
    process_rc=int(re.findall(r'^DEBUG_GET_RC=(\d+)$',text,re.M)[0]);assert process_rc==0
    f={
      'serial':bind('serial',pd.SERIAL,argvref),
      'uid':bind('uid',bundle['uid'],bref),
      'runtime':bind('runtime',pd.RT,rref),
      'boot_before':bind('boot_before',boot[0],sup),
      'boot_after':bind('boot_after',end[0],sup),
      'cfg_sha256':bind('cfg_sha256',hashes['/system/etc/init/01_westlake_u13_toutiao.cfg'],rref),
      'hap_sha256':bind('hap_sha256',hapsha[0],href),
      'compat_absent':bind('compat_absent',True,aref),
      'power':bind('power',{'timeout':int(pm[1]),'override':int(pm[2])},pref),
      # Legacy field name required by frozen prepare_data.py, NOT the process exit code.
      'debug_get_rc':bind('debug_get_rc',int(err[1]),sup),
      'debug_get_process_rc':bind('debug_get_process_rc',process_rc,sup),
      'debug_get_rc_semantics':'param body errNum; legacy field name, not subprocess rc',
      'shell_argv_final_lf_omitted':bind('shell_argv_final_lf_omitted',av[4]!=script,argvref,scriptref),
      'debug_get_raw_line':bind('debug_get_raw_line',after('DEBUG_GET_BEGIN'),sup),
      'run_sha256':bind('run_sha256',sha(run),runref,rref,sup),
      'wid':bind('wid',wid,runref,wmref),
      'parent_wid':bind('parent_wid',int(after('P_WID')),sup),
      'controls':bind('controls',controls,cref),
      'access_token_id':bind('access_token_id',bundle['applicationInfo']['accessTokenId'],bref),
      'runtime_sha256':bind('runtime_sha256',hashes,rref),
      'directory_identities':bind('directory_identities',dirs,sup),
      'protected_directories':bind('protected_directories',protected,sup),
      'providers':bind('providers',[{'path':p,'sha256':shas[p]} for p in ('/system/lib64/libOpenSLES.so',pd.RT+'/liblog.so')],sup),
      'network_sha256':bind('network_sha256',shas[pd.RT+'/libandroid_native_network_compat.so'],sup),
      'parent':parent,'host':host,
      'parent_mnt':bind('parent_mnt',after('P_MNT'),sup),
      'physical_private_files_equal':bind('physical_private_files_equal',True,sup,rref),
      'physical_private_files':bind('physical_private_files',private,sup,rref),
    }
    # Each nested leaf inherits the exact source receipt, not an inferred source.
    def leaves(value,prefix):
        if isinstance(value,dict):
            for k,v in value.items():yield from leaves(v,prefix+'/'+k.replace('~','~0').replace('/','~1'))
        elif isinstance(value,list):
            for i,v in enumerate(value):yield from leaves(v,prefix+'/'+str(i))
        else:yield prefix
    f['field_sources']={leaf:fields[k] for k,v in f.items() if k in fields for leaf in leaves(v,'/'+k)}
    f['evidence']=list(refs.values())
    return f,run

def main():
    p=argparse.ArgumentParser()
    for key in ('intake','supplement','repo','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();f,run=assemble(a.intake,a.supplement)
    params=pd.prepare(f,run,a.repo,a.out)
    print(json.dumps({'status':params['status'],'data':str(a.out),'fresh_sha256':sha((a.out/'fresh.json').read_bytes()),
                      'field_source_count':len(f['field_sources']),'debug_semantic_errNum':f['debug_get_rc'],
                      'debug_process_rc':f['debug_get_process_rc'],'device_calls':0,'approved_by':None},indent=2))
if __name__=='__main__':main()
