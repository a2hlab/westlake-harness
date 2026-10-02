#!/usr/bin/env python3
"""Exercise production tools and gates without importing Board or invoking HDC."""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=R.parent
sys.path.insert(0,str(R/'scripts/lab'))
import generation_bundle as gb, generation_static_checks as static, native_predeploy, u7_executor as u, check_frozen as f

def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--surface',choices=['mac','vm'],required=True);a=p.parse_args()
 out=H/'gates'/a.surface;out.mkdir(parents=True,exist_ok=True)
 c=json.loads((H/'composition.json').read_text());package=Path(c['package'].replace('$WORKSPACES',str(W)));base=Path(c['base_bundle'].replace('$WORKSPACES',str(W)))
 tools={name:shutil.which(name) for name in ['dexdump','llvm-readelf','llvm-nm','llvm-objdump','readelf']}
 assert all(tools.values()),tools
 with tempfile.TemporaryDirectory() as td:
  jar=gb.member(package,json.loads((package/'bundle.json').read_text())['runtime_jar'])
  with zipfile.ZipFile(jar) as z: dex=Path(td)/'classes.dex';dex.write_bytes(z.read('classes.dex'))
  subprocess.run(['dexdump','-f',str(dex)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=25)
 for tool in list(tools)[1:]:subprocess.run([tool,'--version'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=15)
 save(out/'tools.json',{'status':'PASS','tools':tools,'shared_dex_read':'PASS','package_sha256':gb.sha(package/'bundle.json'),'device_access':False})
 n=package/'native';report=native_predeploy.check_package(n,n/'native-checks/native-gates.json',exceptions=R/'knowledge/gates/native-predeploy-exceptions.json',readelf='llvm-readelf');save(out/'native-gate.json',report)
 data=json.loads((package/'bundle.json').read_text());policy=json.loads(gb.member(package,data['static_checks']['policy']).read_text());s=static.check(package,base,policy);save(out/'static-checks.json',s)
 rb=subprocess.run([sys.executable,str(R/'knowledge/toolchains/art-r155/check_boot_oat_rb.py'),str(package/'boot/arm64/boot.oat'),'--image',str(package/'boot/arm64/boot.art')],text=True,capture_output=True);(out/'rb.txt').write_text(rb.stdout+rb.stderr)
 t4b=subprocess.run([sys.executable,str(R/'knowledge/toolchains/art-r155/t4b_build_switch_gate.py'),'--libart',str(n/'payload/route/libart.so'),'--oat',str(package/'boot/arm64/boot.oat'),'--build',str(R/'benchmark/2026-10-02-u12-jar-r2-bake/evidence/U12-BUILD-snapshot.md'),'--out',str(out/'t4b.json')],text=True,capture_output=True);(out/'t4b.txt').write_text(t4b.stdout+t4b.stderr)
 images=gb.image_checks(package,str(W/'westlake-harness/scripts/lab/oatdump_remote.sh'));save(out/'image-gates.json',images)
 frozen=subprocess.run([sys.executable,str(R/'scripts/lab/check_frozen.py'),'--package',str(n)],text=True,capture_output=True);(out/'frozen.txt').write_text(frozen.stdout+frozen.stderr)
 command=[sys.executable,str(R/'scripts/lab/u7_executor.py'),'--dry-run','--package',str(package),'--baseline-native',str(base/'native'),'--oatdump',str(W/'westlake-harness/scripts/lab/oatdump_remote.sh'),'--out',str(out/'executor')]
 proc=subprocess.run(command,text=True,capture_output=True);(out/'production-dry-run.txt').write_text(proc.stdout+proc.stderr)
 composed={}
 for serial,row in c['candidate_boards'].items():
  lines,bad=f.check_artifacts(f.active(f.load(R/'knowledge/frozen/frozen.json')),row['expected'],'U12 final '+serial[:8]);composed[serial]={'lines':lines,'violations':bad}
 save(out/'frozen-composed.json',composed)
 summary={'surface':a.surface,'bundle_sha256':c['bundle_sha256'],'native_manifest_sha256':c['native_manifest_sha256'],'tools':'PASS','native_gate':report['status'],'native_findings':{g:{k:v[k] for k in ['rejected','excepted']} for g,v in report['gates'].items()},'native_errors':report['errors'],'static':s['status'],'static_members':[{k:r.get(k) for k in ['target','status','reason','delta_sha256']} for r in s['members']],'RB_exit_code':rb.returncode,'T4b_exit_code':t4b.returncode,'G1':images['G1'],'G2':images['G2'],'frozen_composed_violations':sum(row['violations'] for row in composed.values()),'frozen_exit_code':frozen.returncode,'production_dry_run_exit_code':proc.returncode,'rollout_ready':False,'device_access':False}
 save(out/'summary.json',summary);print(json.dumps(summary,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
