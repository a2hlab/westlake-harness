from pathlib import Path
import json,re,subprocess
r=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/warm48';d=r/'warm-r1';lines=(d/'child.stderr').read_text(errors='replace').splitlines();sample=[json.loads(l) for l in (d/'samples.jsonl').read_text().splitlines()];j=json.loads((d/'result.json').read_text());pid=j['child']
alive=[s['elapsed'] for s in sample if any(l.startswith(str(pid)+' (') and l.rsplit(') ',1)[1].split()[0]!='Z' for l in s['output'].splitlines())]
j.update(last_alive_sample_s=max(alive),native_sig11_headers=sum(l.startswith('Fatal signal 11') for l in lines),parent_exit_one='child '+str(pid)+' exited(1)' in (d/'parent.log').read_text(),maps_bytes=(d/'maps60.maps').stat().st_size,main_threw=any('J_invokeStaticMain_main_threw' in l for l in lines),uncaught=[l for l in lines if l.startswith("[UNCAUGHT] thread=")],refusals=[l for l in lines if l.startswith('[WESTLAKE-LOADER] refusing')],body_pass=False,acceptance_pass=False,article_input='not injected: original PID/birth liveness assertion failed before uinput; intended380,390',feed_image='during-60.jpeg')
(d/'strict-review.json').write_text(json.dumps(j,indent=2));print(json.dumps(j,indent=2))
(d/'visual-review.json').write_text(json.dumps({'body_text_visible':False,'feed_real_titles':True,'image':'during-60.jpeg','final_screen':'real feed, no modal obstruction, article not opened'},indent=2))
script='/Users/zhaoyue/orca/workspaces/westlake-harness-warm48/benchmark/2026-09-26-warm-hook-48/scripts/assert_heap_hook_refuse.sh'
p=subprocess.run(['bash',script,str(d)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30);(d/'upstream-gate.txt').write_text(p.stdout+'\nrc='+str(p.returncode));print(p.stdout)
