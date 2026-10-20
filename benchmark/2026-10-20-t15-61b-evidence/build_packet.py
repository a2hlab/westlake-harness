#!/usr/bin/env python3
"""Package closed local evidence only. --write is explicit; no device execution."""
import argparse, hashlib, importlib.util, json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');ap.add_argument('--main',type=Path,default=ROOT.parent/'westlake-harness');a=ap.parse_args()
    if not a.write: print('Read-only default. --write creates a fresh packet.');return
    base=Path.home()/'.local/share/westlake/toutiao-resume-20261020'
    out=HERE/'packet';out.mkdir(exist_ok=False);refs=[]
    def clean(t):
        for x,y in [(str(base),'BASE20'),(str(a.main.resolve()),'$WORKSPACES/westlake-harness'),(str(Path.home()),'$HOME')]:t=t.replace(x,y)
        return t
    def dump(n,v):
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(clean(json.dumps(v,indent=2,ensure_ascii=False))+'\n')
    def cp(p,n):
        q=out/n;q.parent.mkdir(parents=True,exist_ok=True);raw=p.read_bytes();data=raw if p.suffix=='.jpeg' else clean(raw.decode()).encode();q.write_bytes(data)
        refs.append(dict(raw_path='BASE20/'+str(p.relative_to(base)),raw_sha256=sha(p),raw_bytes=len(raw),public_path=n,public_sha256=sha(q),byte_exact=raw==data))
    ui=base/'61b-r2-ui-window-01';closed=json.loads((ui/'close.json').read_text())
    assert closed['approved_by']=='outer(codex)' and closed['actual_icon_clicks']==1 and closed['runtime_or_cfg_deployments']==0 and closed['controlled_app_term']==0
    assert closed['guardian_left_running'] and closed['board_lock_released'] and (ui/'unlock.rc').read_text().strip()=='0'
    profile=json.loads((ui/'profile.json').read_text());authority=json.loads((ui/'state/authority.json').read_text())
    assert authority['profile_sha256']==sha(ui/'profile.json')
    images=[]
    for name,visual in [('prepare','DESKTOP'),('launch','IMEHOST_INITIAL_SCREEN'),('after-launch','NEWS_FEED')]:
        record=json.loads((ui/'state'/name/'record.json').read_text());image=ui/'state'/name/'screen.jpeg'
        assert len(record['screenshots'])==1 and record['screenshots'][0]['captured'] is True and record['screenshots'][0]['sha256']==sha(image)
        assert record['profile_sha256']==sha(ui/'profile.json')
        cp(image,'61b/screenshots/'+name+'.jpeg');cp(ui/'state'/name/'record.json','61b/records/'+name+'.json')
        images.append(dict(source='state/'+name,sha256=sha(image),visual=visual))
    assert images[-1]['sha256']==closed['feed_sha256']=='93413897f0dc3fbf6e5c006eea164b7c8bd181523af2c571b62314ca0f685880'
    launch=json.loads((ui/'state/launch/record.json').read_text());assert launch['clicked'] is True
    final=(ui/'final-identity/stdout').read_text();assert final.rstrip().endswith('READ_COMPLETE')
    for text in ['15128 (id.article.news) S 6101','714345','seq=3 child=15128 child_birth=714345 parent=6101 parent_birth=16617 reason=reentry_spawn_ok','reason=process_exit first_read_exited','Timeout=30000ms  OverrideTimeout=86400000ms']:assert text in final,text
    for n in ['close.json','profile.json','state/authority.json','state/preflight/record.json','state/restore/record.json','state/launch.intent.json','state/icon-dispatch.intent.json','final-identity/stdout','final-identity/stderr','final-identity/rc','unlock.rc','held-after.txt']:
        cp(ui/n,'61b/evidence/'+n.replace('/','--')+('.txt' if n.endswith('/stderr') else ''))
    for n in ['preflight/commands/command-00009.stdout.txt','restore/commands/command-00014.stdout.txt']:
        p=ui/'state'/n;assert 'Timeout=30000ms  OverrideTimeout=86400000ms' in p.read_text();cp(p,'61b/evidence/'+n.split('/')[0]+'-power.txt')
    actions=[]
    for f in sorted(ui.glob('*outer-*.argv.json')):
        stem=f.name.removesuffix('.argv.json');rc=int((ui/(stem+'.rc')).read_text());assert rc==0
        actions.append(dict(argv_path='BASE20/'+str(f.relative_to(base)),argv_sha256=sha(f),rc=rc))
        cp(ui/(stem+'.rc'),'61b/outer-actions/'+stem+'.rc')
    cmd=[sys.executable,str(a.main/'scripts/lab/run_facts.py'),str(ui/'state')];r=subprocess.run(cmd,capture_output=True);assert r.returncode==0
    (out/'61b/facts.txt').write_bytes(r.stdout);(out/'61b/facts.stderr.txt').write_bytes(r.stderr)
    dump('61b/facts-receipt.json',dict(argv=[clean(x) for x in cmd],rc=r.returncode,helper_sha256=sha(a.main/'scripts/lab/run_facts.py'),note='Original record-based counts; no inferred liveness. Exact identity evidence is separate.'))
    dump('61b/screenshot-index.json',images)
    dump('61b/results.json',dict(token='t15-61b-evidence-final',status='SCOPED_NORMAL_ICON_FEED_VERIFIED',approved_by=closed['approved_by'],approval_source='evidence/close.json',duration_seconds=closed['duration_seconds'],boot=closed['boot'],parent=closed['parent'],guardian=closed['guardian'],guardian_left_running=True,old_child=closed['old_child'],new_child=closed['new_child'],actual_icon_clicks=1,source_cfg_sha256=profile['cfg_sha256'] if 'cfg_sha256' in profile else profile.get('cfg_sha'),runtime_deployments=0,controlled_term=0,power_restored=closed['power_restored'],unlock_rc=0,random_crash_fix=False,video='UNVERIFIED',future_uptime='UNKNOWN',outer_actions=actions))
    w1=base/'t15-5cd-range-window-01';w2=base/'t15-5cd-range-window-02'
    c1=json.loads((w1/'close.json').read_text());c2=json.loads((w2/'close.json').read_text())
    assert c1['status']=='LOCAL_PIN_REFUSAL_ZERO_DEVICE_COMMANDS' and not (w1/'range').exists()
    assert (w1/'outer.rc').read_text().strip()=='1' and (w1/'unlock.rc').read_text().strip()=='127' and (w1/'unlock-corrected.rc').read_text().strip()=='0'
    assert c2['lock_released'] and (w2/'outer.rc').read_text().strip()=='0' and (w2/'unlock.rc').read_text().strip()=='0'
    for name,w in [('window-01',w1),('window-02',w2)]:
        for f in sorted(w.iterdir()):
            if f.is_file() and (f.name=='close.json' or f.suffix=='.rc' or f.name in ['outer.stderr','unlock.stderr','unlock-corrected.stderr','held-after.stdout','held-after.txt']):
                cp(f,'t15/'+name+'/'+f.name+('.txt' if f.suffix=='.stderr' else ''))
    raw=w2/'range';result=json.loads((raw/'result.json').read_text());transport=json.loads((raw/'transport.json').read_text())
    assert result['status']=='FIXED_RANGE_BYTES_COMPLETE'
    for name,pin in result['files'].items():assert sha(raw/name)==pin['sha256'] and (raw/name).stat().st_size==pin['bytes'],name
    source=a.main/'benchmark/2026-10-20-t14-fixed-range-read/read_range.py'
    spec=importlib.util.spec_from_file_location('t15_original_decoder',source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    decoded=mod.decode((raw/'stdout.raw').read_bytes(),result['plan'],result['token'],transport['rc'],transport['timed_out'])
    assert decoded==(raw/'selected.raw').read_bytes() and len(decoded)==30863473
    assert sha(raw/'selected.raw')==result['sha256']=='87be9dffb8d5d9a2607308be2a8b053459161e4369938a6393cde99263d5ee8d'
    cp(raw/'result.json','t15/window-02/range-result.json')
    dump('t15/range-check.json',dict(status='FIXED_RANGE_BYTES_COMPLETE',decoder_sha256=sha(source),source_offset=result['source_offset'],selected_bytes=len(decoded),selected_sha256=result['sha256'],transport_rc=transport['rc'],timed_out=transport['timed_out'],transport_sha256=sha(raw/'transport.json'),duration_seconds=c2['duration_seconds'],public_payload=False,interpretation_owner='native video_plan; separate safe excerpts',first_fatal='NOT_REINTERPRETED_IN_THIS_PACKET',device_application_writes=0,device_scratch='Producer uses bounded diagnostic scratch; not zero total device writes.',whole_log=False))
    sources=[]
    rels=['benchmark/2026-10-20-61b-permanent-reentry-ui/ui.py','benchmark/2026-10-20-t14-fixed-range-read/read_range.py','benchmark/2026-10-20-t14-fixed-range-read/source-pins.json','scripts/lab/run_facts.py']
    rels+=list(json.loads((a.main/rels[2]).read_text()))
    for rel in sorted(set(rels)):
        p=a.main/rel;commit=subprocess.check_output(['git','-C',str(a.main),'log','-1','--format=%H','--',rel],text=True).strip()
        blob=subprocess.check_output(['git','-C',str(a.main),'show',commit+':'+rel]);assert blob==p.read_bytes()
        sources.append(dict(path=rel,commit=commit,sha256=sha(p)));dst=HERE/'.private/producer-snapshots'/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(blob)
    for n in ['61b_ui_run.py','61b_ui_read.py','t15_run_window2.py']:cp(base/n,'execution-source/'+n)
    dump('source-pins.json',dict(sources=sources,runtime_build='NONE',scope='Historical execution recipes, not a fresh authorization or generic rerun tool.'))
    index=[]
    for w in [ui,w1,w2]:
        for p in sorted(w.rglob('*')):
            if p.is_file():index.append(dict(path='BASE20/'+str(p.relative_to(base)),sha256=sha(p),bytes=p.stat().st_size))
    dump('raw-index.json',index);dump('public-source-index.json',refs)
    print(json.dumps(dict(status='PACKET_CREATED',device_calls=0,raw_files=len(index),public_sources=len(refs))))
if __name__=='__main__':main()
