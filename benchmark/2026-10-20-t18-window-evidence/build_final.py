#!/usr/bin/env python3
"""Freeze closed T18 evidence locally; no device commands or archive upload."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Read-only default. --write creates a fresh final packet.');return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';w=base/'t18-5cd-window-01';repo=ROOT.parent/'westlake-harness'
 ck=HERE/'checkpoint-01';old=json.loads((ck/'manifest.json').read_text())
 assert all(sha(ROOT/r['path'])==r['sha256'] for r in old['files'])
 close=json.loads((w/'close.json').read_text());assert close['status']=='CLOSED_RUNTIME_RESTORED_UI_NOT_RECOVERED' and close['unlocked'] and close['elapsed_seconds']<1800
 assert (w/'close-unlock.rc').read_text().strip()=='0' and (w/'close-held-after.rc').read_text().strip()=='1' and not (w/'close-held-after.stdout').read_bytes().strip()
 out=HERE/'final';out.mkdir(exist_ok=False);refs=[]
 def clean(s):
  for x,y in [(str(base),'BASE20'),(str(repo),'$WORKSPACES/westlake-harness'),(str(Path.home()),'$HOME')]:s=s.replace(x,y)
  return re.sub(r'/Users/[^/\s\"\']+','$RECORDED_SDK_BUILD_HOME',s)
 def dump(n,x):
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(clean(json.dumps(x,indent=2))+'\n')
 def cp(p,n):
  q=out/n;q.parent.mkdir(parents=True,exist_ok=True);b=p.read_bytes();q.write_bytes(b if p.suffix=='.jpeg' else clean(b.decode()).encode());refs.append(dict(raw_path='BASE20/'+str(p.relative_to(base)),raw_sha256=sha(p),raw_bytes=len(b),public_path=n,public_sha256=sha(q),byte_exact=b==q.read_bytes()))
 names=['close.json','human-audio-observation.json','final-snapshot-review.json','rollback-admission.json','rollback/plan.json','rollback/result.json','restored-retry-boot.json']+[p.name for p in sorted(w.glob('close-*'))]
 for n in names:cp(w/n,'receipts/'+n.replace('/','--')+('.txt' if n.endswith('.stderr') else ''))
 rb=json.loads((w/'rollback/result.json').read_text());assert rb['origin_apply_plan_sha256']==sha(w/'apply/plan.json') and (w/'rollback-exec.rc').read_text().strip()=='0'
 before=json.loads((w/'before-snapshot/snapshot.json').read_text());after=json.loads((w/'restored-snapshot/snapshot.json').read_text());fields=['plan_sha256','collection_sha256','bind_targets','init_configs','labels','sha','params','selinux_enforce'];eq={k:before[k]==after[k] for k in fields};assert all(eq.values())
 for s in [before,after]:assert s['complete'] and s['collection_complete'] and s['plan_target_count']==518 and len(s['labels'])==812
 assert after['boot_id']==close['boot']
 supp=[]
 for name in ['before-supplement','restored-supplement']:
  d=w/name;r=json.loads((d/'result.json').read_text());assert r['rc']==0 and r['targets']==26
  for n,pin in r['raw'].items():assert sha(d/n)==pin['sha256'] and (d/n).stat().st_size==pin['bytes']
  b=(d/'stdout.raw').read_bytes();assert b.startswith(b'T16_SUPPLEMENT_BOOT ') and b.endswith(b'T16_SUPPLEMENT_COMPLETE\n');supp.append(b)
 assert supp[0].split(b'\n',1)[1]==supp[1].split(b'\n',1)[1]
 dump('restoration-comparison.json',dict(scope='518 main targets / 812 labels plus 26 supplement targets',equal=eq,supplement26_equal_except_boot_line=True,before_sha256=sha(w/'before-snapshot/snapshot.json'),after_sha256=sha(w/'restored-snapshot/snapshot.json'),raw_boot_pid_uptime_not_required_equal=True))
 # Preserve the mistaken media path and subsequent exact-path correction separately.
 for stem in ['shell-1792462382507923000','shell-1792462396287506000','shell-1792462363623983000']:
  assert (w/(stem+'.rc')).read_text().strip()=='0'
  for suffix in ['argv.json','rc','stdout','stderr']:cp(w/(stem+'.'+suffix),'restoration/'+stem+'.'+suffix+('.txt' if suffix=='stderr' else ''))
 wrong=(w/'shell-1792462382507923000.stdout').read_text();fixed=(w/'shell-1792462396287506000.stdout').read_text()
 assert 'No such file or directory' in wrong and 'PARENT_BIRTH 12101' in wrong
 for v in ['5a3aef638000e49f2a966b2179d57fe7628c29a4897921209fec539bd5dc1b79','d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b','b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02']:assert v in wrong
 assert 'fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9' in fixed and 'Timeout=10000ms  OverrideTimeout=10000ms' in fixed and 'errNum is:106!' in fixed
 # Publish only fixed technical lines from the baseline failure; complete raw remains private.
 fail=w/'shell-1792462230136109000.stdout';lines=[l for l in fail.read_text().splitlines() if 'MediaPlayer.native_init' in l];assert lines
 (out/'baseline-native-init-excerpt.txt').write_text('\n'.join(lines)+'\n');dump('baseline-native-init-source.json',dict(path='BASE20/'+str(fail.relative_to(base)),sha256=sha(fail),bytes=fail.stat().st_size,scope='Restored baseline splash path only; no random exit diagnosis'))
 audio=json.loads((w/'human-audio-observation.json').read_text());assert audio['audio']=='PASS_USER_CONFIRMED_CLIP_AUDIO' and audio['candidate_boot']=='6b99680b-3d15-476a-a229-dc3591e34add' and audio['candidate_bridge_sha256']=='dca530eb4b1b53e5dd0ecc41c36953f7463609c5b70bbdf67a49dc3cae17f9d9'
 im=w/close['restored_ui_screenshot'];meta=im.parent/'screenshot.json';assert sha(im)==json.loads(meta.read_text())['sha256'];cp(im,'images/restored-host.jpeg');cp(meta,'images/restored-host.json')
 dump('images/review.json',dict(sha256=sha(im),actual_image_read=True,verdict='WESTLAKE_IME_HOST_ONLY_NOT_FEED'))
 cmd=[sys.executable,str(repo/'scripts/lab/run_facts.py'),str(w)];r=subprocess.run(cmd,capture_output=True);assert r.returncode==0;(out/'facts.txt').write_bytes(r.stdout);(out/'facts.stderr.txt').write_bytes(r.stderr);dump('facts-receipt.json',dict(argv=[clean(x) for x in cmd],rc=0,helper_sha256=sha(repo/'scripts/lab/run_facts.py'),unmodified=True))
 dump('results.json',dict(token='t18-window-evidence-final',status=close['status'],approved_by=close['approved_by'],elapsed_seconds=close['elapsed_seconds'],restored_boot=close['boot'],runtime='ORIGINALS_RESTORED',restored_ui='HOST_ONLY_NOT_FEED',video='NOT_PASSED_STILL_COVER_ANW_MINUS19',audio=audio['audio'],audio_scope=audio['device_and_clip_binding'],audio_evidence='User audible observation, not instrumented audio test or getter-return proof',observer_samples=0,observer_host_cleanup=False,observer_outer_finally_cleanup=True,rollback_rc=0,snapshot_main_targets=518,supplement_targets=26,main_labels=812,power=[10000,10000],debug_parameter='ABSENT_ERR106',unlock_rc=0,held_after_rc=1,held_after_empty=True,checkpoint_manifest_sha256=sha(ck/'manifest.json'),archive='LOCAL_ARCHIVE_TO_PREPARE_REMOTE_PENDING',device_calls_by_lane=0))
 dump('public-source-index.json',refs)
 dump('raw-archive-allowlist.json',dict(base='BASE20',directories=['t18-5cd-window-01','t18-candidate-inputs'],files=[p.name for p in sorted(base.glob('t18*')) if p.is_file()],scope='All T18 window raw, failures/retries, original shell errors, observer/server crash and cleanup, restoration, audio human receipt and close; exact candidate inputs; no unrelated prior windows. Build and source-closure archives remain separate.'))
 for x in json.loads((ck/'packet-final/source-build-pins.json').read_text())['files']:
  blob=subprocess.check_output(['git','-C',str(repo),'show',x['commit']+':'+x['path']]);assert hashlib.sha256(blob).hexdigest()==x['sha256'];p=HERE/'.private/producer-snapshots'/x['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob)
 print(json.dumps(dict(status='FINAL_CREATED',device_calls=0)))
if __name__=='__main__':main()
