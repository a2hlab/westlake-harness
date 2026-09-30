#!/usr/bin/env python3
"""Reviewed U2 triage, descriptive U0 comparison; no frozen forecast mutation."""
import csv,json,re
from collections import Counter,defaultdict
from pathlib import Path
from extract import HERE,ROOT,SOURCE,sha,dump
# key: cluster, layer, batch, certainty, comparison to exact U0 first checkpoint, explanation
GROUPS=[
('N3-namespace','native','N3','high',[
 ('fd-fluffychat','miss','Flutter private libandroid now needs invisible liboh_android_runtime.so; prior first wall was libandroid itself.'),
 ('fd-kitchenowl','miss','Flutter private libandroid now needs invisible liboh_android_runtime.so.'),
 ('localsend','miss','Flutter private libandroid now needs invisible liboh_android_runtime.so.'),
 ('burgerking','miss','__register_atfork no longer first; libreactnative now cannot load libandroid.so.'),
 ('fd-organicmaps','miss','Prior GLES dependency is superseded by libandroid.so dependency.'),
 ('mcdonalds','miss','Prior liblog dependency is superseded by libandroid.so dependency.'),
 ('ppsspp','hit','Caught libGLESv2 load failure remains first failed checkpoint; later RenderThread SIGSEGV is the first terminating signal, crash stack unavailable.')]),
('N3-property','native','N3','high',[
 ('fd-libre','miss','Flutter advances from GLES library lookup to __system_property_find symbol lookup.'),
 ('fd-saber','miss','Flutter advances from GLES library lookup to __system_property_find symbol lookup.')]),
('N3-eglimpl','native','N3','high',[
 ('fd-app','miss','Unciv advances from libgdx/libstdc++ dependency to EGLImpl._eglGetDisplay JNI.'),
 ('fd-shatteredpixeldungeon','miss','GLImpl initialization advances; EGLImpl._eglGetDisplay is now missing. Earlier libgdx still cannot see libstdc++.so; error Activity does not count as lit.')]),
('N3-jna-resource','native','N3','high',[
 ('firefox','hit','libjnidispatch resource-path lookup still fails; errno export alone does not establish JNA resource discovery.'),
 ('fd-fennec_fdroid','hit','libjnidispatch resource-path lookup still fails.')]),
('N3-opensles','native','N3','high',[
 ('mindustry','miss','libOpenSLES lookup advances to unresolved slCreateEngine import in libarc.')]),
('N3-webview','native','N3','medium',[
 ('fd-tutanota','hit','WebViewFactory.getProvider throws UnsupportedOperationException; full provider/runtime closure spans Java/native, N3 integration owner.')]),
('N3-theme-projection','资源','N3','high',[
 ('vlc','miss','U0 first fatal was AudioSystem JNI, with this resource wall already observed on a later PID. Theme.VLC.Transparent attribute 0x7f040072/index13 remains unresolved. Owner follows outer N3 resource-projection assignment; not an audio JNI first wall this run.')]),
('J4-boot-api','JAR','J4','high',[
 ('fd-feeder','hit','NetworkRequest.getNetworkSpecifier missing in adapter-mainline-stubs.jar.'),
 ('fd-plus','miss','SoundPool is no longer first; NetworkInfo.getState missing in adapter-mainline-stubs.jar.'),
 ('x','hit','NetworkCapabilities.getLinkUpstreamBandwidthKbps still missing.'),
 ('wikipedia','miss','First fatal is now TagSoup.Parser.setProperty, not EGL. Library appears in adapter-mainline-stubs.jar.'),
 ('fd-gallery','hit','MediaStore.Images.Media.EXTERNAL_CONTENT_URI remains missing despite another app PID surviving.')]),
('J4-null-producer','JAR','J4','low',[
 ('fd-catima','hit','ListWidget.updateAll getClass NPE repeats. Null producer unknown; J4 investigation assignment, not proof of widget-service root cause.'),
 ('fd-breezyweather','hit','pa0.G -> zt construction getClass NPE repeats; null producer unknown.'),
 ('fd-wifianalyzer','hit','MainActivity.onCreate:78 getClass NPE repeats; null producer unknown. Shared exception shape is not proof of one shared repair.')]),
('J4-restrictions','JAR','J4','medium',[
 ('fd-meet','miss','resolveRestrictions now dereferences null Collection.iterator, after prior RestrictionsManager-null wall. Exact collection producer not logged.')]),
('J4-haptics','JAR','J4','high',[
 ('fd-reader','miss','SystemVibratorManager.getVibratorIds:66 monitor-enter null; prior failure was null array in SystemVibrator.getInfo. Object initialization must be complete.')]),
('J4-mediarouter','JAR','J4','high',[
 ('noice','miss','IMediaRouterService null at registerClientAsUser is the main-thread fatal, not EGL/native audio in this observation.')]),
('J4-tls-java','JAR','J4','high',[
 ('fd-client','miss','Application bind reaches WestlakeSSLContextSpi.engineCreateSSLEngine:45 -> UnsupportedOperationException; real SSLEngine needed.'),
 ('fd-noice','unknown','No startup fatal; background SoundRepository/SubscriptionRepository threads die on missing android.net.ssl.SSLSockets. White UI causality unproved; secondary blocker only.')]),
('J4-alias-theme','资源','J4','high',[
 ('fd-api','hit','Theme.AppCompat contract still fails; J3 already targets alias/theme, await its separate receipt before duplicating repair.')]),
('J4-media-session','JAR','J4','high',[('fd-musicplayer','hit','Failed to resolve SessionToken for PlaybackService remains first; query/manifest service projection requires closure.')]),
('J4-sentry','JAR','J4','medium',[
 ('fd-im-vector-app','hit','Sentry provider DSN validation still aborts bind; metadata/projection hypothesis retained, no claim that app is mispackaged.')]),
('J4-verifier-interface','JAR','J4','medium',[
 ('fd-immich','hit','Same unresolved d7.c verifier failure before Flutter. Prior addendum NSD interface absence is a candidate only; current U2 class loading has not been proved.')]),
('J4-intent-contract','JAR','J4','medium',[
 ('opencamera','miss','DrawPreview.drawUI:2351 dereferences null Intent.getIntExtra; no current audio JNI first fatal. Determine Intent producer before patching.')]),
('J4-cache-input','JAR','J4','low',[
 ('fd-libretube','unknown','DiskCache.Builder.maxSizeBytes rejects size<=0 during Application.onCreate; U0 was interrupted, so no comparable U0 first wall. r17r addendum had this wall; producer still unknown.')]),
('N3-no-fatal-observation','平台','N3','low',[
 ('fd-uhabits','unknown','No fatal in sweep; externally signed same-state reruns light 1/3. Diagnose intermittent rendering, not deterministic regression.'),
 ('fd-mobile','unknown','No fatal; alive and not outer-signed lit. Rendering/lifecycle diagnosis only, no specific native defect established.'),
 ('termux','unknown','No fatal; finishActivity rc0 then alive/white. Native owner is investigation routing, not cause proof.'),
 ('fd-AppManager','unknown','No fatal; finishActivity rc0 and app PID alive. Loopback/authentication hypothesis belongs to existing cc-wiki probe, not established by this sweep.')]),
('INPUT-assembly','app 打包','input','high',[
 ('fd-seal','hit','Host preflight rejects non-AArch64 libaria2c.zip.so; no on-board fatal.'),
 ('toutiao','hit','Host preflight rejects ELF32 libcvt.so; no on-board fatal.'),
 ('subwaysurfers','hit','Host pinned APK SHA mismatch; input identity rejection, not runtime failure.')]),
]

