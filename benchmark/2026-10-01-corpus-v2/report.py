"""Generate candidate tables from compact indexed identities and explicit priors."""

import argparse
import base64
from collections import Counter
import csv
import gzip
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_evidence():
    return json.loads(gzip.decompress(base64.b64decode((HERE/'selected-index.json.gz.b64').read_bytes())))


def prediction(entry):
    group = entry['group']
    manifest = entry['version']['manifest']
    permissions = {permission['name'] for permission in manifest.get('usesPermission', [])}
    risks = []
    checks = {
        'alarm/job/notification bridge': {'android.permission.SCHEDULE_EXACT_ALARM','android.permission.USE_EXACT_ALARM','android.permission.POST_NOTIFICATIONS','android.permission.RECEIVE_BOOT_COMPLETED'},
        'file/SAF/storage bridge': {'android.permission.READ_EXTERNAL_STORAGE','android.permission.WRITE_EXTERNAL_STORAGE','android.permission.MANAGE_EXTERNAL_STORAGE'},
        'network/bootstrap state': {'android.permission.INTERNET'},
        'audio/camera hardware paths': {'android.permission.CAMERA','android.permission.RECORD_AUDIO'},
        'account/content-provider client': {'android.permission.GET_ACCOUNTS','android.permission.READ_CONTACTS','android.permission.WRITE_CONTACTS','android.permission.READ_CALENDAR','android.permission.WRITE_CALENDAR'},
        'sensor/vibrator service': {'android.permission.VIBRATE','android.permission.ACTIVITY_RECOGNITION','android.permission.BODY_SENSORS'},
    }
    for label, requested in checks.items():
        if permissions & requested:
            risks.append(label)
    if manifest.get('nativecode'):
        risks.append('native sidecar/DT_NEEDED closure; library contents not inspected')
    if manifest.get('usesSdk', {}).get('targetSdkVersion',0) > 36:
        risks.append('target SDK beyond current Android 16 API 36 baseline')
    if group == 'priority':
        reason = 'Indexed ABI-free small local-app candidate; transfer prior from U7 View/local controls. DEX UI framework and startup calls still require APK scan.'
        profile = 'ABI-free local/View candidate'
        t20 = 'own-ui'
        suspected = []
    elif group == 'compose':
        reason = 'Published description explicitly names Jetpack Compose; investigate resource/theme, startup services and first-frame submission after APK preparation.'
        profile = 'Compose coverage'
        t20 = 'unknown'
        suspected = ['resource/theme','startup-service','first-frame']
    elif group == 'webview':
        reason = 'Published description explicitly names WebView; U7 has an unresolved WebViewFactory/provider cluster. Startup reachability is unproved.'
        profile = 'WebView coverage'
        t20 = 'unknown'
        suspected = ['webview-provider']
    else:
        reason = 'Published description explicitly names OpenGL/GLSL; U7 SurfaceView/owner failures warrant coverage. Exact surface creation and native imports need APK scan.'
        profile = 'GL coverage'
        t20 = 'unknown'
        suspected = ['surface-owner','native-closure']
    return dict(profile=profile,evidence_level='repository-index-manifest-and-published-metadata',
                first_wall='unknown',checkpoint='unknown',t20=t20,confidence='low-prior',
                suspected_wall_families=suspected,risks=risks,reason=reason,
                apk_scanned=False,source_language='unknown',androidx_view_classes='unknown',
                criterion='First bound U7 t20 screenshot signed by outer; terminal root by app PID first_fatal.py. Metadata absence cannot establish no blocker.')


def build(evidence):
    rows = []
    for entry in evidence['selected']:
        version = entry['version']
        manifest = version['manifest']
        package = entry['package']
        name = entry['metadata']['name'].get('en-US',package)
        rows.append(dict(package=package,name=name,group=entry['group'],version_name=manifest['versionName'],
                         version_code=manifest['versionCode'],apk_url=evidence['repo_address'].rstrip('/')+version['file']['name'],
                         fdroid_url='https://f-droid.org/en/packages/'+package+'/',
                         sha256=version['file']['sha256'],bytes=version['file']['size'],
                         signer_sha256=manifest['signer']['sha256'],nativecode=manifest.get('nativecode',[]),
                         min_sdk=manifest.get('usesSdk',{}).get('minSdkVersion',1),target_sdk=manifest.get('usesSdk',{}).get('targetSdkVersion'),
                         source_url=entry['metadata']['sourceCode'],license=entry['metadata']['license'],
                         coverage_cue=entry['coverage_cue'],prediction=prediction(entry),input_status='not-prepared'))
    rows.sort(key=lambda row:(row['group']!='priority',row['group'],row['bytes'],row['package']))
    return dict(schema_version=1,status='version-pinned-selection-with-static-metadata-priors',
                index=evidence['index'],entry=evidence['entry'],existing=evidence['existing'],
                selected_count=len(rows),groups=dict(Counter(row['group'] for row in rows)),
                apk_total_bytes=sum(row['bytes'] for row in rows),
                prediction_counts=dict(Counter(row['prediction']['t20'] for row in rows)),
                apk_scan_count=0,freeze_authorized=False,apps_json_changed=False,rows=rows,
                sources=['https://f-droid.org/docs/All_our_APIs/','https://f-droid.org/repo/index-v2.json','https://f-droid.org/repo/entry.jar'],
                handoff=['oc-t4: download exact APK URL; verify size SHA, APK signature and indexed signer fingerprint.',
                         'Resolve LAUNCHER activity, splits and full native inventory; reject ABI mismatch and quarantine problematic input without deleting originals.',
                         'Scan APK DEX/manifest/native contents before runtime prediction freeze; priority UI hypothesis may change to Compose/WebView/GL.',
                         'Record actual input root and full bms_batch resolve; create separate apps-v2.json, retain current apps.json.',
                         'Run the new corpus U7 baseline before combined N10/J8 U8; final lighting requires outer screenshot signoff.'])


