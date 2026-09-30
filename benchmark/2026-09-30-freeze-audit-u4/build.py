#!/usr/bin/env python3
"""Read archived evidence and actual candidates; emit a new, independent forecast."""
import collections
import copy
import csv
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts/lab'))
import lab_paths
import check_frozen
W = lab_paths.workspaces()
J3 = ROOT/'benchmark/2026-09-30-round1-plan/j3-feedback'
WALLS = W/'westlake-harness-walls'
SRC = WALLS/'bms/src/adapter/framework/activity/java'
BUILD = WALLS/'benchmark/2026-09-29-bms-link-entry-walls'
DEPLOY = W/'westlake-harness-bms-deploy'
PINS = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    if isinstance(value, dict): return {k: portable(v) for k,v in value.items()}
    if isinstance(value, list): return [portable(v) for v in value]
    if isinstance(value, str): return value.replace(str(W)+'/', '')
    return value


def ref(path):
    path=Path(path);rel=str(path.relative_to(W));PINS[rel]=sha(path);return rel


def read(path):
    ref(path);return json.loads(Path(path).read_text())


def dump(name, value):
    (HERE/name).write_text(json.dumps(portable(value), ensure_ascii=False, indent=2)+'\n')


def matches(path, pattern, pids=None):
    ref(path);rows=[]
    for n,text in enumerate(Path(path).read_text(errors='replace').splitlines(),1):
        if re.search(pattern,text) and (pids is None or len(text.split())>2 and text.split()[2] in pids):
            rows.append(dict(line=n,text=text))
    return rows


def facts_line(record):
    record=Path(record);p=record.parent.parent/'facts.txt';ref(p)
    key=record.parent.name
    return next(x for x in p.read_text().splitlines() if x.split() and x.split()[0]==key)


def admission(scope_single, blob_matches, passed_apps, lit_apps):
    return bool(scope_single and blob_matches and len(set(passed_apps))>=2 and set(lit_apps)&set(passed_apps))


