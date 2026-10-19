#!/usr/bin/env python3
"""Offline r7 evidence assembly. No device/compiler/network calls. Not a replay tool."""
from pathlib import Path
import json,hashlib,subprocess,tempfile,csv,io,re
from html.parser import HTMLParser
F=Path(__file__).resolve().parent;R=next(p for p in F.parents if (p/'scripts/lab/run_facts.py').is_file());M=R.parent/'westlake-harness';S=Path.home()/'.local/share/westlake/toutiao-resume-20261019';B=Path('benchmark/2026-10-19-toutiao-rea-methods');P=R/B/'video-1919-r7-live-review';A=Path('benchmark/2026-10-19-api-progress-update')
assert not (F/'freeze.json').exists(),'frozen packet'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def copy(a,b):b.parent.mkdir(parents=True,exist_ok=True);b.write_bytes(a.read_bytes())
close=read(S/'video-r7-window-close.json');arc=read(S/'video-r7-window-archive/receipt.json');assert arc['archive_sha256']=='c3b9073a122ba58bd5ae7d2780282202ff069a2538c39029f42543ac1c67ae1c' and arc['bytes']==7452482 and arc['remote_verified']
# Reuse MAIN's public receipt exactly if already published.
public=M/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r5/retry-r7/window-archive.json'
if public.exists():
 copy(public,P/'archive/window-archive.json');assert read(public)['archive_sha256']==arc['archive_sha256']
else:
 d=dict(arc);d['remote']='$HW248_ARTIFACT_ROOT/toutiao-video-r7-20261019/window.tar.gz';d['private_receipt_sha256']=h(S/'video-r7-window-archive/receipt.json');write(P/'archive/window-archive.json',d)
copy(S/'video-r7-window-close.json',P/'archive/window-close.json');copy(S/'video-r7-admission.json',P/'admission.original.json')
board=(M/'.octos/boards/app-lighting.md').read_text(errors='replace');assert close['unlock_line'] in board
lock=next(x for x in board.splitlines() if x.startswith('LOCK(61b0657200000000000000000324012c)') and '2026-10-19T22:25:10' in x)
(F/'canonical-lock-excerpt.txt').write_text(lock+'\n'+close['unlock_line']+'\n')
# Exact images; portable derived records pin their unmodified private originals.
selected=[('video-r7-live/first-icon','candidate-first-icon','Early IMEhost, not feed.'),('video-r7-identity/current','candidate-feed','Actual news feed independently viewed.'),('video-r7-play1','play1','Same cover at t5/t20/t25; t20/t25 byte-equal. No demonstrated playback; audio unknown.'),('video-r7-restored-live/first-icon','restored-first-icon','Early IMEhost; not a feed capture.'),('video-r7-restored-identity/current','restored-current','IMEhost at this capture; later baseline-final image supplies feed evidence.'),('video-r7-restored-identity/baseline-final','restored-feed','Actual news feed independently viewed. First icon eventually reached feed; no zero-delay or long-term-stability claim.')]
for srcname,dstname,verdict in selected:
 src=S/srcname;dst=P/dstname;rec=read(src/'record.json')
 for shot in rec['screenshots']:
  f=src/Path(shot['path']).name;assert h(f)==shot['sha256'];copy(f,dst/f.name);shot['path']=f.name
 rec['source_record_sha256']=h(src/'record.json');rec['independent_visual_review']=verdict;write(dst/'record.json',rec)
 # Do not copy large guardian/log files unless needed for exact current identity.
 if (src/'step-0.txt').exists() and dstname in ['candidate-feed','restored-feed']:copy(src/'step-0.txt',dst/'identity.original.txt')
assert h(P/'restored-feed/screen.jpeg')==close['feed_sha256']
rec=read(P/'restored-feed/record.json');orig=(P/'restored-feed/identity.original.txt').read_text();assert 'child=7422' in orig and 'birth=8420' in orig and 'parent_birth=6888' in orig
assert re.search(r'^\s*7422\s+4897\s+20011206\s',orig,re.M)
for value in ['d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4','fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9','b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02']:
 assert orig.count(value)==2
assert 'errNum is:106!' in orig
assert 'test ! -e ' in rec['commands'][0] and '91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e' in rec['commands'][0]
for mode in ['apply','rollback']:
 for n in ['plan.json','result.json','swap.sh']:copy(S/('video-r7-'+mode)/n,P/mode/n)
