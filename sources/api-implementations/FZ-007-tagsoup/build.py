#!/usr/bin/env python3
"""Build the frozen TagSoup component or the exact T7d source composition offline."""
import argparse, hashlib, json, os, shutil, subprocess, zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--mode',choices=['component','t7d'],default='component');ap.add_argument('--out',type=Path,required=True);ap.add_argument('--dependencies',type=Path,help='Root containing locked out/ and android-source/r8 inputs');a=ap.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 java_home=os.environ.get('JAVA_HOME');javac=str(Path(java_home)/'bin/javac') if java_home else shutil.which('javac');java=str(Path(java_home)/'bin/java') if java_home else shutil.which('java');assert javac and java
 receipt={'mode':a.mode,'kind':'new_rebuild_not_historical_receipt','steps':[],'source_checks':[],'dependency_checks':[]}
 def save(): (out/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 def portable(x):
  s=str(x).replace(str(out),'$OUT').replace(str(REPO),'$REPO')
  if a.dependencies:s=s.replace(str(a.dependencies.resolve()),'$A2HLAB_WS')
  return s
 def run(label,args):
  with (out/(label+'.stdout.txt')).open('wb') as so,(out/(label+'.stderr.txt')).open('wb') as se:p=subprocess.run(list(map(str,args)),stdout=so,stderr=se)
  receipt['steps'].append({'name':label,'argv':[portable(v) for v in args],'rc':p.returncode,'stdout_sha256':sha(out/(label+'.stdout.txt')),'stderr_sha256':sha(out/(label+'.stderr.txt'))});save()
  if p.returncode:raise SystemExit(p.returncode)
 for exe,label in [(javac,'javac-version'),(java,'java-version')]:run(label,[exe,'-version'])
 expected={name:digest for digest,name in [line.split() for line in (HERE/'FROZEN-SHA256SUMS.txt').read_text().splitlines()]}
 frozen=sorted((HERE/'src/org/ccil/cowan/tagsoup').glob('*.java'));assert len(frozen)==15 and {p.name for p in frozen}==set(expected)
 for p in frozen:assert sha(p)==expected[p.name],p.name
 if a.mode=='component':sources=frozen;cp=[]
 else:
  assert a.dependencies,'--dependencies is required for t7d'
  lock=read(HERE/'dependencies.lock.json');deps=a.dependencies.resolve();cp=[]
  for d in lock['t7d_classpath']+[lock['r8']]:
   p=deps/d['path'].removeprefix('$A2HLAB_WS/');assert p.is_file() and sha(p)==d['sha256'],d['path'];receipt['dependency_checks'].append(d)
  cp=[deps/d['path'].removeprefix('$A2HLAB_WS/') for d in lock['t7d_classpath']];r8=deps/lock['r8']['path'].removeprefix('$A2HLAB_WS/')
  sources=[]
  for d in read(HERE/'t7d-sources.lock.json')['sources']:
   p=REPO/d['repo_path'];assert p.is_file() and sha(p)==d['sha256'],d['repo_path'];sources.append(p)
 for p in sources:receipt['source_checks'].append({'path':str(p.relative_to(REPO)),'sha256':sha(p)})
 classes=out/'classes';classes.mkdir();args=[javac,'-encoding','UTF-8']
 if cp:args+=['-classpath',os.pathsep.join(map(str,cp))]
 run('javac',args+['-d',classes]+sources)
 if a.mode=='component':
  testout=out/'test-classes';testout.mkdir();run('smoke-javac',[javac,'-encoding','UTF-8','-classpath',classes,'-d',testout,HERE/'checks/ParserSmoke.java']);run('smoke-java',[java,'-classpath',str(classes)+os.pathsep+str(testout),'ParserSmoke'])
  artifact=out/'tagsoup-classes.jar'
  with zipfile.ZipFile(artifact,'w',compression=zipfile.ZIP_DEFLATED) as z:
   for p in sorted(classes.rglob('*.class')):
    info=zipfile.ZipInfo(str(p.relative_to(classes)),date_time=(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
 else:
  dex=out/'dex';dex.mkdir();args=[java,'-cp',r8,'com.android.tools.r8.D8','--min-api','34']
  for p in cp:args+=['--classpath',p]
  run('d8',args+['--output',dex]+sorted(classes.rglob('*.class')))
  artifact=out/'adapter-mainline-stubs-t7d-rebuilt.jar'
  with zipfile.ZipFile(artifact,'w',compression=zipfile.ZIP_DEFLATED) as z:
   z.writestr('META-INF/MANIFEST.MF','Manifest-Version: 1.0\n\n');z.write(dex/'classes.dex','classes.dex')
  receipt['dex_sha256']=sha(dex/'classes.dex');receipt['historical_dex_equal']=receipt['dex_sha256']==lock['historical_dex_sha256']
  receipt['historical_jar_equal']=sha(artifact)==lock['historical_jar_sha256']
 receipt.update(status='PASS',compiled_class_files=len(list(classes.rglob('*.class'))),artifact={'path':artifact.name,'sha256':sha(artifact),'bytes':artifact.stat().st_size},historical_build_receipt_recovered=False);save();print(json.dumps({'status':'PASS','mode':a.mode,'compiled_class_files':receipt['compiled_class_files'],'artifact':receipt['artifact']}))
if __name__=='__main__':main()
