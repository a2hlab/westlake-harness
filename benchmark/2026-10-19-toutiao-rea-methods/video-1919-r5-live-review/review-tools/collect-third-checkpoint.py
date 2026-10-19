#!/usr/bin/env python3
"""Offline evidence checkpoint assembler. No device calls; refuse frozen packet."""
from pathlib import Path
import json,hashlib,subprocess
P=Path(__file__).resolve().parents[1];R=next(x for x in P.parents if (x/'scripts/lab/run_facts.py').is_file());S=Path.home()/'.local/share/westlake/toutiao-resume-20261019'
h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def w(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
r=json.loads((P/'results.json').read_text());assert r['frozen'] is False
pins=json.loads((P/'source-pins.json').read_text());rows={x['path']:x for x in pins['files']}
def pin(f):
 k='$HOME/'+str(f.relative_to(Path.home()));rows[k]={'path':k,'sha256':h(f),'bytes':f.stat().st_size}
for src,name,technical in [('video-r5-live/reentry-third-icon','third-child-icon','guardian-after.txt'),('video-r5-readonly/supervisor-state','third-child-exited','step-0.txt')]:
 d=S/src;o=P/name;o.mkdir(exist_ok=True);rec=json.loads((d/'record.json').read_text());rec['source_record_sha256']=h(d/'record.json');rec['independent_visual_review']='Reviewer viewed actual image: IMEhost, not feed or video.'
 for img in rec['screenshots']:assert img['sha256']==h(d/'screen.jpeg');img['path']='screen.jpeg'
 w(o/'record.json',rec);(o/'screen.jpeg').write_bytes((d/'screen.jpeg').read_bytes())
 text=(d/technical).read_text();lines=[x for x in text.splitlines() if 'boot=3fcb977b' in x or x.startswith(('boot_id=','child=','parent=','birth=','parent_birth=','seq=','mode=','5128 (','AWAITING_REENTRY','UI_UNVERIFIED'))]
 (o/'guardian-excerpt.txt').write_text('\n'.join(lines)+'\n')
 for n in ['record.json','screen.jpeg',technical]:pin(d/n)
 for f in (d/'commands').iterdir():
  if f.is_file():pin(f)
for folder in ['video-r5-third-preplay-log','video-r5-preplay-crashes']:
 d=S/folder
 if d.exists():
  for f in sorted(d.rglob('*')):
   if f.is_file():pin(f)
pins['files']=list(rows.values());w(P/'source-pins.json',pins)
r.update(status='PARTIAL_PREPLAY_EXITS_P1_NOT_OBSERVED',playback='NOT_OBSERVED',audio='unknown',player_true_consumption='NOT_OBSERVED: no confirmed consumer read; param set/get true alone insufficient',reentry='Actual icon-triggered child spawn is evidenced for seq2 and seq3; no feed stability claim.',retries='outer ended attempts after third pre-video exit',p0_scope='Reentry triggers spawn; this window does not prove stable feed recovery under the diagnostic candidate.',cppcrash_scope='Raw files are private and SHA-bound; no random-crash mechanism analysis or P1 attribution.')
r['preplay_exits']=[{'child':'7078/10101','seq':1,'guardian_spawn_event':102,'guardian_exit_event':121},{'child':'14207/20373','seq':2,'guardian_spawn_event':204,'guardian_exit_event':215},{'child':'21760/32058','seq':3,'guardian_spawn_event':322,'guardian_exit_event':340}]
for item in r['preplay_exits']:item.update(cause='unknown; not investigated',video_click_before_exit='none per outer sequence report',feed_observed=False)
r['prerequisites']={'source_final':'Existing 15-file landing unchanged','native_main_commits_outer_reported':['ebb321','15d29','e9bceb'],'instruction':'Treat as prior inputs; do not rewrite them.'}
w(P/'results.json',r)
a=json.loads((P/'api-row5.draft.json').read_text());a['row'].update(status='诊断未到达消费者；P1=NOT_OBSERVED，非播放因果失败',apps='今日头条；三次实际child7078/14207/21760均在视频tap前退出、未亮feed。图标确触发新child，不称重入未触发。',limitations='无视频tap，未确认player读true；set/get true不等于consumer true。三次退出原因未知，不标P1故障；音频unknown，不能承诺P0稳定成功。');a['reason']='Three pre-video exits; no consumer/playback observation. Await rollback+parameter absence106+feed+UNLOCK before publish.';w(P/'api-row5.draft.json',a)
proc=subprocess.run(['python3',str(R/'scripts/lab/run_facts.py'),str(P)],capture_output=True,text=True);assert proc.returncode==0;(P/'facts.txt').write_text(proc.stdout);w(P/'facts-command.json',{'argv':['python3','scripts/lab/run_facts.py',str(P.relative_to(R))],'rc':proc.returncode,'stdout_sha256':h(P/'facts.txt'),'stderr':proc.stderr})
(P/'ACK.md').write_text('# video-1919-r5-live-review\n\nPARTIAL: P1 NOT_OBSERVED, not a playback-caused failure. Three real children spawned then exited before video tap; no feed seen. Parameter get true is not consumer true. Audio unknown; icon-triggered spawn is evidenced but stable P0 recovery is not promised. Original crash files hash-bound only; no mechanism analysis. Await original-plan rollback, freshboot/absent106/feed and UNLOCK.\n\n'+proc.stdout)
(P/'README.md').write_text('''# Toutiao r5 diagnostic observation — not frozen\n\nThree real child instances (7078/10101,14207/20373,21760/32058) exited before any video tap according to the outer sequence record. Guardian records show seq2 event204 spawn→215 exit and seq3 event322 spawn→340 exit; parent5128/birth8325 is retained in the observed records. Actual icon reentry did spawn new children. It did not yield a verified feed in this diagnostic window. All six reviewed images show IMEhost.\n\n**P1=NOT_OBSERVED**, not a playback-caused failure. Actual parameter set/get true is separate from consumer true, which was not observed. Audio unknown. No random-exit/crash mechanism is investigated here and no stable P0 success is promised. Full three stderr/crash originals remain private with portable paths/full hashes.\n\nSource-final15 files and native commits ebb321/15d29/e9bceb are prerequisites, unchanged by this packet. The fifth API row is an unpublished template. Prior r4 packet and first four observations remain unchanged. Wait for original-plan rollback, freshboot, exact NOT_FOUND106, real restored feed, canonical UNLOCK and remote archive before final freeze.\n''')
print(proc.stdout)
