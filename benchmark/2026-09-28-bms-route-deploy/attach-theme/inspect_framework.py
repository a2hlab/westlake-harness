from pathlib import Path
import subprocess,zipfile,hashlib,json
r=Path(__file__).resolve().parent
b=Path('/home/zhaoyue/a2hlab/build-runs/20260928-oh6.1.0.31-b6')
i=b.parent/'20260928-oh6.1.0.31-b5/inputs'
cp=':'.join(str(p) for p in i.glob('*.jar') if p.name not in ['android.jar','d8.jar','baseline.jar'])
p=Path('/Users/zhaoyue/orca/workspaces/westlake-bms-suite/.bridge-payload/pr03-74e6-portable/android/framework/framework.jar')
out=b/'framework-original';out.mkdir(exist_ok=False)
with zipfile.ZipFile(p) as z:
 for n in z.namelist():
  if n.startswith('classes') and n.endswith('.dex'):
   dex=out/n;dex.write_bytes(z.read(n))
   subprocess.run(['java','-cp',cp,'org.jf.baksmali.Main','disassemble',str(dex),'--classes','Landroid/content/ContextWrapper;,Landroid/app/ContextImpl;,Landroid/app/Activity;,Landroid/app/ActivityThread;','-o',str(out/n.replace('.dex',''))],check=True)
print('framework sha',hashlib.sha256(p.read_bytes()).hexdigest())
