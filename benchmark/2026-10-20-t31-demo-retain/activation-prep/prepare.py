#!/usr/bin/env python3
"""Local-only unsigned evidence/template and read-only shell renderer. Never executes shell."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import time
import uuid

HERE = Path(__file__).resolve().parent
T31 = 'benchmark/2026-10-20-t31-demo-retain'
DATA = 'benchmark/2026-10-20-t30-request-recovery/deployment/final-01'
EXE = 'a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
SERIAL = '5cd1e3dd00000000000000000923012c'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def need(v, s):
    if not v: raise ValueError(s)
def ref(p, alias): return {'path': alias, 'sha256': sha(p), 'bytes': Path(p).stat().st_size}
def put(p, v):
    with p.open('x') as f: json.dump(v, f, indent=2, ensure_ascii=False); f.write('\n')

def template(repo):
    expected=read(HERE/'static-pins.json')
    refs=[]
    for rel,h in expected.items():
        need(sha(repo/rel)==h, 'static source drift: '+rel)
        refs.append(ref(repo/rel, '$MAIN/'+rel))
    return dict(status='UNSIGNED_ACTIVATION_TEMPLATE_NOT_A_VERDICT',approved_by=None,
        signed_at=None,signed_at_epoch=None,created_at=None,retained=None,recovery_responsible=None,
        serial=SERIAL,source_production_recovery_reuse_refs=refs,
        current_window=None,current_identity=None,origin=None,origin_backups=None,
        fresh_six_states=None,fresh_five_slots=None,final_feed=None,normal_icon_receipt=None,
        identity_verification=None,power_original_and_restored=None,debug_absence=None,
        before_snapshot=None,before_supplement=None,final_archive=None,
        audio_scope='Reuse current user manual audible-playback confirmation; no per-clip request or fabricated title attribution',
        limits=['Template has no signature or verified fresh identity','Recovery only live parent/WID29; no unconditional rescue','Original replay/t2 unknowns and unsigned fields unchanged'])

def validate(repo,w,now):
    c=read(w/'context.json');plan=w/'apply/plan.json';ad=w/'scoped-admission.json'
    need(Path(c['repo']).resolve()==repo.resolve() and c['serial']==SERIAL,'context repo/serial')
    need(Path(c['deploy']).resolve()==(repo/DATA).resolve(),'context deploy')
    need(0<=now-float(c['start'])<1200,'not current experiment window')
    for rel,h in c['data_pins'].items():
        need('/' not in rel and rel not in ('.','..'),'data pin basename')
        need(sha(repo/DATA/rel)==h,'context data drift')
    spec=importlib.util.spec_from_file_location('t31_policy',repo/T31/'recovery/recovery_policy.py')
    policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
    p,a=policy.validate_origin(repo/DATA,plan,ad)
    need(p['holder']==c['holder'] and p['start']==c['start'],'plan/current context mismatch')
    need(a['t31_context_sha256']==sha(w/'context.json'),'scoped context SHA')
    return c,p

def render(p,boot,parent,pbirth,host,hbirth,mnt):
    q=shlex.quote
    need(str(uuid.UUID(boot))==boot,'boot UUID')
    need(all(type(x) is int and x>1 for x in (parent,pbirth,host,hbirth)) and parent!=host,'explicit fresh identities')
    import re
    need(re.fullmatch(r'mnt:\[[0-9]+\]',mnt) is not None,'explicit parent namespace')
    def identity(tag):
        lines=[f'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(boot)}',f'echo IDENTITY_{tag}']
        for role,pid,birth,uid in [('P',parent,pbirth,0),('H',host,hbirth,20011300)]:
            lines += [f'r=$(cat /proc/{pid}/stat)',f'printf "{role}_STAT_{tag}=%s\\n" "$r"',
              'z=${r##*) }; set -- $z', 'test "$1" != Z; test "$1" != X',f'test "${{20}}" = {birth}']
            if role=='P':lines+=['test "$2" = 1']
            lines += [f'u=$(sed -n "s/^Uid:[[:space:]]*//p" /proc/{pid}/status); set -- $u',
                f'test "$#" = 4; test "$1:$2:$3:$4" = {uid}:{uid}:{uid}:{uid}',
                f'test "$(sed -n "s/^TracerPid:[[:space:]]*//p" /proc/{pid}/status)" = 0',
                f'e=$(sha256sum /proc/{pid}/exe); set -- $e; {role.lower()}e_{tag}=$1',
                f'printf "{role}_EXE_{tag}=%s\\n" "${role.lower()}e_{tag}"']
            if role=='P':lines += [f'test "$1" = {EXE}']
        lines += [f'test "$(readlink /proc/{parent}/ns/mnt)" = {q(mnt)}',
                  f'test "$(readlink /proc/{parent}/ns/mnt)" != "$(readlink /proc/1/ns/mnt)"']
        return lines
    rows=[('run','run.sh',p['after_sha'],p['run_metadata'],p['run_label']),
          ('compat','libopensles_android_compat.so',p['dso_sha'],'644:20011300:20011300',p['dso_label'])]
    for role,path in [('media','lib/arm64-v8a/libmffmpeg.so'),('player',p['player_path']),('bridge',p['bridge_path']),('shim',p['shim_path'])]:
        rows.append((role,path,p[role+'_after_sha'],p[role+'_metadata'],p[role+'_label']))
    lines=['#!/system/bin/sh','set -eu','echo T31_SIX_READ_BEGIN']+identity('before')
    for phase in ['before','after']:
        for role,rel,digest,meta,label in rows:
            for view,path in [('physical',p['runtime']+'/'+rel),('private',f'/proc/{parent}/root/data/local/tmp/asx/'+rel)]:
                name=role+'_'+view+'_'+phase
                lines += [f'test -f {q(path)}; test ! -L {q(path)}',
                  f'x=$(sha256sum {q(path)}); set -- $x; test "$1" = {digest}',
                  f'printf "{name}_sha=%s\\n" "$1"',
                  f'{name}=$(stat -c "%a:%u:%g:%d:%i" {q(path)})',
                  f'printf "{name}_meta=%s\\n" "${name}"',
                  f'test "$(stat -c "%a:%u:%g" {q(path)})" = {q(meta)}',
                  f'l=$(ls -Zd {q(path)}); set -- $l; test "$1" = {q(label)}',
                  f'printf "{name}_label=%s\\n" "$1"']
            lines += [f'test "${role}_physical_{phase}" = "${role}_private_{phase}"']
        lines += [f'c=$(sha256sum /system/etc/init/01_westlake_u13_toutiao.cfg); set -- $c; test "$1" = {p["cfg_sha"]}',f'printf "CFG_{phase}=%s\\n" "$1"']
        if phase=='before':
            lines += ['echo WMS_BEGIN','hidumper -s WindowManagerService -a "-a"','echo WMS_END',
                      'echo POWER_BEGIN','power-shell dump -s','echo POWER_END',
                      'set +e','param get debug.ttplayer.log.enable','prc=$?','set -e','printf "PARAM_RC=%s\\n" "$prc"']
    for role,*_ in rows:
        lines += [f'test "${role}_physical_before" = "${role}_physical_after"',f'test "${role}_private_before" = "${role}_private_after"']
    lines += identity('after')+['test "$he_before" = "$he_after"','echo T31_SIX_READ_COMPLETE']
    return '\n'.join(lines)+'\n'

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=['template','render'])
    ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--window',type=Path);ap.add_argument('--boot');ap.add_argument('--parent-mnt')
    for n in ['parent','parent-birth','host','host-birth']:ap.add_argument('--'+n,type=int)
    a=ap.parse_args(); repo=a.repo.resolve(); result=template(repo);shell=None
    if a.mode=='render':
        need(a.window is not None,'current window required'); w=a.window.resolve();c,p=validate(repo,w,time.time())
        shell=render(p,a.boot,a.parent,a.parent_birth,a.host,a.host_birth,a.parent_mnt)
        result['current_window']=dict(path_alias='$CURRENT_WINDOW',holder=c['holder'],start=c['start'],context_sha256=sha(w/'context.json'))
        result['current_identity']=dict(status='SUPPLIED_NOT_YET_VERIFIED',boot=a.boot,parent=a.parent,parent_birth=a.parent_birth,host=a.host,host_birth=a.host_birth,parent_mnt=a.parent_mnt,child=None,child_birth=None)
        result['origin']={'apply_plan':ref(w/'apply/plan.json','$CURRENT_WINDOW/apply/plan.json'),'scoped_admission':ref(w/'scoped-admission.json','$CURRENT_WINDOW/scoped-admission.json'),'boot':p['boot']}
        result['origin_backups']={'status':'EXPECTED_PATHS_ONLY_NOT_REREAD','five_files':[{'path':p['runtime']+'/'+rel+'.t21-5cd-before-'+p['boot'][:8],'sha256':p[key]} for rel,key in [('run.sh','before_sha'),('lib/arm64-v8a/libmffmpeg.so','media_before_sha'),(p['player_path'],'player_before_sha'),(p['bridge_path'],'bridge_before_sha'),(p['shim_path'],'shim_before_sha')]],'absent_marker':{'path':p['compat_absence_marker'],'sha256':p['compat_absence_marker_sha256']},'actual_backup_receipt':None}
    a.out.mkdir(parents=True,exist_ok=False)
    put(a.out/'unsigned-retain-evidence.json',result)
    if shell is not None:
        (a.out/'candidate-six-read.sh').write_text(shell)
        put(a.out/'render.json',{'device_calls':0,'shell_sha256':sha(a.out/'candidate-six-read.sh'),'unsigned_sha256':sha(a.out/'unsigned-retain-evidence.json'),'producer_sha256':sha(__file__),'execute':False,'limits':'Root held/time wrapper required; WMS29/power/param text require review, not inferred from marker.'})
    print(json.dumps({'device_calls':0,'signed':False,'output_files':[x.name for x in a.out.iterdir()]}))
if __name__=='__main__':main()
