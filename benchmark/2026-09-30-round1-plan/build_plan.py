#!/usr/bin/env python3
"""Merge the two accepted cluster inventories without overwriting their history."""
import argparse
import collections
import csv
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[1]
TREES = WORK.parent
BOARD = TREES/'westlake-harness/.octos/boards/app-lighting.md'
OLD = TREES/'westlake-harness-walls/benchmark/2026-09-30-r17p-deadapp-clusters/clusters.json'
FEEDBACK = WORK/'benchmark/2026-09-29-static-wall-prediction/unified-r17r-feedback'
SIGNATURE = TREES/'westlake-harness/benchmark/2026-09-30-unified-r17r-5cd-sweep/results.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def catalog():
    rows = []
    def add(cid, name, layer, lane, apps, old, families, probe, reason,
            status='planned', confidence='medium', j='不变', n='不变', u='unknown',
            overrides=None, depends=()):
        rows.append(dict(cluster_id=cid, cluster=name, layer=layer, lane=lane,
            owner={'J1':'cc-t3','N1':'cx-t0','boot':'oc-t4','app':'unassigned / diagnosis only'}.get(lane,lane),
            status=status, layer_confidence=confidence, beneficiary_keys=apps.split(),
            r17p_indices=old, feedback_families=families.split(),
            predictions={k:{'J1':j,'N1':n,'U1':u,**(overrides or {}).get(k,{})} for k in apps.split()},
            pass_checkpoint=probe, reasoning=reason, related_walls=list(depends)))

    add('N01','Same-window EGL surface/session rebuild','native','N1',
        'wikipedia fd-noice noice fd-uhabits',[2], 'egl-window-recreation',
        'Target window survives repeated relayout with a valid surface and renders after the former EGL_NO_SURFACE point; no target-PID BAD_ALLOC/ASSERT.',
        '10:14 cc-wiki assigned same-window session repair to 32df; N1 must port it onto asset-fd without changing FZ-003. Noice may also need J1 audio fallback.',
        n='过墙',u='亮',overrides={'wikipedia':{'N1':'亮'},'fd-uhabits':{'N1':'亮'}},depends=['KEEP01','J05'])
    add('N02','Flutter private dependency namespace / libsurface inherits','native','N1',
        'fd-fluffychat fd-immich fd-kitchenowl fd-libre fd-saber localsend',[0], 'app-native-namespace-dependency',
        'The same app loads its libflutter and private libandroid/GLES dependencies; libsurface inherits error is gone and Flutter engine initialization advances.',
        'r5 exposed libsurface inheritance after caller permission advanced; r6 is an intended repair, not already successful. Immich has a separate earlier verifier failure.',
        n='过墙',u='过墙',depends=['A02'])
    add('N03','App namespace visibility of required shared libraries','native','N1',
        'anki fd-app fd-organicmaps fd-client mcdonalds mindustry',[4,6,15,21,22], 'app-native-namespace-dependency',
        'Exact app library loads in its app namespace and its initialization returns; liblog/libstdc++/GLES/OpenSLES dependency error is absent after that call.',
        'A system-path library hash does not establish app-domain visibility. OrganicMaps/Nextcloud/McDonalds late null state follows earlier loader failures.',
        n='过墙',u='过墙')
    add('N04','App Bionic imports: atfork / fortified fd-set','native','N1',
        'burgerking fd-im-vector-app',[1,11], 'bionic-symbol',
        'libreactnative or librealm-jni completes loading past the exact missing import, without a subsequent loader error at that call.',
        'Retain __register_atfork and __FD_SET_chk as distinct import requirements; Element also fails Sentry provider bind first.',
        n='过墙',u='过墙',depends=['J07'])
    add('N05','JNA native resource/search path','native','N1',
        'fd-fennec_fdroid firefox',[7], 'jna-native-resource',
        'com.sun.jna.Native initialization returns with the matching AArch64 libjnidispatch loaded; Gecko startup advances.',
        'NCDFE wraps missing libjnidispatch, so ownership is native/assembly with Java search-path cooperation, not evidence of a missing boot class.',
        n='过墙',u='过墙',confidence='provisional: assembly/search-path boundary')
    add('N06','SoundPool declared system library','native','N1',
        'fd-plus',[16], 'framework-audio-native-closure',
        'SoundPool class initialization and Builder.build return; Osmand Application/VoiceRouter initialization passes the former loadLibrary failure.',
        'The earliest failure is undeclared system library; DayNightHelper null is later. Do not merge its fix with AudioProductStrategy registration.',
        n='过墙',u='过墙')
    add('N07','GLImpl native class initialization','native','N1',
        'fd-shatteredpixeldungeon',[17], 'gles-jni',
        'GLImpl._nativeClassInit returns and GL context initialization advances, with no replacement JNI failure at the same stage.',
        'Missing native binding is explicit; passing this one JNI method is not proof of a complete GLES path.',n='过墙',u='过墙')
    add('N08','WebView provider availability','native','N1',
        'fd-tutanota',[18], 'webview-provider',
        'WebViewFactory.getProvider returns a usable provider and WebView construction/content initialization advances.',
        'cc-t3 routed this to native, but logs establish provider failure, not a complete repair recipe; Java/boot/provider packaging may also be required.',
        status='candidate-needs-real-provider',confidence='provisional: provider packaging boundary')
    add('N09','Bitmap color-space contract','native','N1',
        'fd-musicplayer',[14], '',
        'The formerly failing bitmap creation returns a bitmap with a valid color space and activity initialization advances.',
        'Native is the triage lead for graphics; exact Java/native source ownership is unresolved. Do not claim SessionToken repair alone fixes the later bitmap error.',
        status='candidate-needs-localization',confidence='unresolved Java/native boundary',depends=['J01'])

    add('J01','Own ServiceInfo / intent service projection','JAR','J1',
        'fd-binaryeye fd-musicplayer',[], 'camerax-configuration media-session-service-resolution',
        'Own camera service discovery/CameraX initialization or media SessionToken construction returns; then the target activity passes that initialization stage.',
        'BinaryEye is explicitly in J1; musicplayer shares service metadata/query requirements. Their later camera JNI/bitmap requirements remain separate.',
        j='过墙',u='过墙',depends=['N09'])
    add('J02','Activity theme/resource and ConstraintLayout projection','JAR','J1',
        'fd-api vlc',[4,8], 'activity-theme-contract',
        'Termux API activity passes AppCompat theme checks or VLC onboarding layout inflates past attribute index 13; target activity draws its own view.',
        'Use exact per-app theme/layout checkpoints. VLC may expose later native media walls; only the smaller API activity is forecast lit.',
        j='过墙',u='过墙',overrides={'fd-api':{'J1':'亮','U1':'亮'}})
    add('J03','RestrictionsManager non-null service','JAR','J1',
        'fd-meet',[13], 'restrictions-service-null',
        'getApplicationRestrictions returns a valid Bundle and React startup passes this call.',
        'An empty restrictions Bundle can satisfy this startup contract; React/native/network paths are not thereby verified.',j='过墙',u='过墙')
    add('J04','Haptic capability arrays during Compose initialization','JAR','J1',
        'fd-reader',[6], 'haptics-capability-null-array',
        'SystemVibrator.getInfo / areAllPrimitivesSupported returns a valid capability result and Compose local initialization passes the old null-array exception.',
        'r17r stack locates the formerly parked null-array inside framework SystemVibrator; JAR service response is a candidate repair seam, not proof of app DI failure.',
        j='过墙',u='过墙',confidence='provisional: service response vs boot implementation')
    add('J05','AudioProductStrategy startup fallback','JAR','J1',
        'opencamera fd-noice noice',[23], 'framework-audio-native-closure',
        'AudioAttributes.setLegacyStreamType returns beyond AudioProductStrategy JNI and OpenCamera.onResume continues.',
        'J1 inherits the r17t Java fallback. OpenCamera has a proven first wall; Noice keys are secondary audio requirements from the outer dual-fix plan, not their observed first fatal. N1 is the alternative for a real binding.',
        j='过墙',u='过墙')
    add('J06','Gallery JAR-side workaround candidate','JAR','J1',
        'fd-gallery',[], '',
        'A documented JAR-only path avoids the exact boot MediaStore field resolution and reaches Gallery content initialization.',
        'Outer explicitly permits only the JAR-fixable portion. A missing field in an already selected boot class cannot be assumed repaired by this JAR.',
        status='candidate-boot-dependent',depends=['B02'])
    add('J07','Sentry provider configuration projection','JAR','J1',
        'fd-im-vector-app',[11], 'sentry-provider-configuration',
        'SentryInitProvider.onCreate returns with the app declared DSN/enabled metadata interpreted correctly; no DSN-required bind failure.',
        'J1 triages metadata/resource projection first. The trace proves rejected provider configuration, not which missing metadata caused it; native Realm remains later.',
        j='过墙',u='过墙',confidence='provisional: metadata/app configuration',depends=['N04'])

    add('B01','TagSoup Parser.setProperty boot definition','boot','boot',
        'fd-libretube',[12], '',
        'The selected boot Parser definition has setProperty and the call returns before LibreTube activity initialization advances.',
        'Declaration is adapter-mainline-stubs.jar. oc-t4 image/toolchain work is a prerequisite; no boot replacement is included in J1/N1 or assumed in U1.',
        status='separate-boot-delivery',u='不变',depends=['A01'])
    add('B02','MediaStore.Images.Media.EXTERNAL_CONTENT_URI boot field','boot','boot',
        'fd-gallery',[], 'mediastore-field',
        'The selected boot class resolves EXTERNAL_CONTENT_URI and Gallery proceeds beyond the old NoSuchFieldError.',
        'Exact failing declaration is adapter-mainline-stubs.jar; J1 workaround is unproven. Do not count a second JAR containing a field as a loaded-class repair.',
        status='separate-boot-delivery',u='不变',depends=['J06'])
    add('B03','NetworkCapabilities boot method','boot','boot',
        'x',[24], 'network-capabilities-method',
        'getLinkUpstreamBandwidthKbps resolves on the selected boot class and Application bind continues; later object graph errors are assessed separately.',
        'Exact failing declaration is adapter-mainline-stubs.jar; adding a runtime service stub alone cannot supply this virtual method.',
        status='separate-boot-delivery',u='不变')

    add('A01','Zero-size disk cache configuration','app 内部','app',
        'fd-libretube',[12], 'disk-cache-size-contract',
        'LibreTube Application constructs Coil DiskCache with positive capacity and bind completes.',
        'Observed at app/Coil contract boundary. Source of zero (app configuration versus platform disk statistics) is unknown; J1 triages before assigning a fix.',
        status='diagnose-before-assignment',confidence='observed boundary only; root owner unknown',depends=['B01'])
    add('A02','Immich verifier unresolved-reference/access failure','app 内部','app',
        'fd-immich',[0], 'dex-verifier-access',
        'A2.b.onMethodCall verifies and bind no longer rejects access through unresolved d7.c; Flutter is checked separately.',
        'The rejected class is in the APK. Do not infer ART defect or bypass verification; J1/boot triage class availability first.',
        status='diagnose-before-assignment',confidence='APK failure location, not proven app bug',u='不变',depends=['N02'])
    add('A03','Unlocalized getClass null during create/resume','app 内部','app',
        'fd-breezyweather fd-wifianalyzer fd-catima',[5,9], '',
        'Identify the null producer and demonstrate the exact create/resume call proceeds.',
        'Keep unknown ownership; generic app DI labels do not justify a framework stub.',status='diagnose-before-assignment',confidence='unresolved')
    add('A04','AppManager authentication/ADB startup hang','app 内部','cc-wiki',
        'fd-AppManager',[], '',
        'Background authentication/mode detection completes or reaches no-root fallback, then MainActivity draws.',
        '10:04 cc-wiki reports healthy splash/window and silent ADB-detection worker. Socket endpoint/timeout remains unproven; J1 inclusion only if Java boundary is established.',
        status='diagnose-before-assignment',confidence='hypothesis from code+logs, blocked thread not sampled')
    add('A05','No diagnosed first fatal / blank or unfinished startup','app 内部','app',
        'fd-feeder ppsspp fd-mobile termux',[1], '',
        'Obtain a target-PID first failure or a blocked-stage trace plus outer screenshot review.',
        'Unknown evidence bucket, not a common mechanism or a promised repair. BurgerKing was removed from this bucket using its newer native failure.',
        status='diagnose-before-assignment',confidence='unknown')
    add('INPUT01','Non-AArch64 library payload input exceptions','app 内部','app',
        'fd-seal toutiao',[], '',
        'Approved exact-input handling installs the original app and creates a launchable record.',
        'Known prelaunch input walls are outside J1/N1. Preserve FZ-001; do not silently weaken installer checks.',status='outside-round',u='不变')
    add('INPUT02','Pinned APK identity mismatch','app 内部','app',
        'subwaysurfers',[], '', 'Obtain a confirmed APK identity before any launch score.',
        'Missing/mismatched input remains unknown, not a runtime failure.',status='outside-round',confidence='unknown')

    add('KEEP01','Frozen asset FD behavior retained in U0/N1','native','N1',
        'newpipe fd-uhabits',[19], 'asset-font-fd-stub',
        'Keep real asset FD behavior: NewPipe retains its own t20 page; uhabits remains beyond Implement me and its later EGL wall is evaluated independently.',
        'FZ-003 and targeted asset53 evidence were already read before this plan. This is retention, not a new round-one success.',
        status='frozen-retention',j='过墙',n='过墙',u='过墙',overrides={'newpipe':{'J1':'亮','N1':'亮','U1':'亮'}})
    add('KEEP02','Historical cppcrash labels now signed lit','native','N1',
        'antennapod fd-fitness',[3], '', 'Retain each app own t20 page on every tested profile.',
        'Both are lit in the accepted unified r17r sweep; do not add two fresh fixes from old r17p deaths.',
        status='regression-control',j='亮',n='亮',u='亮')
    add('KEEP03','Etar PowerExemption behavior retained','JAR','J1',
        'fd-etar',[10], '', 'Retain Etar own t20 page.', 'Newer unified screenshot supersedes the historical PowerExemption null wall.',
        status='regression-control',j='亮',n='亮',u='亮')
    add('KEEP04','Markor window/display behavior retained','JAR','J1',
        'markor',[20], '', 'Retain Markor own onboarding/main t20 page.', 'Newer unified screenshot supersedes the historical addToDisplay failure.',
        status='regression-control',j='亮',n='亮',u='亮')
    return rows


