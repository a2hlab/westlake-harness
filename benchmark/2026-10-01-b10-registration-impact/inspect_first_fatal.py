"""Read-only disassembly of exact U8 first-fatal callsites and register operands."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
TOOLS = Path('/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin')
SKIA_SHA = 'caa86d58671eef0079cdcfa60cf943c6cda6ee7934ecfdf59bf37df754a2abe4'
SKIA_ID = '2f7219f228e1e8c11205d5c787f8e153'
GLMARK_SHA = 'af99ef0fe7a4723020ef7f29eba2606dc46b32f40343aae519d3d4118eaf1b14'


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def require(payload, pin):
    if sha(payload) != pin:
        raise ValueError('First-fatal artifact SHA drift')


def crash_operand(registers, fault_address):
    if registers['x8'] != fault_address:
        raise ValueError('Fault address does not match ldr operand')
    return dict(fault_address=hex(fault_address),dereferenced_vtable=hex(registers['x8']),
        resource_pointer=hex(registers['x0']),resource_index=registers['x22'],
        context_pointer=hex(registers['x20']),cache_pointer=hex(registers['x21']),trace_pointer=hex(registers['x19']),
        null_pointer=registers['x8']==0,resource_pointer_eight_byte_aligned=registers['x0']%8==0,
        upstream_corruption_cause='unknown: no allocation/free/write provenance available')


def registers(text):
    return {name:int(value,16) for name,value in re.findall(r'\b(x\d+):([0-9a-fA-F]{16})\b',text)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspaces',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    known = json.loads((HERE/'known-evidence.json').read_text())
    bound = {row['key']:row for row in known['rows']}
    row = bound['cv2-com-ath0-rpn']
    hilog = args.workspaces/row['source']/'hilog.txt'
    payload = hilog.read_bytes()
    require(payload,row['binding']['hilog_sha256'])
    lines = payload.decode(errors='replace').splitlines()
    excerpt = '\n'.join(f'{index}: {lines[index-1]}' for index in range(47171,47200))+'\n'
    (args.output/'ath0-registers.txt').write_text(excerpt)
    operand = crash_operand(registers(excerpt),int(re.search(r'SEGV_MAPERR\)@(0x[0-9a-f]+)',excerpt)[1],16))
    skia = args.workspaces/'westlake-harness-bms-deploy/bms/src/.work/b68-generation/oh/out/wukong100/packages/phone/system/lib64/platformsdk/libskia_canvaskit.z.so'
    require(skia.read_bytes(),SKIA_SHA)
    notes = subprocess.check_output([str(TOOLS/'llvm-readelf'),'-n',str(skia)],text=True)
    if 'Build ID: '+SKIA_ID not in notes or SKIA_ID not in excerpt:
        raise ValueError('Crash/binary Skia BuildID mismatch')
    apk = args.workspaces/'westlake-inputs/corpus-v2/apks/org.linaro.glmark2_2.apk'
    consumers = json.loads((HERE/'CONSUMERS.json').read_text())
    app = next(item for item in consumers['apps'] if item['key']=='cv2-org-linaro-glmark2')
    require(apk.read_bytes(),app['apk_sha256'])
    with zipfile.ZipFile(apk) as archive:
        native = archive.read('lib/arm64-v8a/libglmark2-android.so')
    require(native,GLMARK_SHA)
    native_path = args.output/'libglmark2-android.so'
    native_path.write_bytes(native)
    library_root = args.workspaces/'westlake-generation-u8-j9-t7e/native/payload/android/lib64'
    providers = [library_root/name for name in ['liboh_android_runtime.so','libhwui.so','libandroid.so']]
    identity = subprocess.run(['python3',str(args.workspaces/'westlake-harness/scripts/lab/artifact_identity.py'),'--expected',str(HERE/'expected-u8.json'),*[str(item) for item in providers]],capture_output=True,text=True)
    if identity.returncode or len(identity.stdout.splitlines())!=3 or not all(line.startswith('DEPLOYED ') for line in identity.stdout.splitlines()):
        raise ValueError('First-fatal provider artifact identity refused')
    requests = [('glmark-scene-info.txt',native_path,0xad60c,0xadc68),
        ('libandroid-converter.txt',library_root/'libandroid.so',0x7d9d8,0x7d9f0),
        ('runtime-converter.txt',library_root/'liboh_android_runtime.so',0x1daa48,0x1daa60),
        ('skia-dump.txt',skia,0x10e9d64,0x10e9e60)]
    evidence = {}
    for name,library,start,stop in requests:
        output = subprocess.check_output([str(TOOLS/'llvm-objdump'),'-d','--demangle',f'--start-address={start}',f'--stop-address={stop}',str(library)],text=True)
        output = output.replace(str(args.workspaces),'$WORKSPACES').replace(str(args.output),'$OUT')
        (args.output/name).write_text(output)
        evidence[name] = sha(output.encode())
    glmark_text = (args.output/'glmark-scene-info.txt').read_text()
    if not re.search(r'ad648:.*\bbl\s+.*AAssetManager_fromJava@plt',glmark_text):
        raise ValueError('Glmark crash callsite changed')
    result = dict(schema='b10-native-first-fatal-followup-v1',identity_exit=identity.returncode,
        glmark=dict(apk_sha256=app['apk_sha256'],library_sha256=GLMARK_SHA,callsite='0xad648 = native_getSceneInfo + 60',
            target='AAssetManager_fromJava@plt',class_name='android/content/res/AssetManager',field='mObject',signature='J',
            lookup_source='AOSP14r1 android_util_AssetManager.cpp:1564; U8 donor android_util_AssetManager_aosp.cpp:1577',
            JNI_GetFieldID_table_offset=752,JNI_GetLongField_table_offset=808,
            direct_GetFieldID_table_load_in_scene_function=bool(re.search(r'ldr\s+x\d+, \[x\d+, #752\]',glmark_text)),
            mechanism='Converter loads gAssetManagerOffsets.mObject then BR tail-calls GetLongField, preserving caller LR and omitting converter stack frame',
            missing_field_id_not_proof_of_missing_Java_field=True,actual_cache_provider_owner='unknown; resolved GOT/namespace not captured'),
        ath0=dict(skia_sha256=SKIA_SHA,skia_build_id=SKIA_ID,hilog_sha256=row['binding']['hilog_sha256'],
            source=row['source'],pc_relative='0x10e9da0',instruction='ldr x8, [x8]',
            object='fResourceCache->fNonpurgeableResources[1] virtual dispatch',**operand),
        evidence_sha256=evidence,tool_sha256={name:sha((TOOLS/name).read_bytes()) for name in ['llvm-objdump','llvm-readelf']},
        limits=['Skia source-to-object mapping is supported by same-b68 source and exact binary BuildID, not a cold rebuild',
            'Invalid resource/vtable operand is observed; use-after-free, layout mismatch and prior writer are not distinguished',
            'No device or runtime-memory write, patch or repair performed'])
    (args.output/'NATIVE-FIRST-FATAL.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    native_path.unlink()
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':
    main()
