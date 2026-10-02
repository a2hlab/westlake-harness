#!/usr/bin/env python3
"""Actual final U12-draft static gate, with isolated test tables; production table stays empty."""
import argparse,hashlib,json,shutil,subprocess,sys,tempfile,zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent;R=H.parents[1];W=R.parent
sys.path.insert(0,str(R/'scripts/lab'));import generation_static_checks as gate,generation_bundle as bundle
TARGET='/system/android/lib64/libmediandk.so';MEDIA='8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58'
EVIDENCE=['benchmark/2026-10-02-u12-mediandk/validation.json','benchmark/2026-10-02-u12-mediandk/evidence/abi-mediandk.json','benchmark/2026-10-02-u12-mediandk/evidence/candidate-dynamic.txt','benchmark/2026-10-02-u12-mediandk/strings-review.json','benchmark/2026-10-02-u12-mediandk/namespace-gates.json']
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--surface',choices=['mac','vm'],required=True);a=p.parse_args();out=H/'gates'/a.surface;out.mkdir(parents=True,exist_ok=True)
 c=json.loads((R/'benchmark/2026-10-02-u12-assembly/composition.json').read_text());root=Path(c['package'].replace('$WORKSPACES',str(W)));base=Path(c['base_bundle'].replace('$WORKSPACES',str(W)));assert bundle.sha(root/'native/payload/android/lib64/libmediandk.so')==MEDIA
 table_before=bundle.sha(gate.NEW_NATIVE_ADMISSIONS);assert json.loads(gate.NEW_NATIVE_ADMISSIONS.read_text())['admissions']==[]
 tools={n:shutil.which(n) for n in ['dexdump','llvm-readelf','llvm-nm','llvm-objdump']};assert all(tools.values()),tools
 for name in list(tools)[1:]:subprocess.run([name,'--version'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=15)
 with tempfile.TemporaryDirectory() as td:
  dex=Path(td)/'probe.dex';d=json.loads((root/'bundle.json').read_text())
  with zipfile.ZipFile(bundle.member(root,d['runtime_jar'])) as z:dex.write_bytes(z.read('classes.dex'))
  subprocess.run(['dexdump','-f',str(dex)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=25)
 unit=subprocess.run([sys.executable,str(H/'test_admissions.py'),'-v'],capture_output=True,text=True);(out/'tests.txt').write_text(unit.stdout+unit.stderr);assert unit.returncode==0
 command=[sys.executable,str(R/'scripts/lab/generation_static_checks.py'),'--package',str(root),'--baseline',str(base),'--out',str(out/'default-static.json')]
 proc=subprocess.run(command,capture_output=True,text=True);(out/'default-static.txt').write_text(proc.stdout+proc.stderr);assert proc.returncode==2
 row={'target':TARGET,'sha256':MEDIA,'package_manifest_sha256':c['native_manifest_sha256'],'reason':'Isolated known-answer fixture only; no outer admission or production registration.','evidence':EVIDENCE,'added':datetime.now().astimezone().isoformat(timespec='seconds')}
 cases={}
 with tempfile.TemporaryDirectory(prefix='new-native-admission-fixture-') as td:
  table=Path(td)/'admissions.json'
  for case,rows in [('exact',[row]),('different_sha',[dict(row,sha256='0'*64)]),('different_manifest',[dict(row,package_manifest_sha256='1'*64)]),('different_path',[dict(row,target='/system/android/lib64/libunreviewed.so')]),('empty',[])]:
   save(table,{'schema':'westlake-new-native-admissions/v1','admissions':rows})
   with patch.object(gate,'NEW_NATIVE_ADMISSIONS',table):report=gate.check(root,base,{})
   save(out/(case+'-static.json'),report);cases[case]=report['status'];assert report['status']==('PASS' if case=='exact' else 'REJECT')
  table.unlink()
  with patch.object(gate,'NEW_NATIVE_ADMISSIONS',table):report=gate.check(root,base,{})
  save(out/'missing-static.json',report);cases['missing']=report['status'];assert report['status']=='REJECT'
 assert table_before==bundle.sha(gate.NEW_NATIVE_ADMISSIONS)
 summary={'surface':a.surface,'device_access':False,'production_registry_unchanged':True,'production_registry_rows':0,'tools':tools,'real_dex_read':'PASS','unit_tests':8,'unit_exit_code':unit.returncode,'default_static_exit_code':proc.returncode,'fixture_cases':cases,'native_manifest_sha256':c['native_manifest_sha256'],'artifact_sha256':MEDIA,'bundle_sha256':c['bundle_sha256'],'note':'PASS uses isolated temporary test admission, never a production approval.'};save(out/'summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