def merged_predictions(key, memberships, lit):
    if key in lit:
        return dict(J1='亮',N1='亮',U1='亮',basis='retain outer-signed r17r lighting; U0 transfer is still a prediction')
    special = {
        'newpipe':('亮','亮','亮','prior asset53 targeted success; exposed retention, not new prediction'),
        'wikipedia':('不变','亮','亮','32df graphics result already reported; combined profile transfer remains untested'),
        'fd-noice':('过墙','过墙','亮','combined Java audio fallback and native session repair'),
        'noice':('过墙','过墙','亮','combined Java audio fallback and native session repair'),
        'fd-uhabits':('不变','亮','亮','asset wall already passed; N1 targets subsequent EGL wall'),
        'fd-api':('亮','不变','亮','J1 targets the observed AppCompat activity contract'),
        'fd-immich':('unknown','不变','不变','native dependency may advance, but earlier verifier failure is not assigned a concrete repair'),
        'fd-libretube':('unknown','不变','不变','disk-cache cause unresolved and boot TagSoup change excluded'),
        'fd-gallery':('unknown','不变','不变','boot field remains; JAR-only bypass not established'),
        'x':('不变','不变','不变','boot method repair excluded from U1'),
    }
    if key in special:
        j,n,u,b=special[key];return dict(J1=j,N1=n,U1=u,basis=b)
    if any(r['status'] in ('diagnose-before-assignment','candidate-needs-real-provider','outside-round') for r in memberships):
        return dict(J1='unknown',N1='unknown',U1='unknown',basis='unresolved cause/input or undelivered real implementation')
    result={}
    for phase in ('J1','N1','U1'):
        values=[r['predictions'][key][phase] for r in memberships]
        result[phase]='过墙' if '过墙' in values else 'unknown' if 'unknown' in values else '不变'
    result['basis']='specific listed checkpoint(s) expected to advance; no own-content lighting promise'
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=HERE/'freeze-v1');args=parser.parse_args()
    if args.out.exists():raise ValueError('refuse to overwrite a frozen plan; select a new output directory')
    old=json.loads(OLD.read_text());feedback=json.loads((FEEDBACK/'missed-walls.json').read_text())
    latest=json.loads((FEEDBACK/'per-key.json').read_text());bykey={r['key']:r for r in latest}
    lit=set(json.loads(SIGNATURE.read_text())['lit_t20_by_screenshot'])
    rows=catalog();source_coverage=[]
    for row in rows:
        if not set(row['beneficiary_keys'])<=set(bykey):raise ValueError('unrecognized key')
        row['evidence']=[dict(key=k,first_failure=bykey[k]['first_failure_evidence'],
                             first_terminal=bykey[k]['terminal_evidence'],record=bykey[k]['source_record'],
                             log_sha256=bykey[k]['hilog_sha256']) for k in row['beneficiary_keys']]
        row['app_count']=len(row['beneficiary_keys'])
        row['new_wall_app_count']=sum(k not in lit for k in row['beneficiary_keys']) if row['status'] not in ('frozen-retention','regression-control') else 0
        row['delivery_prediction']={k:('过墙' if row['lane']=='boot' else row['predictions'][k].get(row['lane'],'unknown')) for k in row['beneficiary_keys']}
        row['novelty']='retention' if row['status'] in ('frozen-retention','regression-control') else 'new-plan'
    for index, item in enumerate(old):
        for key in item['apps']:
            ids=[r['cluster_id'] for r in rows if index in r['r17p_indices'] and key in r['beneficiary_keys']]
            if not ids:raise ValueError(f'unmapped old cluster {index}/{key}')
            source_coverage.append(dict(source='r17p',cluster=index,key=key,destinations=ids))
    for item in feedback:
        for key in item['all_observed_keys']:
            ids=[r['cluster_id'] for r in rows if item['family'] in r['feedback_families'] and key in r['beneficiary_keys']]
            if not ids:raise ValueError(f'unmapped feedback family {item["family"]}/{key}')
            source_coverage.append(dict(source='r17r',cluster=item['family'],key=key,destinations=ids))
    # Stable order: active/candidate work by impacted keys, then retention/diagnosis.
    rows.sort(key=lambda r:(r['status'] in ('regression-control','frozen-retention','outside-round','diagnose-before-assignment'),-r['new_wall_app_count'],r['cluster_id']))
    forecasts=[]
    for key, evidence in sorted(bykey.items()):
        membership=[r for r in rows if key in r['beneficiary_keys']]
        forecasts.append(dict(key=key,apk_sha256=evidence['predicted_apk_sha256'],
            cluster_ids=[r['cluster_id'] for r in membership],baseline_r17r_lit=key in lit,
            observed_first_wall=evidence['actual_first_cause'],observed_terminal=evidence['actual_terminal_cause'],
            observed_log_sha256=evidence['hilog_sha256'],**merged_predictions(key,membership,lit)))
    args.out.mkdir(parents=True);sources=args.out/'sources';sources.mkdir()
    paths={'r17p-clusters.json':OLD,'r17r-missed-walls.json':FEEDBACK/'missed-walls.json',
           'r17r-per-key.json':FEEDBACK/'per-key.json','r17r-outer-signature.json':SIGNATURE,
           'frozen-registry.json':TREES/'westlake-harness/knowledge/frozen/frozen.json'}
    inputs={}
    for name,path in paths.items():
        (sources/name).write_bytes(path.read_bytes());inputs[name]=dict(path=str(path),sha256=sha(path))
    lines=BOARD.read_text(errors='replace').splitlines();start=next(i for i,l in enumerate(lines) if '全面放开后重新调度(10:18' in l)
    end=next(i for i in range(start,len(lines)) if 'J1、N1 各自先' in lines[i])+1
    context='\n'.join(f'{i+1}: {lines[i]}' for i in range(start,end))+'\n'
    if '\ufffd' in context:raise ValueError('invalid UTF-8 in the task excerpt')
    (sources/'board-task.txt').write_text(context)
    profile=dict(U0=dict(package='668e4f7c',runtime='53f00423',jar='dd4f0eae',installer=['6aadb8b4','7048c7c5']),
        J1=dict(name='r17u on U0',jar_sha256=None,required_layers=['JAR']),
        N1=dict(name='native batch on U0',artifact_sha256=None,required_layers=['native']),
        U1=dict(name='U0 + accepted J1 + accepted N1',artifact_sha256=None,boot_change_included=False),
        binding_policy='Feature-plan freeze. Append exact release manifests/SHAs in a separate receipt before scoring; never edit this prediction table. Missing/different components produce a profile-drift stratum, not exact-profile accuracy.')
    policy=dict(wall_pass='Target stage must be reached; old target-PID/API failure disappears AND a positive return/later stage is evidenced. Earlier failure or absent logs => unknown, not pass.',
        lit='Only outer-signed t20 own-content screenshot; process alive/facts PASS is not lighting.',
        prediction_levels={'亮':'predict own content plus relevant wall passage','过墙':'predict named checkpoint, lighting unknown','不变':'no forecast removal of current blocking path','unknown':'abstain'},
        per_app_warning='Cluster forecasts score individual APIs; per-app forecast retains earlier unaddressed walls. Do not sum overlapping app counts.',
        related_walls='Cross-references, not a dependency DAG. A per-key earlier failure may mask a later API test; masked tests are unknown, never passes.',
        sequence='J1 vs U0 and N1 vs U0 separately; then U1 three-board sweep. If one profile changes multiple files/layers, report that scope and avoid single-cause claims.',
        U1_facts='Require 66 unique keys over explicit shard directories, same measured path/hash map and registered frozen fixes. Quote shard facts verbatim, recount captured/process tables, preserve missing/unknown, never borrow previous rounds.',
        exposure='r17p/r17r sweeps, asset53 NewPipe/uhabits, r17t and reported 32df Wikipedia outcomes were known. J1/N1 complete batch and U1 outcomes were not read. Post-freeze click and exact-profile eligibility are evaluated later.',
        frozen_rules='FZ-001 installer, FZ-002 provider, FZ-003 asset source behavior retained; only outer may register permitted revisions. This plan does not authorize changing frozen implementations.')
    write(args.out/'plan.json',dict(schema='round1-cluster-plan-v1',profiles=profile,policy=policy,clusters=rows))
    write(args.out/'predictions.json',forecasts);write(args.out/'source-coverage.json',source_coverage)
    flat=[]
    for r in rows:
        for key in r['beneficiary_keys']:
            flat.append(dict(cluster_id=r['cluster_id'],cluster=r['cluster'],layer=r['layer'],lane=r['lane'],owner=r['owner'],status=r['status'],key=key,delivery_prediction=r['delivery_prediction'][key],**r['predictions'][key],pass_checkpoint=r['pass_checkpoint'],related_walls=';'.join(r['related_walls']),reason=r['reasoning']))
    for name,data in [('plan.csv',flat),('predictions.csv',forecasts)]:
        with (args.out/name).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader()
            writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in data)
    summary=dict(clusters=len(rows),source_r17p_clusters=len(old),source_r17r_families=len(feedback),
                 source_memberships_mapped=len(source_coverage),unique_plan_apps=len({k for r in rows for k in r['beneficiary_keys']}),
                 forecasts=len(forecasts),lane_clusters=dict(collections.Counter(r['lane'] for r in rows)),
                 counts={phase:dict(collections.Counter(r[phase] for r in forecasts)) for phase in ('J1','N1','U1')},
                 status='plan delivered; exact J1/N1 receipts and completed U1 shards pending',
                 inputs=inputs,read_only=True,board_actions=0)
    write(args.out/'results.json',summary)
    frozen=dict(frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),profile_status='feature-plan; release SHA binding pending',
                hashes={str(p.relative_to(args.out)):sha(p) for p in sorted(args.out.rglob('*')) if p.is_file()},
                generator_sha256=sha(Path(__file__)))
    write(args.out/'freeze.json',frozen)
    print(json.dumps({k:summary[k] for k in ['clusters','source_memberships_mapped','unique_plan_apps','counts']},ensure_ascii=False))


if __name__ == '__main__':
    main()
