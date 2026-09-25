"""VM only: reproduce stock core libandroid, add one C object, relink one DSO."""
import hashlib,json,pathlib,re,subprocess
ws=pathlib.Path.home()/'a2hlab/ws'
out=ws/'out-operator-sensor48';out.mkdir()
src=ws/'westlake-operator-sensor48/native/android_sensor_noop.c'
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
report={'commands':[],'input_sha256':{},'source_commit':subprocess.check_output(['git','-C',str(src.parents[1]),'rev-parse','HEAD'],text=True).strip()}
assert report['source_commit']=='72ed855566c530c46cdd5ec3f378b1b979f8bbda'
old=json.loads((ws/'out/native-platform/artifacts.json').read_text())
cmd=next(c for c in old['commands'] if c[-1].endswith('/libandroid.so'))
cmd=[x.replace('/home/dspfac/a2hlab/source-closure/verify',str(ws)) for x in cmd]
objects=json.loads((ws/'out/android-ndk15/artifacts.json').read_text())['artifacts']
for n,e in objects.items():assert sha(ws/'out/android-ndk15'/n)==e['sha256'],n
for x in cmd[:-2]:
 if x.startswith('/') and pathlib.Path(x).is_file():report['input_sha256'][x]=sha(x)
def run(c,label):
 report['commands'].append(c)
 p=subprocess.run(c,capture_output=True,text=True)
 (out/(label+'.log')).write_text(p.stdout+p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stderr[-2000:])
stock=out/'libandroid.stock.so';cmd[-1]=str(stock);run(cmd,'stock-link')
report['stock_sha256']=sha(stock)
assert sha(stock)==old['artifacts']['libandroid.so']['sha256']
assert sha(stock)==sha(ws/'out/native-runtime/libandroid.so')
sdk=ws/'toolchains/ohos-sdk/native';obj=out/'android_sensor_noop.c.o'
run([str(sdk/'llvm/bin/clang'),'--target=aarch64-linux-ohos','--sysroot='+str(sdk/'sysroot'),'-O2','-fPIC','-Wall','-Wextra','-Werror','-c',str(src),'-o',str(obj)],'sensor-compile')
new=out/'libandroid.so';cmd.insert(cmd.index('-Wl,--as-needed'),str(obj));cmd[-1]=str(new);run(cmd,'sensor-link')
readelf=str(sdk/'llvm/bin/llvm-readelf')
def defined(p):
 text=subprocess.check_output([readelf,'--dyn-syms','--wide',str(p)],text=True)
 (out/(p.name+'.symbols.txt')).write_text(text)
 return {f[7] for l in text.splitlines() if len(f:=l.split())>=8 and f[4] in ('GLOBAL','WEAK') and f[6]!='UND'}
before,after=defined(stock),defined(new)
need=set('ASensorManager_getInstance ASensorManager_getDefaultSensor ASensorManager_createEventQueue ASensorManager_destroyEventQueue ASensorEventQueue_getEvents ASensorEventQueue_enableSensor ASensorEventQueue_disableSensor'.split())
assert before<=after and after-before==need,(before-after,after-before)
def needed(p):return re.findall(r'\(NEEDED\).*\[([^]]+)\]',subprocess.check_output([readelf,'-d',str(p)],text=True))
assert needed(stock)==needed(new)
report.update({'source_sha256':sha(src),'object_sha256':sha(obj),'sha256':sha(new),'added_exports':sorted(after-before),'needed':needed(new),'recompiled_objects':1,'reused_objects':len(objects)})
(out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['stock_sha256','sha256','added_exports','recompiled_objects','reused_objects']},indent=2))