def audit(evidence, builds):
    candidate_path=W/'westlake-harness-t3/benchmark/2026-09-30-jar-freeze-inventory/registrable-entries.json'
    candidates=read(candidate_path)['ready_to_register']
    registry=read(W/'westlake-harness/knowledge/frozen/frozen.json')
    used={r['id'] for r in registry['entries']}
    audits=[];all_evidence=[];proposals=[]
    for entry in candidates:
        source=entry['sources'][0];path=WALLS/source['repo_path'];ref(path)
        blob=check_frozen.git_blob(path)
        is_alarm='AlarmVibrator' in path.name
        single=not is_alarm
        tag=r'B8-FETCH\] alarm fetcher replaced' if is_alarm else 'B8-JARVERIFY.*BouncyCastleProvider'
        old=r'NullPointerException.*(?:AlarmManager|alarm)|Caused by:.*AndroidAlarmManager' if is_alarm else 'Sun provider not found'
        rows=[]
        for app in entry['verified_apps']:
            key=app['app'];e=evidence[key];log=Path(e['log']);record=Path(e['record']);rr=read(record)
            image=record.with_name('t20.jpeg');ref(image)
            assert any(s.get('captured') is True and s.get('scheduled_seconds')==20 and Path(s.get('path','')).name=='t20.jpeg' and s.get('sha256')==sha(image) for s in rr['screenshots']),key
            hits=matches(log,tag,e['pids']);failures=matches(log,old,e['pids'])
            assert hits and not failures and e['lit'], key
            before=None
            if not is_alarm:
                prior=ROOT/'benchmark/2026-09-30-v3c-r17j-prospective/backtests/v2-5ea/evidence'/f'{key}.json'
                pr=read(prior);lp=Path(pr['record']).with_name('hilog.txt')
                before=dict(log=ref(lp),hits=matches(lp,'Sun provider not found',pr['target_pids']))
                assert before['hits']
            # Also verify that the originally submitted evidence exists, rather than silently replacing it.
            orig_image=W/app['t20'];orig_record=orig_image.with_name('record.json');original=read(orig_record)
            orig_log=orig_image.with_name('hilog.txt')
            original_hits=matches(orig_log,tag)
            rows.append(dict(key=key,package=e['package'],passed_observed_checkpoint=True,outer_t20_lit=True,
                independently_viewed_j3_image=key in ['fd-droidify','fd-com-amaze-filemanager'],
                after=dict(log=ref(log),pids=e['pids'],positive_hits=hits,negative_failure_hits=failures,
                           t20=ref(image),record=ref(record),facts=facts_line(record)),before=before,
                original_submission=dict(t20=ref(orig_image),record=ref(orig_record),captured=sum(x.get('captured') is True for x in original['screenshots']),helper_hits=original_hits,facts=facts_line(orig_record))))
        full_source=str(path.relative_to(WALLS));build_rows=[]
        for tag_name, build in builds.items():
            emitted=any(x.endswith('/'+path.stem+'.smali') for x in build['added_classes'])
            source_match=build['sources'].get(full_source)==sha(path)
            assert source_match and emitted
            build_rows.append(dict(build=tag_name,jar_sha256=build['output_sha256'],source_sha_matches=source_match,helper_emitted=emitted))
        accepted=admission(single,blob==source['blob'],[r['package'] for r in rows],[r['package'] for r in rows if r['outer_t20_lit']])
        remaining=['Replace colliding proposed ID; FZ-002/003 already belong to native fixes.',
                   'Keep feat/bms-walls cdb82fe5 source snapshot; source file absent from current master, so materialize exact blob in the build source root before enabling source checks.']
        if is_alarm:remaining += ['Split AlarmFetcher from VibratorFetcher; preserve alarm bodies/call order, pin the new alarm-only blob and reverify the split.',
                                 'Do not describe vibrator as frozen: current J3 fd-reader still fails SystemVibratorManager.getVibratorIds monitor-enter NPE, and no second distinct vibrator app was supplied.']
        audit_row=dict(candidate=path.stem,submitted_id=entry['id'],id_collision=entry['id'] in used,
            behavior_evidence_apps=len(rows),packages=[r['package'] for r in rows],lit_apps=len(rows),
            independent_single_fix_file=single,source_blob_matches=blob==source['blob'],actual_blob=blob,
            source=ref(path),source_in_master=(W/'westlake-harness'/full_source).exists(),source_scope_evidence=matches(path,r'replaceFetcher\("(?:alarm|vibrator_manager)"|public static void apply|jvp\[0\] = BC'),
            build_carriage=build_rows,eligible=accepted,verdict='eligible_with_registration_metadata_cleanup' if accepted else 'hold_split_required',remaining=remaining,evidence=rows)
        audits.append(audit_row);all_evidence.extend(rows)
        if accepted:
            proposal=copy.deepcopy(entry);number=1
            while f'FZ-{number:03d}' in used:number+=1
            proposal['id']=f'FZ-{number:03d}';used.add(proposal['id']);proposal['version']=1;proposal['status']='frozen';proposal['history']=[]
            proposal['frozen_at']='SET_BY_OUTER_AT_REGISTRATION'
            proposal['verified_apps']=[dict(app=r['key'],board='J3 '+('61b' if '/j3-61b/' in r['after']['log'] else '5ea'),evidence='t20_lit',t20=r['after']['t20'],facts=r['after']['facts'],log=r['after']['log']+':'+str(r['after']['positive_hits'][0]['line']),change='Earlier PID-attributed Sun-provider failure; J3 helper rewrite present, old failure absent, own t20 UI') for r in rows]
            proposal['source_record'] += '; audited post-split on J3; full logs/SHAs and earlier failure excerpts in benchmark/2026-09-30-freeze-audit-u4/audit.json. Source root is westlake-harness-walls; default master path currently absent.'
            proposals.append(proposal)
    assert check_frozen.validate(proposals)==[]
    dump('audit.json',audits);dump('registration-proposal.json',dict(note='Proposal only. Outer assigns final ID/time and ensures source-root availability; no registry edited.',entries=proposals))
    with (HERE/'registration-table.csv').open('w') as f:
        fields=['candidate','submitted_id','id_collision','behavior_evidence_apps','lit_apps','independent_single_fix_file','actual_blob','source_in_master','verdict','remaining']
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        for row in audits:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in row.items() if k in fields})
    return audits


