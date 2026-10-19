#!/usr/bin/env python3
"""Offline evidence assembly for this exact r5 window; no device or build calls.
Historical assembly recipe, not a deployment tool. Existing freeze refuses rerun.
"""
from pathlib import Path
import csv,hashlib,io,json,re,shutil,subprocess,tempfile
from html.parser import HTMLParser
F=Path(__file__).resolve().parent
R=next(p for p in F.parents if (p/'scripts/lab/run_facts.py').is_file())
M=R.parent/'westlake-harness';S=Path.home()/'.local/share/westlake/toutiao-resume-20261019'
B=Path('benchmark/2026-10-19-toutiao-rea-methods');P=R/B/'video-1919-r5-live-review';U=R/B/'video-1919-r5-review';A=Path('benchmark/2026-10-19-api-progress-update')
assert not (F/'freeze.json').exists(), 'frozen; do not rerun'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
def portable(p):return '$HOME/'+str(p.relative_to(Path.home()))
for n in ['window-archive.json','window-close.json','state-diff.json']:copy(M/U.relative_to(R)/n,U/n)
close=read(U/'window-close.json');archive=read(U/'window-archive.json')
assert archive['archive_sha256']=='998a94b131c6174ff2bd4e2a56ea4513f03c42a5e9859db9299202c0d7bda23e' and archive['bytes']==1949217 and archive['remote_verified']
assert close['unlock_line'].encode() in (M/'.octos/boards/app-lighting.md').read_bytes()
assert close['lock_released'] and close['p1']=='NOT_OBSERVED'
(F/'canonical-lock-excerpt.txt').write_text(close['lock_line']+'\n'+close['unlock_line']+'\n')
for srcname,dstname,verdict in [('restored-observe','restored-first-exit','IMEhost, not feed; first baseline child8092 exited.'),('reentry-observe','restored-feed','News list and gray video card; feed visible, no video playback proven.')]:
 src=S/'video-r5-rollback-live'/srcname;dst=P/dstname;record=read(src/'record.json')
 for shot in record['screenshots']:
  assert h(src/'screen.jpeg')==shot['sha256'];shot['path']='screen.jpeg'
 record['source_record_sha256']=h(src/'record.json');record['independent_visual_review']=verdict
 write(dst/'record.json',record);copy(src/'screen.jpeg',dst/'screen.jpeg')
 copy(src/'guardian-after.txt',dst/'guardian.original.txt')
assert h(P/'restored-feed/screen.jpeg')==close['observed_feed_sha256']
q=S/'video-r5-restored-identity/originals';ident=(q/'step-0.txt').read_text()
assert 'RESTORED_IDENTITY' in ident and 'errNum is:106!' in ident
for val in ['d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4','fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9','b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02']:assert ident.count(val)==2
assert '91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e' in ident
copy(q/'step-0.txt',P/'restored-identity/identity.original.txt')
for i in ['00006','00007','00010']:
 d=read(q/'commands'/('command-'+i+'.json'));assert d['exit_code']==0
 out=(q/'commands'/('command-'+i+'.stdout.txt')).read_text();assert re.search(r'__BMS_REMOTE_RC_[a-f0-9]+__0',out)
 for f in (q/'commands').glob('command-'+i+'.*'):copy(f,P/'restored-identity/commands'/f.name)
cmd=read(q/'commands/command-00007.json')['argv'][-1]
assert 'stat -L -c %d:%i' in cmd and 'test ! -e' in cmd and 'grep -q libopensles_android_compat /proc/5496/maps' in cmd
snapshots=[read(S/row['name']/'snapshot.json') for row in read(U/'state-diff.json')['snapshots']]
for snap in snapshots:
 assert snap['complete'] and snap['collection_complete'] and snap['boot_stable'] and not snap['errors']
 assert snap['plan_target_count']==62 and len(snap['labels'])==351
 for k in ['plan_sha256','labels','init_configs','selinux_enforce']:assert snap[k]==snapshots[0][k],k
write(P/'snapshot-review.json',{'status':'PASS','same_plan':snapshots[0]['plan_sha256'],'snapshots':4,'targets_each':62,'labels_each':351,'labels_init_configs_selinux_equal':True,'snapshot_source_sha256':{row['name']:h(S/row['name']/'snapshot.json') for row in read(U/'state-diff.json')['snapshots']},'scope':'No claim that all runtime bytes were equal during the candidate window.'})
for mode in ['apply','rollback']:
 src=S/('video-r5-'+mode)
 for n in ['plan.json','result.json','swap.sh']:copy(src/n,P/mode/n)
 # Keep the actual remote swap command triplet if portable; other commands remain private SHA-bound.
 for p in (src/'commands').glob('*.json'):
  d=read(p);argv=' '.join(d.get('argv',[]))
  if 'shell' in d.get('argv',[]) and ('sh ' in argv) and ('swap' in argv or 'ttvideo' in argv):
   if '/Users/' not in p.read_text():
    for f in p.parent.glob(p.stem+'.*'):copy(f,P/mode/'commands'/f.name)
