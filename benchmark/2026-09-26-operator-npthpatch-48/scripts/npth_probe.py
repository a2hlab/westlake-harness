from pathlib import Path
import sys,json
name=sys.argv[1];p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),name,'inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
j=json.loads((x['r']/'instance.json').read_text());pid=str(j['child']);log=x['rt']+'/private-tmp/adapter_child_'+pid+'.stderr'
s=x['dev']("cat /proc/uptime; sha256sum /proc/"+pid+"/root/data/local/tmp/asx/lib/arm64-v8a/libnpth.so; grep '/libnpth.so' /proc/"+pid+"/maps; grep -E 'UnsatisfiedLinkError|npth.*JNI|JNI.*npth|NATIVE-LOAD.*libnpth.so|refusing.*npth|CM-EXIT|UNCAUGHT' "+log+" | tail -45",8);(x['r']/'npth-load-proof.txt').write_text(s);print(s)
