"""Run via dockbuild; narrow Java helper merge into the pinned accepted runtime JAR."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[3]
REPORT=Path(__file__).resolve().parent
OUT=Path('/home/zhaoyue/a2hlab/build-runs/20260928-oh6.1.0.31-b5')
INPUT=OUT/'inputs';BUILD=OUT/'build';BUILD.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for item in json.loads((REPORT/'build-inputs.json').read_text()):assert sha(INPUT/item['name'])==item['sha256'],item['name']
assert sha(INPUT/'baseline.jar')=='9161b50756d3ffdfb2a8908ea7ec13f908214688321b2785365977ac40b28dea'
cp=':'.join(str(p) for p in INPUT.glob('*.jar') if p.name not in ['android.jar','d8.jar','baseline.jar'])
def run(args):subprocess.run([str(x) for x in args],check=True)
classes=BUILD/'classes';classes.mkdir();dex=BUILD/'helper-dex';dex.mkdir()
src=ROOT/'bms/src/adapter/framework/activity/java'
run(['javac','--release','8','-cp',INPUT/'android.jar','-d',classes,src/'BinaryAndroidManifestOrientation.java',src/'LaunchActivityAliasProjection.java'])
run(['java','-cp',INPUT/'d8.jar','com.android.tools.r8.D8','--release','--min-api','22','--lib',INPUT/'android.jar','--output',dex,*classes.rglob('*.class')])
with zipfile.ZipFile(INPUT/'baseline.jar') as z:(BUILD/'baseline.dex').write_bytes(z.read('classes.dex'))
smali=BUILD/'smali';helpers=BUILD/'helper-smali';post=BUILD/'postflight'
run(['java','-cp',cp,'org.jf.baksmali.Main','disassemble',BUILD/'baseline.dex','-o',smali])
original={str(p.relative_to(smali)):p.read_bytes() for p in smali.rglob('*.smali')}
run(['java','-cp',cp,'org.jf.baksmali.Main','disassemble',dex/'classes.dex','-o',helpers])
for p in helpers.rglob('*.smali'):
 dest=smali/p.relative_to(helpers);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
scheduler=smali/'adapter/activity/AppSchedulerBridge.smali';text=scheduler.read_text()
pattern=r'(?m)(^    invoke-static[^\n]*->buildActivityInfoFromAbility\([^\n]+\n\s*\n?    move-result-object ([vp]\d+))'
hits=list(re.finditer(pattern,text));assert len(hits)==1,len(hits)
h=hits[0];insertion='\n\n    invoke-static {'+h[2]+'}, Ladapter/activity/LaunchActivityAliasProjection;->apply(Landroid/content/pm/ActivityInfo;)V'
text=text[:h.end()]+insertion+text[h.end():];scheduler.write_text(text)
run(['java','-cp',cp,'org.jf.smali.Main','assemble',smali,'-o',BUILD/'classes.dex'])
run(['java','-cp',cp,'org.jf.baksmali.Main','disassemble',BUILD/'classes.dex','-o',post])
changed=[name for name,data in original.items() if not (post/name).exists() or (post/name).read_bytes()!=data]
allowed={'adapter/activity/AppSchedulerBridge.smali','adapter/activity/BinaryAndroidManifestOrientation.smali','adapter/activity/BinaryAndroidManifestOrientation$StringPool.smali'}
assert set(changed)<=allowed,changed
assert (post/'adapter/activity/AppSchedulerBridge.smali').read_text().count('LaunchActivityAliasProjection;->apply(')==1
output=BUILD/'oh-adapter-runtime.jar'
with zipfile.ZipFile(INPUT/'baseline.jar') as source,zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as dest:
 for item in source.infolist():dest.writestr(item,(BUILD/'classes.dex').read_bytes() if item.filename=='classes.dex' else source.read(item.filename))
result={'baseline_sha256':sha(INPUT/'baseline.jar'),'output':str(output),'output_sha256':sha(output),'changed_existing_classes':changed,'added_classes':sorted(str(p.relative_to(post)) for p in post.rglob('*.smali') if str(p.relative_to(post)) not in original),'sources':{str(p.relative_to(ROOT)):sha(p) for p in [src/'LaunchActivityAliasProjection.java',src/'BinaryAndroidManifestOrientation.java',src/'AppSchedulerBridge.java']}}
(REPORT/'build-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
