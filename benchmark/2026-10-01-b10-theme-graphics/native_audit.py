"""Audit identity-pinned constructor tables and compiled throw paths, not filenames."""

import argparse
import base64
import gzip
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

import rules
import collect

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V1=ROOT/'benchmark/2026-10-01-corpus-v2/apk-scan-v1'


def load_profile():
    return json.loads(gzip.decompress(base64.b64decode((V1/'runtime-profile.json.gz.b64').read_bytes())))


def symbols(path, readelf):
    text=subprocess.check_output([str(readelf),'-s','-W',str(path)],text=True)
    output={}
    for line in text.splitlines():
        match=re.match(r'\s*\d+: ([0-9a-f]+)\s+(\d+)\s+FUNC\s+\S+\s+\S+\s+(\S+)\s+(\S+)',line)
        if match and match[3]!='UND' and int(match[2]):
            output.setdefault(int(match[1],16),dict(size=int(match[2]),symbol=match[4]))
    return output


def disassemble(path, address, size, objdump):
    text=subprocess.check_output([str(objdump),'-d','--start-address='+hex(address),'--stop-address='+hex(address+size),str(path)],text=True)
    text=text.replace(str(path),'$DEPLOYED_LIBRARY')
    instructions=[]
    for number,line in enumerate(text.splitlines(),1):
        match=re.match(r'\s*([0-9a-f]+):\s+[0-9a-f]+\s+(.+)',line)
        if match:
            instructions.append(dict(address=int(match[1],16),line=number,text=match[2].strip()))
    return dict(address=hex(address),size=size,sha256=collect.digest(text.encode()),instructions=instructions)


def creators(profile):
    return {name:item for name,item in profile['methods'].items() if rules.NATIVE_FAMILY.match(name)
            and name.endswith(')J') and not any(word in name for word in ['Finalizer','Destructor'])}


def java_scope(jar, dexdump, owners):
    rows={}
    inventory=[]
    with zipfile.ZipFile(jar) as archive,tempfile.TemporaryDirectory(prefix='b10-framework-dex-') as directory:
        for member in sorted(archive.namelist()):
            if not re.fullmatch(r'classes\d*\.dex',member):
                continue
            payload=archive.read(member)
            path=Path(directory)/member
            path.write_bytes(payload)
            process=subprocess.Popen([str(dexdump),'-d',str(path)],stdout=subprocess.PIPE,text=True,errors='replace')
            owner=None
            block=[]
            selected=[]
            for line in process.stdout:
                if "Class descriptor  : '" in line:
                    if owner in owners:
                        selected.extend(block)
                    owner=line.split("'")[1]
                    block=[]
                if owner in owners:
                    block.append(line)
            if owner in owners:
                selected.extend(block)
            process.stdout.close()
            if process.wait():
                raise ValueError('Framework DEX parse failed')
            unused,methods=collect.parse_dex(selected,member)
            for identifier,method in methods.items():
                relevant=[call for call in method['sites'] if call['name'].startswith('native')]
                if relevant:
                    rows[identifier]=dict(method=identifier,dex=member,native_calls=relevant,
                        initiation='eager-constructor-native-call' if method['name']=='<init>' else 'non-constructor-native-call; typically lazy createNativeInstance/factory, caller timing unknown')
            inventory.append(dict(member=member,sha256=collect.digest(payload)))
    return dict(methods=rows,dex=inventory,limits='Filtered framework class parse uses class-relative dump lines, not full-dump coordinates; byte hashes pin the originals')


