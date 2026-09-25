from board45 import *
pid=int(dev('cat /data/local/tmp/operator45/child.pid').strip());d=json.loads((R/'warm/device-report.json').read_text());log=d['runtime']+f'/private-tmp/adapter_child_{pid}.stderr'
out=dev("grep -E '^\\[ABILITY38-RESUMED\\]|^\\[B47-SLA\\]' "+log+' | head -n 15')
(R/'guard-test/recovery-lifecycle.txt').write_text(out);print(out)
text=dev("hidumper -s WindowManagerService -a '-a'");(R/'guard-test/recovery-windows.txt').write_text(text)
print('\n'.join(l for l in text.splitlines() if 'com.ss.android' in l or 'Focus window' in l))
text=dev("grep -F '[WESTLAKE-REAP]' "+d['stage']+'/parent.log | tail -n 8');(R/'guard-test/parent-reap-late.txt').write_text(text);print(text)