def csvout(name,rows):
 with (HERE/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
def main():
 evidence=json.loads((HERE/'evidence.json').read_text());u0={r['key']:r for r in json.loads((HERE.parent/'u0-assetfd-feedback/per-key.json').read_text())};frozen={r['key']:r for r in json.loads((HERE.parent/'freeze-v1/predictions.json').read_text())}
 defs={key:(cid,layer,batch,confidence,score,note) for cid,layer,batch,confidence,items in GROUPS for key,score,note in items}
 assert len(defs)==42 and set(defs)=={r['key'] for r in evidence if not r['lit']}
 rows=[];outcomes=[]
 for e in sorted(evidence,key=lambda r:r['key']):
  k=e['key'];p=frozen[k]
  outcomes.append(dict(key=k,U1_prediction=p['U1'],U0_lit=u0[k]['actual_lit'],U2_lit=e['lit'],apk_matches=e['apk_sha256']==p['apk_sha256'],wall_score=defs[k][4] if k in defs else 'not-blocked-now'))
  if e['lit']:continue
  cid,layer,batch,confidence,score,note=defs[k];causes=[x for x in e['chain'] if 'Caused by:' in x['text']];cause=causes[-1] if causes else e['anchor']
  first_blocker=cause;fatal=(e['first_terminal'] or {}).get('anchor')
  if k in ['vlc','fd-shatteredpixeldungeon']:
   first_blocker=next(x for x in e['events'] if 'Error loading shared library' in x['text'])
  if k=='ppsspp':first_blocker=next(x for x in e['events'] if 'LoadLibrary failed' in x['text'])
  secondary=[x for x in e['events'] if re.search(r'\[B8-UEH\] background.*uncaught|MUSL-FDSAN.*attempted|DFX_SignalHandler.*signo\(11\)|finishActivity: OH TerminateAbility',x['text'])][:10]
  faults=e['faultlogs'];assert all(x['attributed'] for x in faults)
  fault_note=('Reviewed first: DEBUG SIGNAL(FDSAN), not a terminating SIGABRT. Same PID continues to dependency error and System.exit(1). Keep as additional native diagnostic; do not replace first fatal with DEBUG SIGNAL.' if faults else 'No archived faultlog; use PID-attributed hilog. Missing crash stack remains unknown.')
  if k in ['vlc','fd-shatteredpixeldungeon','fd-im-vector-app','fd-immich']:
   secondary.extend([x for x in e['events'] if re.search(r'Error loading shared library|Error relocating',x['text'])][:2])
  if k=='fd-noice':secondary=[x for x in e['events'] if 'SSLSockets' in x['text']][:4]
  row=dict(key=k,cluster_id=cid,layer=layer,batch=batch,layer_confidence=confidence,first_blocker=first_blocker,first_fatal=fatal,has_explicit_fatal=fatal is not None,blocking_kind='host-input-gate' if batch=='input' else 'no-explicit-fatal' if fatal is None else 'observed-fatal',cause=note,U0_first_family=u0[k]['actual_first_family'],U0_first_failure=u0[k]['first_failure'],U0_exact_checkpoint_score=score,known_U0_secondary_wall=(k=='vlc'),U0_cluster_ids=p['cluster_ids'],U1_prediction=p['U1'],faultlog_review=fault_note,faultlogs=faults,secondary_evidence=secondary,pids=e['pids'],alive_t5=e['alive_t5'],alive_t20=e['alive_t20'],log=e['log'],log_sha256=e['log_sha256'],record=e['record'],record_sha256=e['record_sha256'])
  rows.append(row)
 dump(HERE/'unlit-42.json',rows);csvout('unlit-42.csv',rows);dump(HERE/'per-key-66.json',outcomes);csvout('per-key-66.csv',outcomes)
 clusters=[]
 for cid,layer,batch,confidence,items in GROUPS:
  rs=[r for r in rows if r['cluster_id']==cid];confirmed=[r['key'] for r in rs if r['has_explicit_fatal']];other=[r['key'] for r in rs if not r['has_explicit_fatal']]
  clusters.append(dict(cluster_id=cid,layer=layer,batch=batch,app_count=len(rs),fatal_app_count=len(confirmed),fatal_keys=confirmed,observation_or_input_keys=other,keys=[r['key'] for r in rs],confidence=confidence,notes=[r['cause'] for r in rs],evidence=[dict(key=r['key'],log=r['log'],blocker=r['first_blocker'],fatal=r['first_fatal']) for r in rs]))
 # Additional observed walls are explicitly separate from the exclusive first-wall partition.
 additional={'N3-namespace': ['vlc','fd-shatteredpixeldungeon','fd-im-vector-app'], 'N3-property':['fd-immich']}
 bykey={e['key']:e for e in evidence}
 for c in clusters:
  c['additional_observed_keys']=additional.get(c['cluster_id'],[])
  c['total_observed_apps']=len(set(c['keys']+c['additional_observed_keys']))
  c['additional_evidence']=[dict(key=k,log=bykey[k]['log'],events=[x for x in bykey[k]['events'] if re.search(r'Error loading shared library|Error relocating',x['text'])][:2]) for k in c['additional_observed_keys']]
  c['requires_boot_classpath_coordination']=c['cluster_id']=='J4-boot-api'
 clusters.sort(key=lambda c:(-c['fatal_app_count'],-c['app_count'],c['cluster_id']))
 dump(HERE/'next-clusters.json',clusters);csvout('next-clusters.csv',clusters)
 for batch in ['J4','N3','input']:dump(HERE/(batch+'.json'),[c for c in clusters if c['batch']==batch])
 fault_apps=[e['key'] for e in evidence if e['faultlogs']]
 dump(HERE/'N3-additional-fdsan.json',dict(keys=fault_apps,count=len(fault_apps),first_fatal_count=0,priority='additional-to-namespace-cluster; do not double-count apps',note='FDSAN ownership diagnostic in load_library_header/preload_direct_deps, via StockOpenNamespace/ANL_Dlopen (Flutter: flutter_prepare). Subsequent same-PID execution proves the recorded DEBUG SIGNAL was not itself terminal. Root cause not established.',evidence=[dict(key=e['key'],faultlogs=e['faultlogs']) for e in evidence if e['faultlogs']]))
 lit={e['key'] for e in evidence if e['lit']};pred={k for k,p in frozen.items() if p['U1']=='亮'};u0lit={k for k,p in u0.items() if p['actual_lit']}
 hit_keys=sorted(r['key'] for r in rows if r['U0_exact_checkpoint_score']=='hit');miss_keys=sorted(r['key'] for r in rows if r['U0_exact_checkpoint_score']=='miss');unknown_keys=sorted(r['key'] for r in rows if r['U0_exact_checkpoint_score']=='unknown')
 facts=json.loads((HERE/'record-facts.json').read_text());runs=json.loads((HERE/'run-audit.json').read_text())
 assert all(r['apk_matches'] for r in outcomes)
 result=dict(scope='U2 post-hoc triage and descriptive frozen-feature comparison; NOT exact-profile prospective accuracy',keys=66,unlit=42,lit=24,wall_comparison=dict(policy='Compare the selected U0 startup/fatal checkpoint to U2; earlier caught loader failures are retained separately. A miss includes new post-repair walls, not proof the prior fix failed. Unknown is abstention/no-fatal/incomplete U0. Hits do not imply common root cause.',hits=len(hit_keys),misses=len(miss_keys),known_secondary_reappeared=['vlc'],known_first_or_secondary_hits=len(hit_keys)+1,unknown=len(unknown_keys),hit_keys=hit_keys,miss_keys=miss_keys,unknown_keys=unknown_keys),lighting=dict(predicted=len(pred),actual=len(lit),hits=len(pred&lit),false_alerts=len(pred-lit),misses=len(lit-pred),false_alert_keys=sorted(pred-lit),miss_keys=sorted(lit-pred),precision=len(pred&lit)/len(pred),recall=len(pred&lit)/len(lit),note='Literal frozen U1 light labels evaluated descriptively on U2; advance/unknown do not predict darkness.'),u0_delta=dict(retained=len(lit&u0lit),new=sorted(lit-u0lit),lost=sorted(u0lit-lit)),first_fatal_count=sum(r['has_explicit_fatal'] for r in rows),batch_counts=dict(Counter(r['batch'] for r in rows)),clusters=len(clusters),captured=sum(f['captured'] for f in facts),alive={t:dict(yes=sum(f['alive_'+t] is True for f in facts),no=sum(f['alive_'+t] is False for f in facts),unknown=sum(f['alive_'+t] is None for f in facts)) for t in ['t5','t20']},facts_total=[next(l for l in run['facts'].splitlines() if l.startswith('TOTAL ')) for run in runs],source_verdict=dict(path=str(SOURCE/'results.json'),sha256=sha(SOURCE/'results.json')),U0_source_sha256=sha(HERE.parent/'u0-assetfd-feedback/per-key.json'),freeze_sha256=sha(HERE.parent/'freeze-v1/freeze.json'),all_three_fingerprint_maps_equal=True,faultlogs_reviewed=4,reruns_in_primary_score=False)
 dump(HERE/'results.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
