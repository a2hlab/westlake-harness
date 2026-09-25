from board34 import *
name,op=sys.argv[1:3];r=R/name;d=json.loads((r/'device-report.json').read_text());root=pathlib.Path(__file__).resolve().parents[1]
def action(cmd):
 out=dev(cmd)
 with (r/'manual-actions.jsonl').open('a') as f:f.write(json.dumps({'epoch':time.time(),'command':cmd,'output':out})+'\n')
 return out
if op=='shot':
 label=sys.argv[3];remote='/data/local/tmp/wv38-current.jpeg';action('snapshot_display -f '+remote+' >/dev/null');recv(remote,r/(label+'.jpeg'));p=root/'preview'/name/(label+'.jpeg');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((r/(label+'.jpeg')).read_bytes())
elif op=='shell':print(action(sys.argv[3]))
elif op=='ready':(r/'setup-done').write_text('Screen inspected and setup complete.\n')
elif op=='go':(r/'go-physical').write_text('Visible article feed inspected.\n')
elif op=='lifecycle':
 log=d['runtime']+f'/private-tmp/adapter_child_{d["child"]}.stderr'
 print(action("grep -E '^\\[B47-SLA\\] ENTRY|^\\[ABILITY38-RESUMED\\]|^\\[SOURCE-WEBVIEW-CMD\\]|GLES library translated|^\\[ERROR:shared_context_state|^\\[INFO:GrGLUtil' "+log))
