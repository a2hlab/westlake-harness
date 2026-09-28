"""Docker-only narrow implementation of ContextWrapper.java.patch in the pinned framework dex."""
from pathlib import Path
import subprocess,zipfile,hashlib,json,re
r=Path(__file__).resolve().parent
base=Path('/home/zhaoyue/a2hlab/build-runs/20260928-oh6.1.0.31-b6');out=base/'framework-fixed-v2';out.mkdir(exist_ok=False)
i=base.parent/'20260928-oh6.1.0.31-b5/inputs';cp=':'.join(str(p) for p in i.glob('*.jar') if p.name not in ['android.jar','d8.jar','baseline.jar'])
original=Path('/Users/zhaoyue/orca/workspaces/westlake-bms-suite/.bridge-payload/pr03-74e6-portable/android/framework/framework.jar')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(original)=='3e106350d882cd1f2f6d71c3cc4e9f124412d16f50a2dcb160007c34e6dde9af'
cls=next((base/'framework-original').glob('*/android/content/ContextWrapper.smali'));dexname=cls.relative_to(base/'framework-original').parts[0]+'.dex'
with zipfile.ZipFile(original) as z:(out/'original.dex').write_bytes(z.read(dexname))
def run(args):subprocess.run([str(x) for x in args],check=True)
run(['java','-cp',cp,'org.jf.baksmali.Main','disassemble',out/'original.dex','-o',out/'smali'])
old={str(p.relative_to(out/'smali')):p.read_bytes() for p in (out/'smali').rglob('*.smali')}
p=out/'smali/android/content/ContextWrapper.smali';text=p.read_text()
pat=r'(?ms)^\.method public getApplicationInfo\(\)Landroid/content/pm/ApplicationInfo;.*?^\.end method'
match=re.search(pat,text);assert match and text.count('.method public getApplicationInfo()')==1
expected=(cls.read_text());assert match.group(0) in expected
replacement=''' .method public getApplicationInfo()Landroid/content/pm/ApplicationInfo;
    .registers 4
    iget-object v0, p0, Landroid/content/ContextWrapper;->mBase:Landroid/content/Context;
    if-nez v0, :b6_attached
    const-string v0, "B6ContextWrapper"
    const-string v1, "[B6] ContextWrapper base not attached"
    new-instance v2, Ljava/lang/Throwable;
    invoke-direct {v2}, Ljava/lang/Throwable;-><init>()V
    invoke-static {v0, v1, v2}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I
    new-instance v0, Ljava/lang/NullPointerException;
    invoke-direct {v0, v1}, Ljava/lang/NullPointerException;-><init>(Ljava/lang/String;)V
    throw v0
    :b6_attached
    invoke-virtual {v0}, Landroid/content/Context;->getApplicationInfo()Landroid/content/pm/ApplicationInfo;
    move-result-object v0
    return-object v0
.end method'''.lstrip()
p.write_text(text[:match.start()]+replacement+text[match.end():])
run(['java','-cp',cp,'org.jf.smali.Main','assemble',out/'smali','-o',out/'classes.dex'])
run(['java','-cp',cp,'org.jf.baksmali.Main','disassemble',out/'classes.dex','-o',out/'postflight'])
def normalize(data):
 return re.sub(rb'(?m)^(\.field[^\n]*) = (?:0x0|false|null)$',rb'\1',data)
raw_changed=[name for name,data in old.items() if (out/'postflight'/name).read_bytes()!=data]
changed=[name for name,data in old.items() if normalize((out/'postflight'/name).read_bytes())!=normalize(data)];assert changed==['android/content/ContextWrapper.smali'],changed
fixed=out/'framework.jar'
with zipfile.ZipFile(original) as src,zipfile.ZipFile(fixed,'w',zipfile.ZIP_DEFLATED) as dst:
 for item in src.infolist():dst.writestr(item,(out/'classes.dex').read_bytes() if item.filename==dexname else src.read(item.filename))
(r/'build-framework.json').write_text(json.dumps({'original_sha256':sha(original),'output':str(fixed),'output_sha256':sha(fixed),'changed_dex':dexname,'changed_classes':changed,'default_static_value_encoding_only':[x for x in raw_changed if x not in changed],'source_patch_sha256':sha(r.parents[2]/'bms/src/adapter/aosp_patches/frameworks/base/core/java/android/content/ContextWrapper.java.patch'),'guard_smali':replacement,'deployed':False},indent=2)+'\n')
print('one class changed',sha(fixed))