CSV_FIELDS = ['package','name','group','version_name','version_code','apk_url','sha256','bytes','signer_sha256','nativecode','min_sdk','target_sdk','profile','first_wall','checkpoint','t20','confidence','apk_scanned','risks','reason','source_url']


def csv_text(result):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream,fieldnames=CSV_FIELDS,lineterminator='\n')
    writer.writeheader()
    for row in result['rows']:
        record = {field:row.get(field) for field in CSV_FIELDS}
        record.update({field:row['prediction'][field] for field in ['profile','first_wall','checkpoint','t20','confidence','apk_scanned','risks','reason']})
        for field in ['signer_sha256','nativecode','risks']:
            record[field] = json.dumps(record[field],ensure_ascii=False,separators=(',',':'))
        writer.writerow(record)
    return stream.getvalue()


def markdown(result):
    lines = ['# Corpus-v2: 100 new F-Droid candidates', '',
             'The earlier breadth corpus did not provide enough low-native candidates to reach the 100-light target. This selection adds 80 indexed ABI-free local-app candidates plus 20 explicit coverage samples: 10 Compose, 6 WebView, 4 GL. The existing 66-key manifest is retained; this task prepares a handoff list.', '',
             '## Identities and selection', '',
             '- Official index: '+str(result['index']['bytes'])+' bytes / '+str(result['index']['packages'])+' packages, SHA `'+result['index']['sha256']+'`.',
             '- `entry.jar` SHA `'+result['entry']['sha256']+'`; embedded entry.json index SHA/size match. This lane checked identity binding; cryptographic index-signature trust was not independently accepted here.',
             '- Existing `apps.json` SHA `'+result['existing']['sha256']+'`, '+str(result['existing']['key_count'])+' keys / '+str(len(result['existing']['packages']))+' distinct package IDs. Null X/Noice package fields were resolved from their actual input metadata before exclusion.',
             '- 100 distinct new package IDs and 100 distinct APK hashes, all in the pinned index; stable eligible preferred-signer versions, ABI-free or arm64-capable. Total APK bytes: '+str(result['apk_total_bytes'])+'.',
             '- Priority selection: no indexed nativecode, modest APK size, local notes/calculators/lists/timers/puzzles. These are View candidates; the index does not prove Java/Kotlin language, AndroidX classes or startup reachability.',
             '- Coverage labels use exact description tokens in the pinned index. Full versions/URLs/SHA/signers and per-app predictions: [CANDIDATES.csv](CANDIDATES.csv) / [results.json](results.json). Compact replay evidence: `selected-index.json.gz.b64`.', '',
             '## Static predictions and limits', '',
             '- This delivery scanned repository manifest metadata for all 100 candidates; **0 APKs scanned**. The 80 priority t20 `own-ui` entries are low-confidence transfer priors from signed U7 View/local controls. The 20 coverage t20 entries are `unknown`.',
             '- First-wall and checkpoint remain `unknown` for all 100 until APK preparation provides manifest/DEX/native evidence. Permission-derived service risks are listed per app, not asserted fatal causes.',
             '- WebView candidates carry the U7 provider risk; GL candidates carry SurfaceView/owner/native closure risk; Compose candidates exercise resource/theme/startup and first-frame paths. Framework inclusion alone does not prove launch use.',
             '- Input admission and actual t20 image signoff remain separate. Downloaded APKs and the 62 MB full index stay outside this public repository.', '',
             '## Candidate table', '',
             '| Package | Version / code | Group | APK SHA-256 | APK URL | t20 prior / static risks |',
             '|---|---|---|---|---|---|']
    for row in result['rows']:
        prior=row['prediction'];risks=', '.join(prior['risks']) or 'startup APIs not yet inspected'
        lines.append('| '+row['package']+' | '+row['version_name']+' / '+str(row['version_code'])+' | '+row['group']+' | `'+row['sha256']+'` | [APK]('+row['apk_url']+') | '+prior['t20']+' (low prior); '+risks+' |')
    lines.extend(['','## oc-t4 input handoff',''])
    for instruction in result['handoff']:
        lines.append('- '+instruction)
    lines.extend(['','## Replay and verification','',
                  '`python3 benchmark/2026-10-01-corpus-v2/test_selection.py -v` checks pinned identities, eligibility failures, package exclusion and deterministic output. `collect.py` optionally recollects from the supplied external index; `report.py` replays compact evidence without network.',
                  'Gate receipts and exact landing identities are recorded in `validation.json`; shared-document additions are in `documentation.json`.','',
                  'Sources: [F-Droid APIs](https://f-droid.org/docs/All_our_APIs/), [official index](https://f-droid.org/repo/index-v2.json), [signed entry](https://f-droid.org/repo/entry.jar).',''])
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--format',choices=['json','csv','markdown'],default='json')
    args=parser.parse_args()
    result=build(load_evidence())
    if args.format=='csv':
        print(csv_text(result),end='')
    elif args.format=='markdown':
        print(markdown(result),end='')
    else:
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