assert read(P/'rollback/plan.json')['origin_apply_plan_sha256']==h(P/'apply/plan.json')
for n in ['video_guarded_window_r6.py','video_r5_control.py','board_step.py','live_tools.py','wait_boot_ready.py','archive_video_r5.py']:
 src=S/n;assert src.is_file();assert b'/Users/' not in src.read_bytes();copy(src,P/'historical-recipes'/n)
assert h(P/'historical-recipes/video_guarded_window_r6.py')=='b8e9c4b2296bebf91f2364e272f6047cfc494e7f70e719688b73fd0ae695a531'
pins=read(P/'source-pins.json');rows={x['path']:x for x in pins['files']}
for item in archive['members']:
 p=S/item
 if not p.exists():continue
 files=[p] if p.is_file() else sorted(x for x in p.rglob('*') if x.is_file())
 for f in files:rows[portable(f)]={'path':portable(f),'sha256':h(f),'bytes':f.stat().st_size}
pins['files']=list(rows.values());pins['archive_public_receipt']=str(U.relative_to(R)/'window-archive.json');write(P/'source-pins.json',pins)
r=read(P/'results.json');r.update(token='video-1919-r5-final-packet',status='CLOSED_DIAGNOSTIC_NOT_OBSERVED_RESTORED',frozen=True,rollback='VERIFIED: original run/media/player SHA; physical/private inode equality; compat absent and parent unmapped; original cfg; freshboot parameter errNum106',restored_feed={'status':'VISUALLY_CONFIRMED_NEWS_LIST_GRAY_VIDEO_CARD_NOT_PLAYBACK','sha256':h(P/'restored-feed/screen.jpeg'),'boot':close['restored_boot'],'parent':'5496/7495','child':'14317/17079','first_baseline_child':'8092/9039 exited before second real icon recovered feed'},unlock=close['unlock_line'],archive={'sha256':archive['archive_sha256'],'bytes':archive['bytes'],'receipt':str(U.relative_to(R)/'window-archive.json')},snapshot_review='snapshot-review.json',source_prerequisite_main_commit='3d326919cf',duration_seconds=817)
write(P/'results.json',r)
proc=subprocess.run(['python3',str(M/'scripts/lab/run_facts.py'),str(P)],capture_output=True,text=True)
assert proc.returncode==0; (P/'facts.txt').write_text(proc.stdout);(P/'facts.stderr.txt').write_text(proc.stderr)
write(P/'facts-command.json',{'argv':['python3','$MAIN/scripts/lab/run_facts.py',str(P.relative_to(R))],'rc':proc.returncode,'tool_sha256':h(M/'scripts/lab/run_facts.py')})
(P/'README.md').write_text('''# R5 transient-parameter diagnostic: not observed, restored\n\nParameter set/get true did not establish player consumption. Three actual children (7078, 14207, 21760) exited before any video tap and never displayed feed in this candidate window. Icon reentry did spawn new children. This is P1 NOT_OBSERVED, not a playback-causal failure or a successful playback test. Audio and diagnostic-consumer true remain unknown/not observed. No random-crash mechanism was investigated.\n\nThe same r4 four artifacts were reused; no new build occurred. Existing source/provider evidence remains at MAIN commit3d326919cf and is not redelivered. Source mapping, artifact build receipts, parameter readback, and live playback are separate claims.\n\nRollback restored the exact original run/media/player and physical/private inode equality, removed compat (also absent from parent maps), retained cfg91e31, and freshboot d90678dd returned exact parameter error106. First baseline child8092 exited; a second real icon spawned14317 and the reviewed image shows a news list with a gray video card, not playing video. This does not establish stable first-launch recovery. All4 same-plan snapshots have62targets/351labels with unchanged labels/init configs/SELinux. The canonical lock was released21:01:41 after13m37s.\n\n## Layout and provenance\n\nSmall original screenshots, command triplets and technical guardian excerpts are public. Portable private paths and exact SHA values are in source-pins.json; full stderr/crashes and large raw evidence remain in the remotely verified window archive referenced by ../video-1919-r5-review/window-archive.json. Public archive/close/state metadata are copied byte-for-byte from MAIN. Normalized screenshot records change only private path representation and add a separate independent review; original record SHA is retained. Raw sources remain untouched.\n\nHistorical execution sources under historical-recipes are exact recipes for the original guarded window, not generic safe rerun entrypoints. review-tools and api-preview preserve earlier checkpoints; their pending text is historical and superseded by results.json. No live commands were executed by this reviewer. Actual screenshot/alive counts are solely facts.txt; absent standard alive tables mean unknown. Final landing includes a separate historical review-generator archive. The API update adds one observation, preserves the first4 objects and does not change the signed315 table or its grades.\n''')
(P/'ACK.md').write_text('video-1919-r5-final-packet: scoped ACCEPT of diagnostic evidence and restoration only. P1 NOT_OBSERVED; audio unknown; no consumer-true or stable P0 claim. See results.json and facts.txt. No device/build calls or push.\n')
# Original renderer in an isolated combined root, exact prior four objects.
base=read(M/A/'observations.json');assert len(base['rows'])==4
new=json.loads(json.dumps(base));row=read(P/'api-row5.draft.json')['row']
row['status']='诊断未到达消费者；P1=NOT_OBSERVED；已回滚收窗'
row['deployment']='沿用r4四件，无新构建；原run/media/player与private inode核对、compat absent/unmapped、cfg91e31及freshboot参数106已恢复。首baseline8092退出，第2图标child14317显示新闻列表+灰视频卡（非播放）；21:01:41解锁。'
row['frozen']=False # no verified public API freeze
row['limitations']='无视频tap，未确认player读true；set/get true不等于consumer true。三次退出原因未知，不归因P1故障；音频unknown。恢复首child也退出，不承诺P0稳定/冷启零失败。'
def ref(path):
 p=R/path if (R/path).is_file() and (path.startswith(str(P.relative_to(R))) or path.startswith(str(U.relative_to(R)))) else M/path
 return {'path':path,'sha256':h(p)}