assert read(P/'rollback/plan.json')['origin_apply_plan_sha256']==h(P/'apply/plan.json')
for srcname,dst in [('video-r7-log-enabled','parameter-enabled'),('video-r7-restored-metadata','parameter-restored'),('video-r7-reboot','candidate-reboot'),('video-r7-ready','candidate-ready'),('video-r7-rollback-reboot','rollback-reboot'),('video-r7-restore-ready','rollback-ready')]:
 for n in ['result.json','ready.json','param-before.txt','param-after.txt']:
  if (S/srcname/n).exists():copy(S/srcname/n,P/dst/n)
# Preserve one actual swap receipt triplet per action and exact final checks.
for srcname,dst,needle in [('video-r7-apply','apply','swap.sh'),('video-r7-rollback','rollback','swap.sh'),('video-r7-restored-identity/baseline-final','restored-feed','errNum_never_match')]:
 for f in sorted((S/srcname/'commands').glob('*.json')):
  d=read(f);argv=' '.join(d.get('argv',[]));selected=('shell' in d.get('argv',[]) and (needle in argv or (dst=='restored-feed' and 'test ! -e' in argv)))
  if selected:
   assert d['exit_code']==0
   for q in f.parent.glob(f.stem+'.*'):copy(q,P/dst/'commands'/q.name)
# Native-after identity and minimal exact technical excerpt; no full stderr/hilog public.
src=S/'video-r7-native-after';dst=P/'native-after'
for n in ['identity.json','before-child.stat','after-child.stat','before-parent.stat','after-parent.stat','parameter.txt']:copy(src/n,dst/n)
for n,birth,ppid in [('before-child.stat','8704','4979'),('after-child.stat','8704','4979'),('before-parent.stat','6990','1'),('after-parent.stat','6990','1')]:
 tail=(dst/n).read_text().rsplit(') ',1)[1].split();assert tail[19]==birth and tail[1]==ppid
for f in sorted((src/'commands').glob('*.json')):
 d=read(f)
 if 'hilog -x -P 6951 -L D,I,W,E,F -v monotonic' in ' '.join(d.get('argv',[])):
  write(dst/'hilog-invocation.json',{'argv':d['argv'],'exit_code':d['exit_code'],'original_receipt_sha256':h(f),'stdout_sha256':h(f.with_suffix('.stdout.txt')),'stderr_sha256':h(f.with_suffix('.stderr.txt'))})
lines=(src/'child.stderr').read_text(errors='replace').splitlines();hits=[(i+1,x) for i,x in enumerate(lines) if x=='[WESTLAKE-WEBVIEW-BIONIC] property debug.ttplayer.log.enable=true'];assert len(hits)==1
(dst/'property-consumer.original-excerpt.txt').write_text(hits[0][1]+'\n');write(dst/'excerpt-provenance.json',{'raw_path':'$HOME/.local/share/westlake/toutiao-resume-20261019/video-r7-native-after/child.stderr','raw_sha256':h(src/'child.stderr'),'line':hits[0][0],'note':'Actual bridge read; exact caller stack not captured. Verbose flag independently sampled1.'})
copy(S/'video-r7-play1/got.json',P/'play1/got.original.json')
# Actual8slot results, matched source/path identities and registered callback chain.
for n in ['reads.json','before-liblog.so-identity.txt','after-liblog.so-identity.txt','before-libttmplayer.so-identity.txt','after-libttmplayer.so-identity.txt']:copy(S/'video-r7-log-slots1'/n,P/'log-slots'/n)
copy(S/'video-r7-logger-chain/reads.json',P/'logger-chain/reads.json');copy(S/'video-r7-identity/logger-files/step-0.txt',P/'logger-chain/files.original.txt')
# Only relevant maps, with full map originals SHA-pinned in source-pins.
for srcname,dstname,names in [('video-r7-log-slots1','log-slots',['maps-before.txt','maps-after.txt']),('video-r7-logger-chain','logger-chain',['maps.txt','maps-after.txt'])]:
 for n in names:
  text=(S/srcname/n).read_text(); keep=[l for l in text.splitlines() if any(v in l for v in ['libttmplayer.so','liblog.so','libbase.so','liboh_android_runtime.so','libhilog.so','libwebview_bionic_shim.so'])]
  (P/dstname/(n+'.selected.txt')).write_text('\n'.join(keep)+'\n')
