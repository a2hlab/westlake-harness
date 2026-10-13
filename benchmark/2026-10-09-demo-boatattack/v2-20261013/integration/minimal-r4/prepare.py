"""Local-only derivation of the eleven-member/seven-bind r4 package; needs real captures."""
import argparse,copy,json,os,re
from pathlib import Path
import installer as i
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[5])));MAIN=WS/'westlake-harness'
OLD='/data/westlake-demo/u13/boat-v2-20261013';ROOT=i.ROOT;RUNTIME='/system/android/lib64/liboh_android_runtime.so'
STOCK='18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae'
LIBANDROID='/system/android/lib64/libandroid.so'
ANDROID_BASE='9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db'
ADC='adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130'
PORT='94718e0d0b617a0f9a860e0b50b879b0d7d4639f32e8230b1f90f8e26e2c1354'
def pin(path):
 resolved=Path(path).resolve();workspace=WS.resolve()
 if resolved.is_relative_to(workspace):portable='$WORKSPACES/'+str(resolved.relative_to(workspace))
 elif resolved.is_relative_to(workspace.parent):portable='$WORKSPACES/../'+str(resolved.relative_to(workspace.parent))
 else:portable=str(resolved)
 return {'path':portable,'sha256':i.sha(path)}
def pinned(ref):
 p=i.resolve(ref['path']);i.need(i.sha(p)==ref['sha256'],'capture/source pin drift');return p

def android_source():
 report_path=HERE.parent/'historical-recipe-diff.json';report=i.read(report_path)
 i.need(i.sha(report_path)=='af00aa5b58ab1302502b5a5bbf6b366281f192ee42651f3152344eeb14aaa14c','historical byte replay evidence pin')
 r=report['independent_byte_replay'];base=pinned(r['baseline']);source=pinned(r['candidate']);patch=i.read(pinned(r['patch_table']))
 i.need(i.sha(base)==ANDROID_BASE and i.sha(source)==ADC,'libandroid source pair drift')
 data=bytearray(base.read_bytes());i.need(len(patch['changes'])==49,'exact49 patch records required')
 for change in patch['changes']:
  n=int(change['file_offset'],16);i.need(data[n]==change['before'],'libandroid patch before drift');data[n]=change['after']
 i.need(bytes(data)==source.read_bytes(),'full libandroid byte replay drift')
 return source,report_path

