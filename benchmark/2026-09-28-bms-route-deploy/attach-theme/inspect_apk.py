from pathlib import Path
import subprocess,json,hashlib
r=Path(__file__).resolve().parent
b=Path('/home/zhaoyue/a2hlab/build-runs/20260928-oh6.1.0.31-b6')
i=b.parent/'20260928-oh6.1.0.31-b5/inputs'
cp=':'.join(str(p) for p in i.glob('*.jar') if p.name not in ['android.jar','d8.jar','baseline.jar'])
for p in sorted(b.glob('classes*.dex')):
 text=subprocess.check_output(['java','-cp',cp,'org.jf.baksmali.Main','list','classes',str(p)],text=True)
 (b/(p.name+'.classes.txt')).write_text(text)
 selected=[x for x in text.splitlines() if 'AppCompat' in x or 'ContextThemeWrapper' in x or x=='Lorg/wikipedia/main/MainActivity;' or x=='Lorg/wikipedia/activity/BaseActivity;']
 print(p.name,selected,flush=True)
 # Include all dex methods so obfuscated delegate callers can be traced locally.
 subprocess.run(['java','-cp',cp,'org.jf.baksmali.Main','disassemble',str(p),'-o',str(b/(p.name+'.smali'))],check=True)