# New scripts preserved exactly; old executable recipes reused by immutable references, not recopied.
copy(S/'read_r7_chain.py',P/'historical-recipes/read_r7_chain.py');probe=M/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r5/retry-r6/read_log_state.py';assert h(probe)=='6812122e7eb7f8184a231c5ed6e2ccbf2712960a38d6a75fc77436e391bf6aa9';copy(probe,P/'historical-recipes/read_log_state.py')
refs=[]
for n in ['video_guarded_window_r6.py','video_r5_control.py','board_step.py','live_tools.py','wait_boot_ready.py']:
 q=M/B/'video-1919-r6-live-review/historical-recipes'/n;assert h(q)==h(S/n);refs.append({'path':str(q.relative_to(M)),'sha256':h(q)})
write(P/'historical-recipes/reused-sources.json',{'sources':refs,'note':'Exact prior committed sources reused; not copied into this packet. One-off execution recipes, not safe blind replay tools.'})
# Public static output replaces path banners only; private originals and exact command receipts stay archived.
static=S/'video-r7-static-logger';receipt=read(static/'receipt.json');pub=[]
for row in receipt:
 assert row['rc']==0;raw=static/(row['name']+'.stdout');assert h(raw)==row['stdout_sha'];assert not (static/(row['name']+'.stderr')).read_bytes()
 if row['name'] in ['log-print','runtime-logger']:
  q=P/'static-logger'/(row['name']+'.stdout.sanitized.txt');q.parent.mkdir(parents=True,exist_ok=True);q.write_text(raw.read_text().replace(str(S),'$HOME/.local/share/westlake/toutiao-resume-20261019'))
 row['command']=[x.replace(str(S),'$HOME/.local/share/westlake/toutiao-resume-20261019') for x in row['command']];pub.append(row)
write(P/'static-logger/receipt.sanitized.json',{'commands':pub,'original_receipt_sha256':h(static/'receipt.json'),'sanitization':'Only local path prefix; no instruction edits. Raw originals in window archive.'})
proof=M/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r5/retry-r7/runtime-format-proof.json';write(P/'static-logger/main-format-proof-pin.json',{'path':str(proof.relative_to(M)),'sha256':h(proof)})
a=read(S/'video-r7-state-before/snapshot.json');z=read(S/'video-r7-state-restored/snapshot.json')
for x in [a,z]:assert x['capture_status']=='COMPLETE' and x['boot_stable'] and x['complete'] and not x['errors']
for k in ['plan_sha256','collection_sha256','labels','init_configs','selinux_enforce']:assert a[k]==z[k],k
write(P/'snapshot-review.json',{'snapshots':2,'targets_each':62,'labels_each':len(z['labels']),'plan_sha256':a['plan_sha256'],'collection_sha256':a['collection_sha256'],'labels_configs_selinux_equal':True,'before_sha256':h(S/'video-r7-state-before/snapshot.json'),'restored_sha256':h(S/'video-r7-state-restored/snapshot.json')})
pins=[]
for member in arc['members']:
 src=S/member
 for q in ([src] if src.is_file() else sorted(x for x in src.rglob('*') if x.is_file())):pins.append({'path':'$HOME/.local/share/westlake/toutiao-resume-20261019/'+str(q.relative_to(S)),'sha256':h(q),'bytes':q.stat().st_size})
