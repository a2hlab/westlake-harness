#!/usr/bin/env python3
"""Freeze candidate-only local evidence; never asserts window closure or calls devices."""
import argparse, hashlib, importlib.util, json, re, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
    if not a.write:print('Read-only default; --write creates a new candidate-only packet.');return
    base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';w=base/'t16-5cd-window-01';main=ROOT.parent/'westlake-harness'
    out=HERE/'packet';out.mkdir(exist_ok=False);refs=[]
    def clean(s):
        for x,y in [(str(base),'BASE20'),(str(main),'$WORKSPACES/westlake-harness'),(str(Path.home()),'$HOME')]:s=s.replace(x,y)
        return s
    def dump(n,x):
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(clean(json.dumps(x,indent=2))+'\n')
    def copy(p,n):
        q=out/n;q.parent.mkdir(parents=True,exist_ok=True);raw=p.read_bytes();q.write_bytes(raw if p.suffix=='.jpeg' else clean(raw.decode()).encode())
        refs.append(dict(raw_path='BASE20/'+str(p.relative_to(base)),raw_sha256=sha(p),raw_bytes=len(raw),public_path=n,public_sha256=sha(q),byte_exact=q.read_bytes()==raw))
    profile=json.loads((w/'candidate-profile/profile.json').read_text());apply=json.loads((w/'apply/result.json').read_text());admission=json.loads((w/'admission-r3.json').read_text())
    assert (w/'apply.rc').read_text().strip()=='0' and apply['executor_sha256']==admission['executor_sha256']=='05099f6cdd68ca9903833ca88a1748803b69d28e79a493f8c573c4fffee3884b'
    assert profile['boot']=='62f810ad-8ae9-45b8-aad6-c44f1ea89e17' and profile['child']['pid']==8151 and profile['child']['birth']==17437
    for n in ['context.json','admission.json','admission-r3.json','apply/plan.json','apply/result.json','apply/run-normalization.json','apply.rc','candidate-boot.json','candidate-profile/profile.json','candidate-normal-icon/record.json','candidate-observation/state.json']:
        copy(w/n,'evidence/'+n.replace('/','--'))
    # Preserve all three known refusal/failure chains, without publishing large logs.
    for stem in ['preflight','preflight-r3','observe-capture-1792456885318447000']:
        for suffix in ['argv.json','rc','stdout','stderr']:
            p=w/(stem+'.'+suffix)
            if p.exists():copy(p,'failures/'+p.name+('.txt' if suffix=='stderr' else ''))
    for stem in ['t16-before-snapshot-exec','t16-before-snapshot-v2-exec']:
        for suffix in ['argv.json','rc','stdout','stderr']:copy(base/(stem+'.'+suffix),'failures/'+stem+'.'+suffix+('.txt' if suffix=='stderr' else ''))
    images=[]
    selected=[('capture-1792456763279434000','NEWS_FEED'),('candidate-observation/1792456805398556000-begin','NEWS_FEED'),('candidate-observation/1792456818897493000-ui','WRONG_OLD_TAB_COORDINATE_NOVEL_PAGE'),('candidate-observation/1792456846285289000-ui','BOTTOM_VIDEO_CORRECTION_VIDEO_COVER'),('capture-1792456927713296000','SAME_COVER_SUBJECT_NAVIGATION_COMMENT_UI_CHANGED')]
    for i,(name,visual) in enumerate(selected,1):
        p=w/name/'screen.jpeg';meta=w/name/'screenshot.json';m=json.loads(meta.read_text());assert m['sha256']==sha(p)
        copy(p,f'images/{i:02}.jpeg');copy(meta,f'images/{i:02}.json')
        images.append(dict(source=name,sha256=sha(p),captured_at=m['captured_at'],independent_visual_review=visual))
    assert images[0]['sha256'].startswith('28c00029') and images[-2]['sha256'].startswith('95cfd24a') and images[-1]['sha256'].startswith('7c0d1604')
    dump('images/index.json',dict(images=images,video='NOT_PROVEN',audio='UNKNOWN',same_subject_pair=[4,5],jpeg_bytes_equal=False,note='UI changes do not prove moving video.'))
    cmd=[sys.executable,str(main/'scripts/lab/run_facts.py'),str(w)];r=subprocess.run(cmd,capture_output=True);assert r.returncode==0
    (out/'facts.txt').write_bytes(r.stdout);(out/'facts.stderr.txt').write_bytes(r.stderr)
    dump('facts-receipt.json',dict(argv=[clean(x) for x in cmd],rc=r.returncode,helper_sha256=sha(main/'scripts/lab/run_facts.py'),note='Original record scan at checkpoint. Most capture producers emit screenshot.json, not record.json. The five reviewed JPEGs are individually bound; no synthetic record or alive count.'))
    prefix=w/'candidate-full-log-prefix';pr=json.loads((prefix/'result.json').read_text());tr=json.loads((prefix/'transport.json').read_text());raw=(prefix/'selected.raw').read_bytes()
    assert len(raw)==pr['selected_bytes']==30236818 and sha(prefix/'selected.raw')==pr['sha256']=='4e32d9d54f571e854d62acd55bededc43b31ed165c1ffca597f02d4ef39783df'
    decoder=main/'benchmark/2026-10-20-t14-fixed-range-read/read_range.py';spec=importlib.util.spec_from_file_location('t16_original_frame',decoder);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    framed=(prefix/'stdout.raw').read_bytes();token=re.match(rb'T15_BEGIN_([a-f0-9]{32}):',framed).group(1).decode()
    assert m.decode(framed,m.plan(0,len(raw)),token,tr['rc'],tr['timed_out'])==raw
    patterns=[b'JNI_OnLoad,188',b'TTPlayer',b'ret:-97',b'err:-97',b'SL_IID',b'[WL-TTLOG ']
    counts={p.decode():{'literal_count':raw.count(p),'first_byte_offset':raw.find(p)} for p in patterns}
    assert counts['ret:-97']['literal_count']==7 and counts['TTPlayer']['literal_count']==2 and counts['SL_IID']['literal_count']==0
    safe=[]
    for tokenline in [b'libttplayer.cpp,JNI_OnLoad,188',b'tt_player.cpp,TTPlayer,194']:
        for line in raw.splitlines():
            if tokenline in line:
                start=line.find(b'[WL-TTLOG ');assert start>=0
                safe.append(line[start:].decode(errors='replace'))
    (out/'player-safe-excerpt.txt').write_text('\n'.join(safe)+'\n')
    copy(prefix/'result.json','evidence/fullprefix-result.json')
    dump('prefix-check.json',dict(status='FIXED_PREFIX_COMPLETE',source_start=0,source_end=len(raw),sha256=sha(prefix/'selected.raw'),decoder_sha256=sha(decoder),transport_sha256=sha(prefix/'transport.json'),transport_rc=tr['rc'],timed_out=tr['timed_out'],counts=counts,player_JNI_OnLoad_token_byte_offset=raw.find(b'JNI_OnLoad',16800000),mirror_two_hop_binding='NOT_MEASURED',iid_absence_scope='Only literal SL_IID in this captured prefix; not a global absence or playback verdict.',same_inode_does_not_prove_content_immutability=True,media_URLs_public=False))
    snapshot=json.loads((base/'t16-before-snapshot-v2/snapshot.json').read_text());supp=json.loads((base/'t16-before-supplement/result.json').read_text());scope=main/'benchmark/2026-10-20-t16-snapshot-scope/results.json';sc=json.loads(scope.read_text())
    assert snapshot['complete'] and snapshot['collection_complete'] and snapshot['plan_target_count']==518
    assert supp['status']=='SUPPLEMENT_BYTES_COMPLETE' and supp['rc']==0 and supp['targets']==26 and supp['boot']==snapshot['boot_id']
    assert sc['original_target_count']==544 and sc['coverage_union_equals_original'] and sc['intersection_empty']
    dump('snapshot-scope.json',dict(original_targets=544,supported_targets=518,supplement_targets=26,union_equals_original=True,intersection_empty=True,snapshot_sha256=sha(base/'t16-before-snapshot-v2/snapshot.json'),supplement_receipt_sha256=sha(base/'t16-before-supplement/result.json'),scope_source=str(scope.relative_to(main)),scope_source_sha256=sha(scope),before_boot=snapshot['boot_id'],collection_sha256=snapshot['collection_sha256'],plan_sha256=snapshot['plan_sha256'],status='BEFORE_ONLY_NOT_RESTORE_VERIFICATION',note='5cd scope. Not the 61b 64-target plan.'))
    reuse='benchmark/2026-10-20-t15-player-load-reuse/';r8='benchmark/2026-10-19-toutiao-video-playback/candidate-r8/'
    source_paths=[reuse+n for n in ['executor.py','parameters.json','executor-source-pins.json','candidate-inputs.json','reused-source-pins.json','run5cd.after.wid29.reference.sh']]
    source_paths += [r8+n for n in ['candidate.json','archive-receipt.json','ttplayer_log_mirror.c','derive_ttmplayer_logmirror.py','build_candidate.sh','evidence/r8-build-outer-2329/execution.rc.sanitized.txt','evidence/r8-build-outer-2329/build/abi-comparison.json.sanitized.txt']]
    source_paths += ['benchmark/2026-10-19-toutiao-video-playback/candidate-r3/derive_mffmpeg.py','benchmark/2026-10-20-t14-play-observation/observe.py','benchmark/2026-10-20-t14-fixed-range-read/read_range.py','benchmark/2026-10-20-t16-snapshot-scope/results.json']
    pins=[]
    for rel in source_paths:
        p=main/rel;commit=subprocess.check_output(['git','-C',str(main),'log','-1','--format=%H','--',rel],text=True).strip();blob=subprocess.check_output(['git','-C',str(main),'show',commit+':'+rel]);assert blob==p.read_bytes()
        pins.append(dict(path=rel,commit=commit,sha256=sha(p)))
    assert pins[0]['sha256']==apply['executor_sha256'];candidate=json.loads((main/r8/'candidate.json').read_text())
    assert candidate['artifacts']['libttmplayer.so']==apply['player_after_sha'] and candidate['artifacts']['libopensles_android_compat.so']==apply['dso_sha']
    dump('source-build-pins.json',dict(execution_source_commit='e30cb618f91026934939691c42f0c796790b07ce',sources=pins,artifacts={k:apply[k] for k in ['after_sha','dso_sha','media_after_sha','player_after_sha']},build='Reused R8 exact outputs and existing raw build archive; no new build. Provider binding is not inferred from static build acceptance.'))
    helperpins=[]
    for p in sorted(base.glob('t16_*.py')):
        copy(p,'execution-source/'+p.name);helperpins.append(dict(path='BASE20/'+p.name,sha256=sha(p)))
    # Exact bounded allowlist for the later full raw archive. Closure is required separately.
    dirs=['t16-5cd-window-01','t16-before-snapshot-v2','t16-before-supplement']
    files=[p.name for p in sorted(base.glob('t16-before-snapshot*exec.*'))]+['t16-candidate-player-initial-read.txt','t16-candidate-current-read.txt']+[p.name for p in sorted(base.glob('t16_*.py'))]
    dump('raw-archive-allowlist.json',dict(base='BASE20',directories=dirs,files=files,excludes='Unrelated previous windows/trees; final restore additions require explicit follow-up.',archive_status='NOT_CREATED_WINDOW_PENDING'))
    index=[]
    for dirname in dirs:
        for p in sorted((base/dirname).rglob('*')):
            if p.is_file():index.append(dict(path='BASE20/'+str(p.relative_to(base)),sha256=sha(p),bytes=p.stat().st_size))
    for n in files:
        p=base/n;index.append(dict(path='BASE20/'+n,sha256=sha(p),bytes=p.stat().st_size))
    private=HERE/'.private';private.mkdir(exist_ok=True)
    full=private/'raw-index-at-checkpoint.json';full.write_text(json.dumps(index,indent=2)+'\n')
    dump('raw-index-at-checkpoint.json',dict(status='PRIVATE_COMPLETE_INDEX',files=len(index),sha256=sha(full),bytes=full.stat().st_size,persistent_path='LANE/'+str(full.relative_to(ROOT)),public_evidence_index='public-source-index.json'))
    dump('public-source-index.json',refs)
    dump('results.json',dict(token='t16-window-evidence',status='CANDIDATE_CHECKPOINT_NOT_CLOSED',approved_by=admission['approved_by'],candidate_apply_rc=0,boot=profile['boot'],child=profile['child'],parent=profile['parent'],feed_sha256=images[0]['sha256'],video='NOT_PROVEN',audio='UNKNOWN',mirror_two_hop_binding='NOT_MEASURED',before_targets='544 = 518 + 26',T14_power_restore_scope='Only its window-entry value [10000,86400000], not final baseline power.',baseline_restore='PENDING',final_feed='PENDING',unlock='PENDING',archive='PENDING',device_calls_by_review=0))
    print(json.dumps(dict(status='CANDIDATE_CHECKPOINT_CREATED',images_reviewed=len(images),raw_files_indexed=len(index),device_calls=0)))
if __name__=='__main__':main()
