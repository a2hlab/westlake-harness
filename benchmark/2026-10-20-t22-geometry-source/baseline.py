#!/usr/bin/env python3
"""Recompile the unmodified exact-source libandroid baseline. Never deploys."""
import argparse,hashlib,json,shlex,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--sdk',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
if not a.execute:print('PREVIEW: original source only; device_calls=0');sys.exit()
a.out.mkdir(parents=True,exist_ok=False);rec={'candidate':False,'device_calls':0,'commands':[],'pins':{}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):rec['pins'][str(p)]={'sha256':sha(p),'bytes':p.stat().st_size}
def run(n,argv):
 (a.out/(n+'.argv.json')).write_text(json.dumps(list(map(str,argv)),indent=2)+'\n')
 with (a.out/(n+'.stdout')).open('wb') as so,(a.out/(n+'.stderr')).open('wb') as se:
  try:rc=subprocess.run(list(map(str,argv)),stdout=so,stderr=se,timeout=90).returncode
  except subprocess.TimeoutExpired:rc=124
 (a.out/(n+'.rc')).write_text(str(rc)+'\n');rec['commands'].append({'name':n,'rc':rc});(a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
 if rc:raise RuntimeError(n)
record=a.inputs/'out-sp20/webview-shims/artifacts.json';src=a.inputs/'out-sp20/webview-shims/src/framework/webview-shim/libandroid_webview_core_shim.c';old=a.inputs/'out-sp20/webview-shims/libandroid.so';cc=a.sdk/'llvm/bin/clang'
assert sha(src)=='37cfbdcb5b8efdb498341dd048820f4032a984c8152301d7886eaac3ad56473b'
assert sha(old)=='76512d97758c308acf7baff4647f07db792c02b8fae2eda93399bd18eda03727'
for x in [record,src,old,cc,a.sdk/'llvm/bin/ld.lld',Path(__file__)]:pin(x)
run('00-frozen',[sys.executable,a.repo/'scripts/lab/check_frozen.py','--git',a.repo,'--registry',a.repo/'knowledge/frozen/frozen.json'])
original=next(shlex.split(c) for c in json.loads(record.read_text())['commands'] if ' -o ' in c and c.endswith('libandroid.so '));(a.out/'original.argv.json').write_text(json.dumps(original,indent=2)+'\n')
args=[str(a.inputs)+'/'+x.split('/source-closure/verify/',1)[1] if x.startswith('/home/') else '--sysroot='+str(a.inputs)+'/'+x.split('/source-closure/verify/',1)[1] if x.startswith('--sysroot=') else x for x in original]
args[0]=str(cc);args[-1]=str(a.out/'baseline.so');args.insert(1,'-resource-dir='+str(a.inputs/'toolchains/ohos-sdk/native/llvm/lib/clang/15.0.4'))
run('01-driver',args+['-###'])
run('02-dependencies',[cc,'--target=aarch64-linux-ohos','--sysroot='+str(a.inputs/'toolchains/ohos-sdk/native/sysroot'),'-resource-dir='+str(a.inputs/'toolchains/ohos-sdk/native/llvm/lib/clang/15.0.4'),'-M',src])
for x in shlex.split((a.out/'02-dependencies.stdout').read_text().replace('\\\n',' ').split(': ',1)[1]):pin(Path(x))
for line in (a.out/'01-driver.stderr').read_text().splitlines():
 if 'ld.lld' in line:
  for x in shlex.split(line):
   q=Path(x)
   if q.is_file():pin(q)
run('03-baseline',args);rec['output']={'sha256':sha(a.out/'baseline.so'),'bytes':(a.out/'baseline.so').stat().st_size};rec['exact_match']=sha(old)==rec['output']['sha256'];rec['status']='UNMODIFIED_BASELINE_COMPILED';(a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({'output':rec['output'],'exact_match':rec['exact_match']}))