write(P/'source-pins.json',{'archive':'archive/window-archive.json','files':pins,'full_raw_private':True,'full_environment_not_published':True})
results={'token':'video-1919-r7-final-packet','status':'CLOSED_NOT_PASSED_RESTORED','candidate_boot':close['candidate_boot'],'parent':'4979/6990','child':'6951/8704','playback':'NOT_PASSED_STATIC_COVER','audio':'UNKNOWN','actual_probe':'player print GOT exact d8ad+7548; property GOT shim; verbose1; callback_enabled0; logger exact libbase+1eff0; minimum1','registered_chain':'libbase std::function -> exact runtime8ab+1b2fa4 HiLogLogger','downstream':'runtime HiLogPrint GOT1cc0f0 UNOBSERVED; two libhilog map groups sameinode do not determine provider; chromium/domain output is not player-call evidence','minimum':'slot1; exact d8ad is_loggable maps1 to INFO4; get_minimum_priority GOTd4a0 not sampled','FILE_sink':'player FILE*478e28 not sampled','native_property_read':'OBSERVED_TRUE_BRIDGE_LOG_LINE'+str(hits[0][0]),'restored_boot':close['restored_boot'],'restored_parent':'4897/6888','restored_child':'7422/8420 seq1','restored_feed_sha256':close['feed_sha256'],'restored_feed':'INDEPENDENTLY_VISUALLY_CONFIRMED','original_SHA_private_inode_compat_absence_cfg_parameter106':'VERIFIED','compat_parent_unmapped':'not asserted; no parent maps check in baseline-final','same_plan_snapshot':'COMPLETE62targets351labels; collection/labels/configs/SELinux equal','unlock':close['unlock_line'],'window_seconds':833,'archive_sha256':arc['archive_sha256'],'archive_bytes':arc['bytes'],'archive_remote_verified':True,'reviewer_device_calls':0,'new_builds':0,'historical315_changed':False}
write(P/'results.json',results)
(P/'README.md').write_text('''# R7 native logging bindings: static cover, restored\n\nThe unchanged r4 four-file tuple and temporary true parameter reached a real feed on candidate boot904a55b5. One video tap600,1590 produced the same cover at all three samples; t20/t25 bytes are identical. No dynamic playback or audio success. P1 remains NOT_PASSED. Child6951/b8704, parent4979/b6990 survived the before/after log collection.\n\nThe actual8slot probe binds player5f and liblogd8ad SHA/dev/inode to their stable mappings. Player print GOT reaches liblog+7548; property GOT reaches the identified shim; verbose=1, callback_enabled=0, logger points into libbase and minimum=1. Additional pointer reads and actual file identities close the registered std::function chain to runtime8ab HiLogLogger. This is registration/binding evidence, not a player emission trace. The runtime HiLogPrint GOT was not sampled, and libhilog has two separate mapped instances. Do not substitute chromium/C00f00 output for this missing caller-specific proof.\n\nExact runtime format is [%s:%u] %s, not public-format annotated; file/line/message argument placement and severity5/6 fatal-only stderr branch follow actual ELF. Current minimum1 is interpreted as INFO4 by the exact d8ad body; the final accessor GOT was not sampled. Native property true was actually read and flag1 sampled; missing log text does not prove prepare/dataSource never executed. Full environment is not included. Next-observation and feasibility files are static proposals only; no new implementation/admission is included.\n\nRollback binds this window's original apply-plan and restores run/media/player physical/private SHA+inode, compat absence, cfg91e31 and freshboot71849ac6 parameter106. Both snapshots COMPLETE, same62targets/351labels and equal collection/labels/configs/SELinux. The first restored icon is initially IMEhost; later same seq1 child7422/b8420 parent4897/b6888 has the independently viewed real feed11671a14. No zero-delay or future-stability claim. UNLOCK22:39:03 closes13m53s.\n\nRaw window archivec3b9073a,7,452,482bytes is remotely verified. Big logs, full maps and exact private receipts remain there; source-pins hashes all original members. Public screenshot bytes are exact, derived record paths are portable and original-record SHA is retained. New read-only scripts are preserved; unchanged r6 recipes are referenced by exact committed SHA instead of copied. Intermediate checkpoints remain historical; results.json is final. facts.txt from the proper parent record layout is the only screenshot/alive count authority. API adds observation7 only, preserving old6 objects and historical315.\n''')
proc=subprocess.run(['python3',str(M/'scripts/lab/run_facts.py'),str(P)],capture_output=True,text=True);assert proc.returncode==0
(P/'facts.txt').write_text(proc.stdout);(P/'facts.stderr.txt').write_text(proc.stderr);write(P/'facts-command.json',{'argv':['python3','$MAIN/scripts/lab/run_facts.py',str(P.relative_to(R))],'rc':proc.returncode,'tool_sha256':h(M/'scripts/lab/run_facts.py')})
# Original renderer, one new observation. No copied historical payload trees.
base=read(M/A/'observations.json');assert len(base['rows'])==6;new=json.loads(json.dumps(base));new['as_of']='2026-10-19T22:39:03+08:00'
def ref(path):
 q=R/path if path.startswith(str(P.relative_to(R))) else M/path
 return {'path':path,'sha256':h(q)}