row['source']=[ref(str(P.relative_to(R)/'historical-recipes/video_r5_control.py'))]+[ref(str(B/'video-1919-r5-param-recovery'/n)) for n in ['source-final.json','provider-final.json']]
row['build']=[ref(str(B/'video-1919-r4-live-review/archive/build-artifacts-receipt.json'))]
row['evidence']=[ref(str(P.relative_to(R)/n)) for n in ['results.json','admission.original.json','first-child-loaded/identity.original.txt','second-child-exited/identity.original.txt','third-child-exited/guardian-excerpt.txt','restored-first-exit/screen.jpeg','restored-feed/screen.jpeg','restored-identity/identity.original.txt','parameter-restored/commands/command-00007.stdout.txt','snapshot-review.json']]+[ref(str(U.relative_to(R)/n)) for n in ['window-close.json','window-archive.json','state-diff.json']]
new['rows'].append(row);write(F/'api-row5.json',row)
with tempfile.TemporaryDirectory(prefix='r5-final-render-') as td:
 root=Path(td);dst=root/A;dst.mkdir(parents=True);copy(M/A/'render.py',dst/'render.py');write(dst/'observations.json',new)
 for rr in new['rows']:
  for group in ['source','build','evidence']:
   for item in rr[group]:
    path=item['path'];p=R/path if path.startswith(str(P.relative_to(R))) or path.startswith(str(U.relative_to(R))) else M/path
    assert h(p)==item['sha256'];copy(p,root/path)
 hist=Path('benchmark/2026-10-14-api-source-delivery/views/index.html');copy(M/hist,root/hist)
 run=subprocess.run(['python3',str(dst/'render.py')],capture_output=True,text=True);assert run.returncode==0,run.stderr
 (F/'renderer.stdout.txt').write_text(run.stdout);(F/'renderer.stderr.txt').write_text(run.stderr)
 class Links(HTMLParser):
  def __init__(self):super().__init__();self.links=[]
  def handle_starttag(self,t,a):
   if t=='a':self.links.extend(v for k,v in a if k=='href')
 parser=Links();parser.feed((dst/'index.html').read_text());assert all((dst/u.split('#')[0]).is_file() for u in parser.links)
 csvrows=list(csv.DictReader(io.StringIO((dst/'observations.csv').read_text(encoding='utf-8-sig'))))
 assert len(csvrows)==5
 for a,b in zip(csvrows,new['rows']):
  for k,v in b.items():assert (json.loads(a[k]) if isinstance(v,list) else a[k])==(v if isinstance(v,list) else str(v)),k
 assert new['rows'][:4]==base['rows']
 # Deliver only the four rendered canonical successors; prior source inputs pinned below.
 for n in ['observations.json','observations.csv','index.html','results.json']:copy(dst/n,R/A/n)
 write(F/'checks.json',{'renderer_rc':run.returncode,'original_renderer_sha256':h(M/A/'render.py'),'api_rows':5,'refs_by_row':[sum(len(rr[g]) for g in ['source','build','evidence']) for rr in new['rows']],'html_links':len(parser.links),'all_links_resolved':True,'csv_all_fields_equal':True,'first_four_objects_unchanged':True,'previous_canonical_sha256':{n:h(M/A/n) for n in ['observations.json','observations.csv','index.html','results.json']},'historical315_modified':False,'device_calls':0,'builds':0,'public_archive_three_files_exact_main':True,'snapshot_and_identity_checks':'PASS'})
print(proc.stdout);print((F/'checks.json').read_text())