def build(captured_path,out):
 i.need(not out.exists(),'fresh output directory required');captured=i.read(captured_path)
 i.need(captured['serial']=='5ea34a4500000000000000001123012c','5ea only')
 i.need(re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',captured['boot_id']),'captured boot required')
 for ref in captured['evidence'].values():pinned(ref)
 i.need(captured['absence']['target']==ROOT and captured['absence']['exists'] is False,'actual r4 directory absence required')
 rt=captured['runtime_before'];i.need(rt['target']==RUNTIME and rt['exists'] is True and rt['sha256']==STOCK,'runtime stock preimage required')
 i.need(captured['baseline319_equal'] is True and captured['original_cfg_restored'] is True,'outer restored baseline evidence required')
 # Reuse root window1 sources/CAS and exact existing executor; no active r2 state is assumed.
 window=MAIN/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/candidate-window1'
 original=window/'plan.json';i.need(i.sha(original)=='368b02a17cb0c85a6e1b1bd8563e9bc05721ec03f657080552893bec3128cac4','original placement pin')
 plan=copy.deepcopy(i.read(original));plan['execution_enabled']=False;plan['boot_id']=captured['boot_id'];plan['serial']=captured['serial'];core=i.core_for(plan);core.metadata(rt,'runtime preimage')
 linkref=captured['runtime_closure'];link=i.read(pinned(linkref));build=link['fresh_build'];i.need(build['status']=='pass','runtime build closure not pass')
 source=pinned(build['candidate']);i.need(i.sha(source)==PORT,'947 artifact pin')
 i.need(build['baseline']['sha256']==STOCK and build['elf_checks']['exports_after']==787 and build['elf_checks']['new_undefined']==[],'runtime baseline/ABI closure')
 absence={'exists':False,'proof':captured['evidence']['r4_absence']}
 for row in plan['members']:
  row['target']=row['target'].replace(OLD,ROOT)
  if row['before']['exists'] is False:row['before']=copy.deepcopy(absence)
  else:row['before']['source']=str(window/'checkpoint-01/current-recover.cfg').replace(str(WS),'$WORKSPACES')
 for row in plan['directories']:row['target']=row['target'].replace(OLD,ROOT);row['before']=copy.deepcopy(absence)
 for row in plan['binds']:row['source']=row['source'].replace(OLD,ROOT)
 meta={k:rt[k] for k in ['mode','uid','gid','label']};before={k:rt[k] for k in ['exists','sha256','mode','uid','gid','label']}
 runtime_member={'target':ROOT+'/sources/liboh_android_runtime.so','source':pin(source)['path'],'sha256':PORT,'before':copy.deepcopy(absence),'after':meta}
 plan['members'].insert(5,runtime_member)
 plan['binds'].append({'target':RUNTIME,'source':runtime_member['target'],'sha256':PORT,'before':before,'after':meta})
 plan['preserved'].append({'target':RUNTIME,'before':before})
 ar=captured['libandroid_before'];i.need(ar['target']==LIBANDROID and ar['exists'] is True and ar['sha256']==ANDROID_BASE,'libandroid9cc actual preimage required');core.metadata(ar,'libandroid preimage')
 adc_source,report_path=android_source();android_meta={k:ar[k] for k in ['mode','uid','gid','label']};android_before={k:ar[k] for k in ['exists','sha256','mode','uid','gid','label']}
 android_member={'target':ROOT+'/sources/libandroid.so','source':pin(adc_source)['path'],'sha256':ADC,'before':copy.deepcopy(absence),'after':android_meta}
 plan['members'].insert(6,android_member);plan['binds'].append({'target':LIBANDROID,'source':android_member['target'],'sha256':ADC,'before':android_before,'after':android_meta});plan['preserved'].append({'target':LIBANDROID,'before':android_before})
 out.mkdir(parents=True)
 for name in ['installer.py','recover.cfg','recover-v3-boat.sh']:(out/name).write_bytes((HERE/name).read_bytes())
 rows=[]
 for row in plan['binds']:
  b=row['before'];a=row['after'];rows.append('\t'.join([Path(row['source']).name,row['target'],b['sha256'],row['sha256'],':'.join(str(b[k]) for k in ['mode','uid','gid','label']),':'.join(str(a[k]) for k in ['mode','uid','gid','label'])]))
 (out/'binds.tsv').write_text('\n'.join(rows)+'\n');(out/'worker.sh').write_text((HERE/'worker.template.sh').read_text().replace('__TABLE_SHA256__',i.sha(out/'binds.tsv')))
 for row in plan['members']:
  if row['target']==i.CFG:name='recover.cfg'
  elif row['target'] in [ROOT+'/'+n for n in ['binds.tsv','worker.sh','recover-v3-boat.sh']]:name=Path(row['target']).name
  else:continue
  row['source']='$PACKAGE/'+name;row['sha256']=i.sha(out/name)
 plan['installer_sha256']=i.sha(out/'installer.py');plan['schema']='boat-seven-bind-place/v1';plan['evidence']={'captured':pin(captured_path),'root_window1_plan':pin(original),'runtime_closure':linkref,'historical_libandroid_replay':pin(report_path),'adc_closure':pin(HERE/'adc-closure.json'),**captured['evidence']}
 plan['notes']=['Fresh r4 directory; original six binds then libandroid ADC; reverse rollback','Source body derived from reviewed minimal+r2; no board calls by compiler','All runtime source/target metadata copied from same-boot real captured preimage; no guessed metadata; ADC never placed at runtime path','Not sealed; approved historical exact artifact reuse; original ADC source/build reproducibility is unclosed, remote0d7b log is not ADC evidence; new49-byte replay is not a source build','Outer admission/cold boot/UI proof still required']
 (out/'plan.disabled.json').write_text(json.dumps(plan,indent=2)+'\n')
 return plan
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--captured',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();plan=build(a.captured,a.out);print(json.dumps({'status':'PREPARED_DISABLED','members':len(plan['members']),'binds':len(plan['binds']),'plan_sha256':i.sha(a.out/'plan.disabled.json'),'device_calls':0}))