row={'id':'OBS-20261019-PLAYER-R7','kind':'既有候选日志绑定只读观测（非新增公共API）','name':'TTPlayer实际日志GOT与注册回调链','status':'实际verbose=1与日志绑定已观测；静止封面，P1未通过；已回滚恢复feed','method':'复用r4四件及临时单键true；同PID/birth读8slots与注册链，核前后SHA/dev/inode/maps，实际tap及5/20/25秒截图。','platform':'61b/arm64，candidate boot904a55b5；本条不新增平台版本证明。','apps':'今日头条child6951/8704、parent4979/6990；tap600,1590进入视频页，三图同封面，t20/t25字节相同。','limitations':'链只闭合到runtime callback；HiLogPrint GOT未读，同inode两套libhilog映射不能选定provider。chromium/C00f00不是player调用证明。minimum1与exact函数INFO4语义不等于原调用返回值已跟踪；未见prepare正文不证明未执行。声音unknown；非两轮有声播放。','deployment':'按本轮原apply-plan回滚四件；原SHA/private inode、compat absent、cfg91e31、参数106和同plan快照均核。boot71849ac6首图标后child7422/8420 seq1最终真实feed，22:39:03解锁；早图仍IMEhost保留。','source':[ref(str(P.relative_to(R)/'historical-recipes/read_log_state.py')),ref(str(P.relative_to(R)/'historical-recipes/read_r7_chain.py')),ref(str(P.relative_to(R)/'historical-recipes/reused-sources.json'))],'build':[ref(str(B/'video-1919-r4-live-review/archive/build-artifacts-receipt.json'))],'evidence':[ref(str(P.relative_to(R)/x)) for x in ['results.json','admission.original.json','log-slots/reads.json','logger-chain/reads.json','logger-chain/files.original.txt','native-after/property-consumer.original-excerpt.txt','native-after/identity.json','play1/record.json','play1/t20.jpeg','checkpoint-logger-chain.json','restored-feed/screen.jpeg','restored-feed/identity.original.txt','parameter-restored/param-before.txt','snapshot-review.json','archive/window-close.json','archive/window-archive.json']],'frozen':False}
new['rows'].append(row);write(F/'api-row7.json',row)
with tempfile.TemporaryDirectory(prefix='r7-render-') as td:
 root=Path(td);dst=root/A;dst.mkdir(parents=True);copy(M/A/'render.py',dst/'render.py');write(dst/'observations.json',new)
 for rr in new['rows']:
  for group in ['source','build','evidence']:
   for item in rr[group]:
    rel=item['path'];src=R/rel if rel.startswith(str(P.relative_to(R))) else M/rel;assert h(src)==item['sha256'];copy(src,root/rel)
 copy(M/'benchmark/2026-10-14-api-source-delivery/views/index.html',root/'benchmark/2026-10-14-api-source-delivery/views/index.html')
 run=subprocess.run(['python3',str(dst/'render.py')],capture_output=True,text=True);(F/'renderer.stdout.txt').write_text(run.stdout);(F/'renderer.stderr.txt').write_text(run.stderr);assert run.returncode==0,run.stderr
 class Links(HTMLParser):
  def __init__(self):super().__init__();self.links=[]
  def handle_starttag(self,t,a):
   if t=='a':self.links.extend(v for k,v in a if k=='href')
 links=Links();links.feed((dst/'index.html').read_text());assert all((dst/u.split('#')[0]).is_file() for u in links.links)
 csvrows=list(csv.DictReader(io.StringIO((dst/'observations.csv').read_text(encoding='utf-8-sig'))));assert len(csvrows)==7
 for aa,bb in zip(csvrows,new['rows']):
  for k,v in bb.items():assert (json.loads(aa[k]) if isinstance(v,list) else aa[k])==(v if isinstance(v,list) else str(v)),k
 assert new['rows'][:6]==base['rows'];assert read(R/A/'observations.json')['rows']==base['rows']
 for n in ['observations.json','observations.csv','index.html','results.json']:copy(dst/n,R/A/n)
 write(F/'checks.json',{'renderer_rc':run.returncode,'renderer_sha256':h(M/A/'render.py'),'rows':7,'refs_by_row':[sum(len(rr[g]) for g in ['source','build','evidence']) for rr in new['rows']],'html_links':len(links.links),'all_links_resolved':True,'csv_all_fields_equal':True,'first_six_objects_unchanged':True,'historical315_modified':False,'prior_MAIN_observations_sha256':h(M/A/'observations.json'),'device_calls':0,'new_builds':0})
print(proc.stdout);print((F/'checks.json').read_text())
