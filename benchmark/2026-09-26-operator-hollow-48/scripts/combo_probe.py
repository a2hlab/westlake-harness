from pathlib import Path
import sys,json
name=sys.argv[1];p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),name,'inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
j=json.loads((x['r']/'instance.json').read_text());pid=str(j['child']);log=x['rt']+'/private-tmp/adapter_child_'+pid+'.stderr'
libs=['libnpth.so','libgodzilla-memsponge.so','libmonitorcollector-lib.so','libgodzilla-sysopt.so'];prefix='/proc/'+pid+'/root/data/local/tmp/asx/lib/arm64-v8a/'
s=x['dev']("cat /proc/uptime; sha256sum "+' '.join(prefix+n for n in libs)+"; grep -E '/(libnpth|libgodzilla-memsponge|libmonitorcollector-lib|libgodzilla-sysopt)\\.so' /proc/"+pid+"/maps; grep -E 'UnsatisfiedLinkError|NATIVE-LOAD.*(libnpth.so|memsponge|monitorcollector-lib|godzilla-sysopt)|JNI.*(npth|memsponge|monitorcollector|sysopt)|CM-EXIT|UNCAUGHT' "+log+" | tail -50",10);(x['r']/'combo-load-proof.txt').write_text(s);print(s)
