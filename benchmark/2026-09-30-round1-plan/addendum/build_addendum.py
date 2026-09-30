#!/usr/bin/env python3
"""Read the old evidence again; never amend the accepted forecast."""
import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=ROOT.parent
FREEZE=HERE.parent/'freeze-v1'
FEEDBACK=ROOT/'benchmark/2026-09-29-static-wall-prediction/unified-r17r-feedback'
sys.path.insert(0,str(FEEDBACK.parent))
from scan_classes_v3 import dex_classes


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')


def immich_classes(out):
    old=json.loads((ROOT/'benchmark/2026-09-30-background-start-prospective/evidence/fd-immich.json').read_text())
    apk=Path(old['apk'])
    if sha(apk)!=old['apk_sha256']:raise ValueError('Immich input changed')
    classes={}
    with zipfile.ZipFile(apk) as z:
        for dex in z.namelist():
            if re.fullmatch(r'classes\d*\.dex',dex):
                raw=z.read(dex)
                for row in dex_classes(raw):
                    if row['class'] in {'d7/c','b7/a','A2/b','e8/y'}:classes[row['class']]={**row,'dex':dex,'dex_sha256':hashlib.sha256(raw).hexdigest()}
    expected=json.loads((ROOT/'benchmark/2026-09-30-r17op-prospective/freezes/v3/evidence/v3c-package.json').read_text())['files']
    jarroot=BASE/'westlake-generation-v3c-candidate/payload/android/framework'
    jars=[p for p in sorted(jarroot.glob('*.jar')) if p.name!='oh-adapter-runtime.jar']
    jars.append(BASE/'vm-copies/r17r-dd4f0eae/oh-adapter-runtime.jar')
    target='android/net/nsd/NsdManager$DiscoveryListener';inputs=[];definitions=[]
    for jar in jars:
        digest=sha(jar);pin=expected.get('payload/android/framework/'+jar.name)
        if jar.name=='oh-adapter-runtime.jar':
            runtime_pin=json.loads((FEEDBACK/'results.json').read_text())['profile_audit']['actual_jar_sha256']
            if digest!=runtime_pin:raise ValueError('wrong runtime JAR')
        elif digest!=pin:raise ValueError('package JAR mismatch: '+jar.name)
        inputs.append({'path':str(jar),'sha256':digest,'matches_v3c_package':digest==pin})
        with zipfile.ZipFile(jar) as z:
            for dex in z.namelist():
                if re.fullmatch(r'classes\d*\.dex',dex):
                    definitions.extend(dict(row,jar=str(jar),dex=dex) for row in dex_classes(z.read(dex)) if row['class']==target)
    result=dict(apk=str(apk),apk_sha256=sha(apk),app_classes=classes,required_interface=target,
        definitions_in_supplied_jars=definitions,jar_inputs=inputs,
        scope='v3c package-pinned framework JARs plus exact r17r replacement, definition scan only. Not a live boot-classpath dump, runtime Class.forName result, or proof that this is the sole verifier cause.')
    save(out/'immich-class-surface.json',result)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=HERE/'v1');args=parser.parse_args()
    out=args.out
    if out.exists():raise ValueError('addenda are versioned; do not overwrite')
    receipt=json.loads((FREEZE/'freeze.json').read_text())
    for name,digest in receipt['hashes'].items():
        if sha(FREEZE/name)!=digest:raise ValueError('frozen file changed: '+name)
    forecasts={r['key']:r for r in json.loads((FREEZE/'predictions.json').read_text())}
    original={r['key']:r for r in json.loads((FEEDBACK/'first-failures.json').read_text())}
    out.mkdir(parents=True);(out/'evidence').mkdir()
    static=immich_classes(out)
    cases=[
      ('A01','fd-libretube','app 内部 / platform value boundary','J1 / cc-t3 (triage)','unresolved producer',[(44766,44773),(51138,51139)],
       'Coil DiskCache.Builder.maxSizeBytes rejects size <= 0 in LibreTubeApp.onCreate; later boot TagSoup method also fails.',
       'Log does not record supplied capacity, disk statistics, or preference value; cannot blame StatFs/native storage or an app constant.',
       'Resolve the argument producer at onCreate:420; record capacity, free/total space and preference before assigning JAR/native repair.'),
      ('A02','fd-immich','JAR / framework class availability','J1 / cc-t3; boot / oc-t4 if loader scope requires','strong static candidate; live cause unconfirmed',[(34562,34578)],
       'WorkManagerInitializer triggers verification of A2.b; d7.c is unresolved. APK defines d7/c extending b7/a and implementing NsdManager.DiscoveryListener; that interface is absent from the supplied v3c+r17r definition union.',
       'A2.b/d7.c are not absent APK classes. Missing interface is a candidate explanation, not proof of a verifier bug; do not bypass verification. Separate later libflutter failure remains.',
       'J1 check the required public interface in the app/boot loader and restore its real signature if missing; rerun provider initialization before testing Flutter.'),
      ('A03','fd-breezyweather','app 内部 observed frame; root unknown','J1 / cc-t3 (triage)','unresolved null producer',[(45227,45239)],
       'Null dereference at pa0.G -> zt constructor -> app MainActivity.onCreate.',
       'Obfuscated stack does not identify the null object or a specific system service.',
       'Trace the null register producer in pa0.G / zt constructor before adding a framework service stub.'),
      ('A03','fd-wifianalyzer','app 内部 observed frame; root unknown','J1 / cc-t3 (triage)','unresolved null producer',[(27175,27179)],
       'getClass null in MainActivity.onCreate at source position 78.',
       'Nearby service-proxy creation is not evidence that WifiManager or LocationManager returned null.',
       'Resolve the getClass receiver in this exact APK onCreate; route only after the receiver source is known.'),
      ('A03','fd-catima','app widget / JAR service boundary','J1 / cc-t3 (triage)','widget path known; null producer unknown',[(35210,35215)],
       'ListWidget.updateAll fails in MainActivity.updateLoyaltyCardList/onResume.',
       'The widget path narrows scope but does not prove AppWidgetManager was the null object.',
       'Inspect ListWidget.updateAll receiver creation and appwidget-service result; retain unknown until tied to the dereference.'),
      ('A05','fd-feeder','boot','boot / oc-t4','confirmed missing boot method',[(56995,57014),(57028,57029)],
       'Main-thread W-ROOM-SURVIVE UNCAUGHT: NetworkRequest.getNetworkSpecifier missing in adapter-mainline-stubs.jar; JobInfo.Builder.build -> periodic RSS job; System.exit(1).',
       'Absence of J_invokeStaticMain_main_threw was an extractor blind spot, not absence of fatal failure. No JAR-only repair is assumed.',
       'Provide the selected boot NetworkRequest method; require JobInfo.Builder.build and periodic-sync setup to return. Coordinate with other boot API gaps.'),
      ('A05','ppsspp','native','N1 / cx-t0','confirmed loader failure and exit',[(22763,22764),(24943,24943)],
       'PpssppActivity catches libppsspp_jni load failure: missing libGLESv2 in app namespace; process then calls System.exit(-1).',
       'Library present on system disk does not prove app namespace visibility. Do not call this an unidentified native crash.',
       'Add PPSSPP to N03 app-native namespace validation; require libppsspp_jni load to complete and Activity initialization to proceed.'),
      ('A05','fd-mobile','native','N1 / cx-t0 (FZ-003 retention)','API failure confirmed; UI causal link unknown',[(58215,58224),(58568,58573)],
       'Background pool worker hits AssetManager.nativeOpenAssetFd Implement me; B8-UEH explicitly keeps process alive. View later has 1200x1920 geometry and drew-once flags.',
       'This is not a main-thread fatal or proof that asset FD alone lights the app. U0 already includes asset53; its effect on this app has not been read.',
       'Validate fd-mobile as an additional FZ-003 API consumer under U0/N1; check worker completion and independent outer t20 image. Do not re-edit the frozen helper.'),
      ('A05','termux','app / JAR lifecycle boundary','J1 / cc-t3 (triage)','finish path confirmed; initiating cause unknown',[(22597,22597),(24957,24957),(25002,25003)],
       'Bind returns OK; finishActivity reaches OH TerminateAbility rc=0; subsequent activity state is finished, not window-added, decor null.',
       'No sampled app stack explains why finish was requested. This is not evidence of a renderer crash, and rc=0 is not evidence of a replacement Activity being displayed.',
       'Identify the finish caller and any intended successor/initial setup Activity; compare resolved launcher and start/finish lifecycle before touching graphics.'),
      ('INPUT01','fd-seal','host harness input validation','cx-bms (input/assembly)','confirmed pre-install gate',[],
       'record clicked=false, install=null: native sidecar libaria2c.zip.so is rejected as non-AArch64 shared ELF.',
       'No app hilog exists for this attempted launch. This run did not reach BMS, so its failure cannot be assigned to N1 or frozen installer binaries.',
       'Reconcile the exact previously approved archive-as-data exception with sidecar assembly; preserve hashes and strict checks for other files.'),
      ('INPUT01','toutiao','host harness input validation','cx-bms (input/assembly)','confirmed pre-install gate',[],
       'record clicked=false, install=null: native sidecar libcvt.so is rejected as non-AArch64 shared ELF.',
       'No app hilog exists for this attempted launch; do not conflate the host sidecar gate with prior BMS manifest/native validation errors.',
       'Reconcile the exact approved ABI/input exception with sidecar assembly, without weakening FZ-001 or silently changing APK bytes.'),
      ('INPUT02','subwaysurfers','host harness identity validation','cx-bms (input pin reconciliation)','confirmed pre-install gate',[],
       'record clicked=false, install=null: pinned identity changed: apk_sha256.',
       'The record preserves the expected pin; it does not establish the replacement APK hash. No launch or app fatal is present.',
       'Read app-input and actual APK SHA, reconcile authorized cohort identity, and create a new identity receipt; do not rewrite the frozen forecast pin.'),
    ]
    rows=[]
    for group,key,layer,lane,confidence,ranges,observation,boundary,next_step in cases:
        old=original[key];path=Path(old['log']);evidence=[]
        if ranges:
            raw=path.read_text(errors='replace').splitlines()
            if sha(path)!=old['log_sha256']:raise ValueError('hilog changed: '+key)
            for lo,hi in ranges:
                evidence.extend({'line':i,'text':raw[i-1]} for i in range(lo,min(hi,len(raw))+1))
        else:
            path=Path(old['record']);raw=path.read_text().splitlines()
            evidence=[{'line':i,'text':s} for i,s in enumerate(raw,1) if any(v in s for v in ['"clicked"','"install"','"error"','"apk_sha256"'])]
        save(out/'evidence'/(key+'.json'),dict(source=str(path),sha256=sha(path),target_pids=old['pids'],lines=evidence))
        rows.append(dict(cluster_id=group,key=key,layer=layer,lane=lane,confidence=confidence,observation=observation,
                         boundary=boundary,next_step=next_step,evidence=str(path)+':'+str(evidence[0]['line']),
                         evidence_snapshot='evidence/'+key+'.json',source_sha256=sha(path),
                         frozen_prediction={v:forecasts[key][v] for v in ['J1','N1','U1']},prediction_changed=False))
    batch=ROOT/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py';lines=batch.read_text().splitlines()
    save(out/'evidence/host-input-gates.json',dict(source=str(batch),sha256=sha(batch),
         scope='Current local caller matching the exact exception text, not a provenance claim for the historical runner binary.',
         lines=[{'line':i,'text':lines[i-1]} for a,b in [(113,117),(158,165)] for i in range(a,b+1)]))
    save(out/'addendum.json',dict(freeze_sha256=sha(FREEZE/'freeze.json'),scope='12 apps in six unresolved/input entries; layer/owner/checkpoint supplement only',
         groups=sorted({r['cluster_id'] for r in rows}),rows=rows,forecast_mutations=0))
    with (out/'plan-addendum.csv').open('w') as f:
        fields=['cluster_id','key','layer','lane','confidence','observation','boundary','next_step','evidence','prediction_changed']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in rows)
    save(out/'results.json',dict(groups=6,apps=len(rows),frozen_files_verified=len(receipt['hashes']),frozen_predictions_changed=False,
         newly_localized=['fd-feeder:boot','ppsspp:native','fd-mobile:native API failure, lighting unknown'],
         strong_candidate=['fd-immich:missing NSD listener definition; runtime class resolution unverified'],
         confirmed_host_input_gates=['fd-seal','toutiao','subwaysurfers'],
         root_not_proven=['fd-libretube','fd-breezyweather','fd-wifianalyzer','fd-catima','termux'],
         board_actions=0,source_profile='unified-r17r historical evidence; no U0/J1/N1 result read'))
    print('6 groups / 12 apps; immutable forecast verified; interface definitions:',len(static['definitions_in_supplied_jars']))


if __name__=='__main__':main()