def main():
    if (HERE/'freeze.json').exists():
        raise SystemExit('Forecast is frozen; create an explicit revision instead of overwriting it.')
    evidence={r['key']:r for r in read(J3/'evidence.json')}
    walls={r['key']:r for r in read(J3/'per-key.json')}
    clusters={c['cluster_id']:c for c in read(J3/'next-clusters.json')}
    plan=read(ROOT/'benchmark/2026-09-30-round1-plan/four-board-v1/shards.json')
    builds={tag:read(BUILD/f'build-result-{tag}.json') for tag in ['j1final','j3','j4','j5']}
    for tag,folder in [('j3','j3-75c2068c'),('j4','j4-1c1bbef'),('j5','j5-dbce2eee')]:
        jar=W/'vm-copies'/folder/'oh-adapter-runtime.jar'
        assert sha(jar)==builds[tag]['output_sha256'];ref(jar)
    candidates=audit(evidence,builds)
    n2=read(W/'westlake-generation-n2-51a78bde/package.json')
    n3b=read(W/'westlake-generation-n3b-53bb18d1/package.json')
    assert sha(W/'westlake-generation-n3b-53bb18d1/package.json')=='53bb18d1743a69bee9be98b4704afc5e684f57c002687fc2771678c2edd575d3'
    delta={p:dict(before=n2['files'].get(p),after=h) for p,h in n3b['files'].items() if n2['files'].get(p)!=h}
    dump('native-delta.json',delta)
    for p,h in delta.items():assert sha(W/'westlake-generation-n3b-53bb18d1'/p)==h['after']
    gap=read(HERE/'webview-contract-gap.json')
    assert not gap['definition_found'] and gap['native']['required_class_string_offset']>=0
    for row in gap['jars']+[gap['native']]:assert sha(W/row['path'])==row['sha256'];ref(W/row['path'])
    changes={
      'N3-namespace':dict(checkpoint='selected libandroid/libGLESv2/resident-runtime resolution',source=DEPLOY/'benchmark/2026-09-30-n3-native/README.md',pattern='Resident runtime publication'),
      'N3-jna-symbol':dict(checkpoint='__sF@LIBC relocation before JNA resource fallback',source=DEPLOY/'benchmark/2026-09-30-n3-native/README.md',pattern='JNA stdio sentinels'),
      'N3-property':dict(checkpoint='__system_property_find and read_callback import resolution',source=DEPLOY/'benchmark/2026-09-30-n3-native/README.md',pattern='Property find/read callback'),
      'N3-eglimpl':dict(checkpoint='EGLImpl._eglGetDisplay(Object)J binding',source=DEPLOY/'benchmark/2026-09-30-n3-native/README.md',pattern='Runtime EGLImpl registration'),
      'N3-opensles':dict(checkpoint='slCreateEngine and Android extension IID resolution',source=DEPLOY/'benchmark/2026-09-30-n3-native/README.md',pattern='Whole `opensles_android_compat.c`'),
    }
    for info in changes.values(): info['evidence']=dict(file=ref(info['source']),lines=matches(info['source'],info['pattern']))
    ref(SRC/'WlMediaRouter.java');ref(SRC/'AndroidFrameworkPackage.java');ref(SRC/'WestlakeWebViewInstall.java');ref(SRC/'WebViewPackageFallback.java');ref(SRC/'B7BindFixes.java')
    rows=[]
    for key in sorted(plan['expected_keys']):
        e=evidence[key];wall=walls.get(key,{});cluster=wall.get('cluster_id','already-lit')
        row=dict(key=key,package=e['package'],shard=next(s['name'] for s in plan['shards'] if key in s['keys']),
          baseline_lit=e['lit'],baseline_apk_sha256=e['apk_sha256'],apk_sha256=plan['expected_apk_sha256'][key],
          apk_changed=e['apk_sha256']!=plan['expected_apk_sha256'][key],prediction='不变',expected_lit=e['lit'],
          expected_new_light=False,confidence='medium',checkpoint='preserve own t20 UI' if e['lit'] else wall.get('cause','unknown'),
          checkpoint_outcome='unchanged',next_wall=wall.get('cause'),conditions=[],secondary_benefit=None,
          baseline=dict(log=e['log'],log_sha256=e['log_sha256'],pids=e['pids'],first_blocker=wall.get('first_blocker'),first_fatal=wall.get('first_fatal')),
          change_evidence=[])
        if cluster in changes:
            info=changes[cluster];row.update(prediction='推进',expected_lit=None,expected_new_light=None,checkpoint=info['checkpoint'],checkpoint_outcome='predicted_pass',next_wall='unknown_after_checkpoint',conditions=['Full N3b delta deployed, exact consumer selected, imports resolve in actual owner namespace; static symbol supply does not prove runtime binding.'],change_evidence=[info['evidence']])
        if key=='noice':row.update(prediction='亮',expected_lit=True,expected_new_light=True,confidence='medium',checkpoint='MediaRouter.registerClientAsUser no longer null',checkpoint_outcome='predicted_pass',next_wall='unknown; background TLS may still fail',conditions=['J5 retains J4 WlMediaRouter; own first UI is a forecast, not an observation.'],change_evidence=[dict(file=ref(SRC/'WlMediaRouter.java'),lines=matches(SRC/'WlMediaRouter.java',r'registerClientAsUser|media_router'))])
        if key=='newpipe':row.update(prediction='推进',checkpoint='PlayerService Platform signature not found',checkpoint_outcome='predicted_pass_functional_only',next_wall='playback outcome unknown',secondary_benefit='Already lit; no additional light counted.',change_evidence=[dict(file=ref(SRC/'AndroidFrameworkPackage.java'),lines=matches(SRC/'AndroidFrameworkPackage.java',r'pi.signatures|signingInfo'))])
        if key=='fd-tutanota':row.update(checkpoint='WebViewFactory.isWebViewSupported remains false',next_wall='same WebViewFactory UnsupportedOperationException',confidence='high',conditions=['No declared real provider APK/Chromium/data configuration in U4 package.', 'Even with provider bytes added, native exact WebViewUpdateServiceAdapter class is absent in J5 + supplied boot JAR union. Requires another Java artifact/profile before rescoring.'],change_evidence=[dict(file='westlake-harness-bms/benchmark/2026-09-30-freeze-audit-u4/webview-contract-gap.json'),dict(file=ref(DEPLOY/'benchmark/2026-09-30-n3b-webview/JAVA-HANDOFF.md'),lines=matches(DEPLOY/'benchmark/2026-09-30-n3b-webview/JAVA-HANDOFF.md',r'Provider payload checklist|WebViewUpdateServiceAdapter.isAvailable|contain none'))])
        if key in ['fd-immich','vlc']:
            row['secondary_benefit']='Property imports may pass after d7.c verifier wall' if key=='fd-immich' else 'GLES visibility checkpoint may pass; Transparent context/theme failure not repaired'
            row['conditions']=['Primary remaining Java/resource failure is outside implemented repair; secondary progress is scored separately.']
        if key in ['fd-seal','toutiao','subwaysurfers']:
            row.update(prediction='推进',expected_lit=None,expected_new_light=None,checkpoint='host input gate to BMS installation attempt',checkpoint_outcome='host_preflight_verified_device_unknown',next_wall='unknown_BMS_extract_or_app_start',conditions=['Use repaired bms_batch and current manifest; installer extraction exception status still unverified. Input-tool benefit, not J4/J5/N3b runtime yield.'],change_evidence=[dict(file=ref(ROOT/'benchmark/2026-09-30-input-recovery/results.json'))])
        if key=='fd-noice':row['secondary_benefit']='None: already-lit welcome screen protected; SSLSockets background failure is still not repaired.'
        if cluster=='J4-boot-api':row['conditions']=['#91/T7 boot repairs are not included in N3b+J5; boot jars unchanged.']
        if key in ['termux','fd-AppManager','fd-mobile','fd-uhabits']:
            row['confidence']='low';row['conditions']=['No explicit first fatal and no matching repair. Keep baseline point forecast; runtime observation may vary.']
        rows.append(row)
    assert len(rows)==66 and len({r['key'] for r in rows})==66
    dump('predictions.json',rows)
    fields=['key','shard','baseline_lit','prediction','expected_lit','expected_new_light','confidence','checkpoint','checkpoint_outcome','next_wall','secondary_benefit','conditions','apk_changed','apk_sha256']
    with (HERE/'predictions.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        for row in rows:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in row.items() if k in fields})
    profile=dict(native_manifest_sha256=sha(W/'westlake-generation-n3b-53bb18d1/package.json'),runtime_sha256=gap['native']['sha256'],jar_sha256=builds['j5']['output_sha256'],jar_includes=builds['j4']['output_sha256'],installer=read(W/'westlake-harness/knowledge/frozen/frozen.json')['entries'][0]['artifacts'],native_delta_paths=len(delta),provider_declared=False,fourth_oh_serial=None,rollout_ready=False,source_native_package='westlake-generation-n3b-53bb18d1',source_jar='vm-copies/j5-dbce2eee/oh-adapter-runtime.jar')
    dump('profile.json',profile)
    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    summary=dict(frozen_at=timestamp,keys=len(rows),baseline_lit=sum(r['baseline_lit'] for r in rows),predictions=dict(collections.Counter(r['prediction'] for r in rows)),lighting_predictions=dict(yes=sum(r['expected_lit'] is True for r in rows),no=sum(r['expected_lit'] is False for r in rows),unknown=sum(r['expected_lit'] is None for r in rows)),new_light_forecast_keys=[r['key'] for r in rows if r['expected_new_light'] is True],api_checkpoint_pass_only_keys=[r['key'] for r in rows if r['checkpoint_outcome']=='predicted_pass' and r['prediction']=='推进'],freeze_eligible=sum(x['eligible'] for x in candidates),freeze_hold=sum(not x['eligible'] for x in candidates),device_actions=0,screenshots_new=None,alive_new=None,profile=profile,scoring='Only records clicked after freeze, exact APK and profile, count in prospective score. Checkpoint passage, functional repair and lighting have separate denominators; exclude null lighting forecasts and report their coverage. Changed JAR/provider or unbound fourth slot needs a separately frozen revision.')
    dump('results.json',summary)
    dump('source-pins.json',PINS)
    frozen_names=['predictions.json','predictions.csv','profile.json','results.json','source-pins.json','webview-contract-gap.json','native-delta.json']
    dump('freeze.json',dict(frozen_at=timestamp,files={n:sha(HERE/n) for n in frozen_names}))
    print(json.dumps({k:summary[k] for k in ['keys','predictions','lighting_predictions','new_light_forecast_keys','freeze_eligible','freeze_hold']},ensure_ascii=False))

if __name__=='__main__':main()
