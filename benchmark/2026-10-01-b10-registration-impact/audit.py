"""Registration dispatch, original initializer coordinates, and distinct ELF owners."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAIN_SHA = 'a001929dc40858bbbd1d8f883bf2a8d6c8bdb63c1e1827a4b0f7a2275278a6b2'
PINNED = {'liboh_android_runtime.so':'216b68fbb3a40b5ac7a90b726f6d8184fa7cdba848ccde56c809abd400a660df',
    'libhwui.so':'be59260f93b3debe1ad64cc8e7b6b0575e5be04794b46f8eb876436d1ebc9b74',
    'libandroid.so':'9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db'}
INITIALIZER = re.compile(r'(?:\b(?:g[A-Za-z0-9_]*(?:Offsets|ClassInfo)|g[A-Za-z0-9_]+(?:_class|_field|_method))\b|FindClass|Get(?:Static)?(?:Field|Method)ID|NewGlobalRef|setJavaVM|RegisterNatives|registerNativeMethods|\binit\w*\s*\()')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(data, pin):
    if sha(data) != pin:
        raise ValueError('Registration source identity drift')


def comments(text):
    expression = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/'
    return re.sub(expression,lambda match: ''.join('\n' if value=='\n' else ' ' for value in match[0]) if match[0].startswith(('/',)) else match[0],text)


def body_end(text, start):
    masked = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',lambda match:' '*len(match[0]),text)
    depth = 0
    for index in range(start,len(masked)):
        if masked[index]=='{':
            depth += 1
        elif masked[index]=='}':
            depth -= 1
            if depth==0:
                return index+1
    raise ValueError('Unbalanced source function/table')


def dispatch(text):
    stripped = comments(text)
    rows = []
    for table in ['kRegJNI','kRegJNI_GL','kHwuiRegFns']:
        found = re.search(r'\b'+table+r'\s*\[\s*\]\s*=\s*\{',stripped)
        if not found:
            continue
        start = found.end()-1
        stop = body_end(stripped,start)
        pattern = r'\{\s*"([^"\n]+)"\s*,\s*(?:"([^"\n]+)"|(?:::)?([A-Za-z0-9_:]+))\s*\}'
        for entry in re.finditer(pattern,stripped[start:stop]):
            name = entry[3].split('::')[-1] if table!='kHwuiRegFns' else re.search(r'(register_android_\w+?)(?:EP7_JNIEnv|P7_JNIEnv)',entry[2])[1]
            rows.append(dict(function=name,label=entry[1],table=table,line=stripped.count('\n',0,start+entry.start())+1,
                symbol=entry[2] or entry[3],mode='dlsym-whole-function-delegation' if table=='kHwuiRegFns' else 'direct-registration-dispatch'))
    return rows


def functions(text):
    stripped = comments(text)
    output = []
    for match in re.finditer(r'\b(register_android_\w+)\s*\(\s*JNIEnv\s*\*\s*\w*\s*\)\s*\{',stripped):
        start = match.end()-1
        stop = body_end(stripped,start)
        first = stripped.count('\n',0,match.start())+1
        last = stripped.count('\n',0,stop)+1
        lines = text.splitlines()
        body = '\n'.join(lines[first-1:last])
        effects = [dict(line=number,text=line.strip()) for number,line in enumerate(lines[first-1:last],first) if INITIALIZER.search(comments(line))]
        output.append(dict(function=match[1],first_line=first,last_line=last,body_sha256=sha(body.encode()),body=body,
            direct_initializer_lines=effects,limitation='Direct body evidence only; helper initialization and external entry ordering require separate call-context audit'))
    return output


def cache_writes(body):
    return sorted(set(re.findall(r'\b(g[A-Za-z_0-9]+(?:\.[A-Za-z_0-9]+)*)\s*=(?!=)',comments(body))))


def ported(root):
    output = {}
    for path in sorted(root.rglob('*.cpp')):
        payload = path.read_bytes()
        for function in functions(payload.decode(errors='replace')):
            output.setdefault(function['function'],[]).append(dict(file=str(path.relative_to(root)),file_sha256=sha(payload),**function))
    return output


def reference(root, provenance):
    verified = provenance.get('revision')=='refs/tags/android-14.0.0_r1' and bool(re.fullmatch(r'[0-9a-f]{40}',provenance.get('frameworks_base_commit','')))
    if not verified:
        raise ValueError('Unverified AOSP14r1 reference version')
    output = {}
    contexts = []
    for relative,pin in provenance['files'].items():
        path = root/relative
        payload = path.read_bytes()
        verify(payload,pin)
        text = payload.decode(errors='replace')
        for function in functions(text):
            output.setdefault(function['function'],[]).append(dict(file=relative,file_sha256=pin,**function))
        for number,line in enumerate(comments(text).splitlines(),1):
            if 'setJavaVM' in line:
                contexts.append(dict(file=relative,line=number,text=text.splitlines()[number-1].strip(),file_sha256=pin))
    return output,contexts


def symbols(path, readelf):
    text = subprocess.check_output([str(readelf),'-s','-W',str(path)],text=True)
    output = {}
    for line in text.splitlines():
        match = re.match(r'\s*\d+: ([0-9a-f]+)\s+(\d+)\s+(\w+)\s+\w+\s+\w+\s+(\S+)\s+(\S+)',line)
        if match and match[4]!='UND':
            output[match[5]] = dict(address='0x'+match[1].lstrip('0') if int(match[1],16) else '0x0',size=int(match[2]),type=match[3])
    return output


def function_name(symbol):
    if symbol.startswith('register_'):
        return symbol
    match = re.search(r'(register_\w+?)(?:EP7_JNIEnv|P7_JNIEnv)$',symbol)
    return match[1] if match else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspaces',type=Path,required=True)
    parser.add_argument('--reference-root',type=Path)
    parser.add_argument('--reference-provenance',type=Path)
    parser.add_argument('--ported-source-root',type=Path)
    parser.add_argument('--expected',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    generation = args.workspaces/'westlake-generation-u8-j9-t7e'
    libraries = {name:generation/'native/payload/android/lib64'/name for name in PINNED}
    tool = args.workspaces/'westlake-harness/scripts/lab/artifact_identity.py'
    receipt = subprocess.run(['python3',str(tool),'--expected',str(args.expected),*[str(path) for path in libraries.values()]],capture_output=True,text=True)
    if receipt.returncode or not all(line.startswith('DEPLOYED ') for line in receipt.stdout.splitlines()) or len(receipt.stdout.splitlines())!=3:
        raise ValueError('U8 deployed artifact identity refused')
    for name,path in libraries.items():
        verify(path.read_bytes(),PINNED[name])
    main_path = generation/'native/native-checks/n4-order-runtime.cpp'
    verify(main_path.read_bytes(),MAIN_SHA)
    dispatches = dispatch(main_path.read_text())
    dispatches.append(dict(function='register_android_graphics_Typeface',label='Typeface real registration branch',table='separate-Typeface-proxy',line=None,
        symbol='_Z34register_android_graphics_TypefaceP7_JNIEnv',mode='dlsym-whole-function-delegation'))
    readelf = Path('/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/llvm-readelf')
    binary_symbols = {name:symbols(path,readelf) for name,path in libraries.items()}
    originals,contexts = reference(args.reference_root,json.loads(args.reference_provenance.read_text())) if args.reference_root and args.reference_provenance else ({},[])
    ports = ported(args.ported_source_root) if args.ported_source_root else {}
    rows = []
    for item in dispatches:
        target = 'libhwui.so' if item['mode']=='dlsym-whole-function-delegation' else 'liboh_android_runtime.so'
        owners = [dict(library=library,library_sha256=PINNED[library],symbol=symbol,**value) for library,table in binary_symbols.items() for symbol,value in table.items()
                  if library==target and function_name(symbol)==item['function'] and value['type']=='FUNC'
                  and (item['table']!='kHwuiRegFns' or symbol==item['symbol'])]
        matches = originals.get(item['function'],[])
        implementations = ports.get(item['function'],[]) if item['mode']=='direct-registration-dispatch' else []
        original_writes = sorted({name for match in matches for name in cache_writes(match['body'])})
        ported_writes = sorted({name for match in implementations for name in cache_writes(match['body'])})
        rows.append(dict(**item,provider_symbols=owners,AOSP14r1=matches,
            ported_source_candidates=implementations,original_direct_cache_writes=original_writes,ported_direct_cache_writes=ported_writes,
            original_cache_identifiers_not_written_in_ported_body=sorted(set(original_writes)-set(ported_writes)) if implementations else [],
            initializer_status='whole-provider-function-delegated; original in-function effects not bypassed by dlsym itself' if item['mode']=='dlsym-whole-function-delegation' else
                'replacement-source-inventory; missing exact identifier is a candidate, helpers/renaming/late lookup and binary linkage require review' if implementations else 'replacement-source-unverified',
            comparison='original-entrypoint-found-not-a-skipped-cache-proof' if matches else 'reference-unverified-or-entrypoint-not-found',
            skipped_initializer_claim=None,causal=False))
    cache_owners = [dict(library=library,library_sha256=PINNED[library],symbol=symbol,**value) for library,table in binary_symbols.items() for symbol,value in table.items()
        if any(token in symbol for token in ['Offsets','ClassInfo','setJavaVM','AAssetManager_fromJava','AndroidBitmap_','ANativeWindow_fromSurface','AHardwareBuffer_fromHardwareBuffer','ASurfaceTexture_fromSurfaceTexture'])]
    result = dict(schema='b10-registration-dispatch-v1',rows=rows,entries=len(rows),source_main=dict(path='westlake-generation-u8-j9-t7e/native/native-checks/n4-order-runtime.cpp',sha256=MAIN_SHA),
        reference_verified=bool(originals),reference_context_initializers=contexts,cache_owners=cache_owners,artifacts=PINNED,
        identity=dict(exit=receipt.returncode,stdout=receipt.stdout.replace(str(args.workspaces),'$WORKSPACES'),expected_sha256=sha(args.expected.read_bytes()),tool_sha256=sha(tool.read_bytes())),
        readelf_sha256=sha(readelf.read_bytes()),scanner_sha256=sha(Path(__file__).read_bytes()),
        reference_provenance_sha256=sha(args.reference_provenance.read_bytes()) if args.reference_provenance else None,
        ported_source_scope='Original U8 recipe donor sources, SHA recorded; not a complete cold reproduction of every object. Never infer deployed provider bytes solely from these sources',
        limits=['A dlsym whole-function call can run its original initializers; method-table-only proxying and external initialization are different',
            'Symbol availability does not prove successful registration, cache contents, interposition owner or runtime namespace',
            'AOSP14r1 reference function bodies do not automatically equal a patched deployed provider'])
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')


if __name__=='__main__':
    main()
