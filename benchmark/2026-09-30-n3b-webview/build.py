#!/usr/bin/env python3
"""Compile one new TU, reproduce N3 first, then relink with the same recipe/order."""
import hashlib,json,os,re,shutil,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1];W=R/'bms/src/.work';B=W/'n3b-webview'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
B.mkdir(parents=True,exist_ok=True)
# Preserve every N3 object; never refresh the old cache or rebuild unrelated TUs.
objects={}
for f in sorted((W/'n3-native/runtime-objects').glob('*.o')):
 out=B/'runtime-objects'/f.name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,out);os.utime(out,None);objects[f.name]=sha(f)
(P/'baseline-objects.json').write_text(json.dumps(objects,indent=2)+'\n')
original=R/'benchmark/2026-09-30-n3-native'
recipe=(original/'runtime-recipe.sh').read_text();driver=(original/'build-runtime.sh').read_text()
# These inputs are historical recorded recipes. Relocate to the current checkout;
# generated author-absolute commands stay in .work and are not shipped as source.
def relocate(s):
 return re.sub(r'/(?:Users|home)/[^\s\"\']+?/westlake-harness-bms-deploy',str(R),s)
recipe=relocate(recipe)
extra='''if [ "${N3B_WITH_PUBLICATION:-0}" = "1" ]; then
    $CXX $COMMON -include "$BC/libcxx_compat.h" $INC $DEFS -c "$N3B_SOURCE" -o "$BUILD/webview_publication.o" || exit $?
    objs+=("$BUILD/webview_publication.o")
fi
'''
anchor='if $CXX --target=aarch64-linux-ohos $LDFLAGS'
assert recipe.count(anchor)==1;recipe=recipe.replace(anchor,extra+anchor)
(B/'recipe.sh').write_text(recipe)
driver=relocate(driver).replace('/n3-native/runtime-out','/n3b-webview/runtime-out').replace('/n3-native/runtime-objects','/n3b-webview/runtime-objects')
driver='\n'.join(l for l in driver.splitlines() if not any(t in l for t in ['build-egl.sh','restore_cache.py']))+'\n'
driver=driver.replace(str(original/'runtime-recipe.sh'),str(B/'recipe.sh'))
(B/'driver.sh').write_text(driver)
env=os.environ.copy();env['N3B_SOURCE']=str(P/'src/webview_publication.cpp')
records={'recipe_sha256':sha(original/'runtime-recipe.sh'),'driver_sha256':sha(original/'build-runtime.sh'),'objects':len(objects),'source_sha256':sha(P/'src/webview_publication.cpp'),'rounds':[]}
for name,flag in [('baseline','0'),('candidate','1')]:
 env['N3B_WITH_PUBLICATION']=flag
 with (P/f'build-{name}.log').open('w') as log:
  result=subprocess.run(['bash',str(B/'driver.sh')],env=env,stdout=log,stderr=subprocess.STDOUT)
 records['rounds'].append({'mode':name,'returncode':result.returncode})
 (P/'build-results.json').write_text(json.dumps(records,indent=2)+'\n')
 if result.returncode:raise SystemExit(f'{name} failed: see build-{name}.log')
 output=B/'runtime-out/liboh_android_runtime.so';h=sha(output)
 records[name+'_sha256']=h
 if name=='baseline':
  expected='2cf33c15962c68011889fa74c6b2ef5793675871e6a6083a15b82db95104c13a'
  records['baseline_expected']=expected;records['baseline_bit_identical']=h==expected
  (P/'build-results.json').write_text(json.dumps(records,indent=2)+'\n')
  if h!=expected:raise SystemExit('N3 baseline relink differs; stop before candidate')
  shutil.copy2(output,B/'baseline.so')
 assert all(sha(B/'runtime-objects'/f)==h for f,h in objects.items()),'old object changed'
(P/'build-results.json').write_text(json.dumps(records,indent=2)+'\n')
print('N3b candidate',records['candidate_sha256'])