def audit(workspaces):
    profile=load_profile()
    expected=ROOT/'benchmark/2026-10-01-u7-prospective/v1/expected-run.json'
    physical=lambda value:Path(value.replace('$WORKSPACES',str(workspaces)).replace('$HOME',str(Path.home())))
    wanted={name:item for name,item in profile['inputs'].items() if name.endswith(('/libhwui.so','/liboh_android_runtime.so','/framework.jar'))}
    files={name:physical(item['path']) for name,item in wanted.items()}
    script=workspaces/'westlake-harness/scripts/lab/artifact_identity.py'
    result=subprocess.run(['python3',str(script),'--expected',str(expected),*[str(path) for path in files.values()]],capture_output=True,text=True)
    if result.returncode or any(not line.startswith('DEPLOYED ') for line in result.stdout.splitlines()):
        raise ValueError('Artifact identity refused: '+result.stdout)
    if len(files)!=3 or any(collect.digest(path.read_bytes())!=wanted[name]['sha256'] for name,path in files.items()):
        raise ValueError('Missing or changed U7 artifacts')
    llvm=Path('/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin')
    objdump=llvm/'llvm-objdump'
    readelf=llvm/'llvm-readelf'
    maps={name:symbols(path,readelf) for name,path in files.items() if name.endswith('.so')}
    rows=[]
    for identifier,item in sorted(creators(profile).items()):
        implementations=[]
        for entry in item['evidence']:
            name=entry.get('library','').removeprefix('U7_DEPLOYED_PROFILE/')
            if name not in files or not entry.get('function_address'):
                continue
            address=int(entry['function_address'],16)
            symbol=maps[name].get(address)
            if not symbol:
                implementations.append(dict(library=name,status='unknown-function-boundary',table_address=entry['table_address']))
                continue
            body=disassemble(files[name],address,symbol['size'],objdump)
            implementations.append(dict(library=name,library_sha256=wanted[name]['sha256'],symbol=symbol['symbol'],
                compiled_table=dict(address=entry['table_address'],function_address=entry['function_address'],method=entry['method'],signature=entry['signature']),
                source_attribution=entry.get('source',[]),body=body,throw=rules.throw_class(body['instructions'])))
        rows.append(dict(id=identifier,owner=identifier.split('.')[0],jni_status=item['status'],jni_reason=item['reason'],
                         implementations=implementations,
                         runtime_registration='table/source attribution only; actual RegisterNatives execution not inferred'))
    jar=next(path for name,path in files.items() if name.endswith('/framework.jar'))
    java=java_scope(jar,Path.home()/'Library/Android/sdk/build-tools/37.0.0/dexdump',{'L'+row['owner']+';' for row in rows})
    return dict(schema='b10-u7-graphics-constructors-v1',baseline='U7 before N10/J8/T7e',rows=rows,java=java,
        artifacts={name:dict(path=wanted[name]['path'],sha256=wanted[name]['sha256']) for name in files},
        artifact_identity=dict(exit_code=result.returncode,expected_sha256=collect.digest(expected.read_bytes()),
            stdout=result.stdout.replace(str(workspaces),'$WORKSPACES'),tool_sha256=collect.digest(script.read_bytes())),
        runtime_profile_sha256=collect.digest((V1/'runtime-profile.json.gz.b64').read_bytes()),
        disassembly_tools={str(path.name):collect.digest(path.read_bytes()) for path in [objdump,readelf]},
        audit_dependencies={str(path.relative_to(ROOT)):collect.digest(path.read_bytes()) for path in [Path(__file__),HERE/'rules.py',HERE/'collect.py']},
        limitations='Compiled code proves local direct throw behavior, not arbitrary transitively called Skia provider behavior or every Java caller argument; no source/registration string guessing')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspaces',type=Path,default=Path(os.environ.get('WORKSPACES',ROOT.parent)))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.workspaces)
    raw=json.dumps(result,sort_keys=True,indent=2).replace(str(args.workspaces),'$WORKSPACES')
    args.output.write_text(raw+'\n')
    print('identity',result['artifact_identity']['exit_code'],'constructors',len(result['rows']),
          'unconditional',[row['id'] for row in result['rows'] if any(entry.get('throw',{}).get('status')=='unconditional-normal-path-direct-throw' for entry in row['implementations'])])


if __name__=='__main__':
    main()
