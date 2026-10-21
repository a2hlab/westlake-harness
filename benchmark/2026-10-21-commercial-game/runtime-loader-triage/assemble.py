#!/usr/bin/env python3
"""Explicit-write offline evidence assembly; source snapshots are immutable inputs."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent
REPO=D.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true',required=True);ap.add_argument('--main',type=Path,required=True);ap.add_argument('--bms-source',type=Path,required=True);ap.add_argument('--private',type=Path,required=True);a=ap.parse_args()
 idx=[]
 def snap(root,rel,lines,label='MAIN'):
  src=root/rel;dst=D/'sources'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
  idx.append({'origin_alias':label,'origin':rel,'snapshot':str(dst.relative_to(D)),'sha256':sha(src),'bytes':src.stat().st_size,'lines':lines})
 sources=[('bms/src/adapter/framework/app-native-loader/src/app_native_loader.c',[[62,77],[338,425],[432,482]]),('bms/src/adapter/framework/native-loader-oh/src/native_loader.cpp',[[66,124]]),('bms/src/adapter/framework/native-loader-oh/include/nativeloader/native_bridge_policy.h',[[17,28],[44,53]]),('bms/src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/src/westlake_stock_host_main.c',[[139,330]]),('bms/src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/src/resident-compat.h',[[7,45]]),('benchmark/2026-10-03-u13-first-fatal-clusters/evidence/provider-exports.txt',[[1,30]]),('benchmark/2026-10-21-commercial-game/normal-ui-01/exit-log-excerpt.txt',[]),('benchmark/2026-10-21-commercial-game/normal-ui-01/log-provenance.json',[]),('benchmark/2026-10-21-commercial-game/reuse/reuse-matrix.json',[]),('benchmark/2026-10-21-commercial-game/exact-static/rea-method-findings.json',[]),('benchmark/2026-10-21-commercial-game/exact-static/rea-ledger.json',[])]
 for rel,lines in sources:snap(a.main,rel,lines)
 for rel,lines in [('benchmark/2026-09-30-n3-native/src/native_abi.c',[[43,46]])]:snap(a.bms_source,rel,lines,'BMS_DEPLOY_SOURCE')
 put(D/'evidence-index.json',idx)
 raw=a.private/'runtime-loader-readonly-01';analysis=json.loads((D/'.private/exact-01/analysis.json').read_text());put(D/'evidence/exact-elf.json',analysis)
 # Public excerpts retain original line numbers; full raw remains private.
 orig=a.private/'normal-ui-01/child-hilog.stdout';assert sha(orig)=='8a82fca6c80d4baa42e3c26ac0bfe01dbdd5d73ddd6ba8c0a5962d3e0fa8aa4f'; lines=orig.read_text().splitlines()
 selected=[(258,258),(2756,2756),(2902,2902),(3041,3041)]
 (D/'evidence/namespace-log-excerpt.txt').write_text(''.join(f'{i}: {lines[i-1]}\n' for lo,hi in selected for i in range(lo,hi+1)))
 put(D/'evidence/namespace-log-provenance.json',{'original_alias':'$COMMERCIAL_PRIVATE/normal-ui-01/child-hilog.stdout','sha256':sha(orig),'bytes':orig.stat().st_size,'ranges':selected})
 findings=json.loads((a.main/'benchmark/2026-10-21-commercial-game/exact-static/rea-method-findings.json').read_text());checks=[]
 for i,r in enumerate(findings['records']):
  f=a.private/f'exact-static/outer-rea/method-{i}.tool-result.json';assert sha(f)==r['raw']['sha256'] and f.stat().st_size==r['raw']['bytes'];checks.append({'method':r['method'],'raw':r['raw'],'evidence_id':r['evidence_id'],'source_sha256':r['source_sha256'],'anchors':r['anchors'],'finding':r['finding'],'verified':True,'executed_by':'outer(codex)','reanalyzed_by':'inner(codex)'})
 put(D/'rea-reuse.json',{'existing_methods':checks,'new_rea':'NOT_EXECUTED','reason':'Existing exact APK methods plus local LLVM analysis resolve this static slice; child provider identity remains unavailable, not a decompilation gap.'})
 inv=json.loads((a.main/'benchmark/2026-10-21-commercial-game/exact-static/elf-inventory.json').read_text());cons=[]
 for lib in inv['libraries']:
  if Path(lib['member']).name in ['libyuanshen.so','libMHYComboCrypto.so']:
   cons.append({k:lib[k] for k in ['member','sha256','bytes','needed']}|{'focused_imports':[s for s in lib['imports'] if s.startswith(('__errno','egl','gl'))]})
 put(D/'evidence/exact-consumers.json',{'source_sha256':sha(a.main/'benchmark/2026-10-21-commercial-game/exact-static/elf-inventory.json'),'apk_sha256':inv['apk_sha256'],'libraries':cons})
 gp=raw/'graphics-peer-01/results.json';assert sha(gp)=='e653072bd2c2656189639ea4f2ac0d7d0d7503235cef7d2a7fbdae89dedd8da5'
 # Keep peer as indexed external evidence; it may contain personal paths.
 put(D/'evidence/graphics-peer-reference.json',{'alias':'$COMMERCIAL_PRIVATE/runtime-loader-readonly-01/graphics-peer-01/results.json','sha256':sha(gp),'bytes':gp.stat().st_size,'facts':{'stock_GLESv3_gl_exports':887,'NDK23_GLES2_core_coverage':'142/142','stock_EGL_egl_exports':79,'yuanshen_direct_EGL_import_coverage':'18/18','yuanshen_direct_GL_imports':0},'limits':['GLESv3 SONAME differs from needed GLESv2','dynamic extensions, native window/display/context ABI unproven','provider exports are not app namespace binding']})
 pubraw=[]
 for p in sorted(raw.glob('*.json')):
  if p.name=='route-receipts.json' or p.name.startswith(('obj','parent-','boot-')):
   text=p.read_text().replace(str(Path.home()),'$HOME');dst=D/'evidence/outer-read-receipts'/p.name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(text);pubraw.append({'alias':'$COMMERCIAL_PRIVATE/runtime-loader-readonly-01/'+p.name,'sha256':sha(p),'bytes':p.stat().st_size,'public':str(dst.relative_to(D)),'public_sha256':sha(dst)})
 for stem in ['obj5-before','obj5-recv','obj5-after','parent-stat-before','parent-stat-after','boot-before','boot-after']:
  p=raw/(stem+'.stdout');dst=D/'evidence/outer-read-receipts'/(stem+'.stdout.txt');dst.write_bytes(p.read_bytes());pubraw.append({'alias':'$COMMERCIAL_PRIVATE/runtime-loader-readonly-01/'+p.name,'sha256':sha(p),'bytes':p.stat().st_size,'public':str(dst.relative_to(D)),'public_sha256':sha(dst)})
 put(D/'evidence/outer-read-index.json',pubraw)
 # Actual local tool double streams, sanitized only in public copies.
 ri=[]
 for p in sorted((D/'.private/exact-01/raw').iterdir()):
  rel='evidence/llvm/'+p.name+('.txt' if p.suffix in ['.stdout','.stderr'] else '')
  dst=D/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(p.read_text().replace(str(Path.home()),'$HOME'))
  ri.append({'private_alias':'$G16_PRIVATE/exact-01/raw/'+p.name,'sha256':sha(p),'bytes':p.stat().st_size,'public':rel,'public_sha256':sha(dst)})
 put(D/'evidence/llvm-index.json',ri)
 print(json.dumps({'sources':len(idx),'rea_methods':len(checks),'system_elfs':len(analysis['system']),'route_elfs':len(analysis['routes'])}))
if __name__=='__main__':main()
