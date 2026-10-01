"""Exact installer resource selection crossed with SHA-bound U8 own-tile evidence."""

import argparse
import base64
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import struct
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
THEME = ROOT/'benchmark/2026-10-01-b10-theme-graphics'
sys.path.insert(0,str(THEME))
SPEC = importlib.util.spec_from_file_location('icon_input_cohort',THEME/'collect.py')
cohort = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cohort)
RESOLVER = ROOT/'bms/src/adapter/framework/package-manager/jni/arsc_resolver.cpp'
RESOLVER_SHA = '22b27c2e88b9763fc4843df3a17edf2941729084c8a6f97e8c4a7322490c7bb1'
FRAMEWORK_SHA = '76a157c084f9b90dae195191d2159901434f11f815e3e2d9eea02ded486e7770'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(data, pin):
    if sha(data) != pin:
        raise ValueError('Icon scan identity drift')


def build_probe(output):
    verify(RESOLVER.read_bytes(),RESOLVER_SHA)
    subprocess.run(['/usr/bin/clang++','-std=c++17','-O2','-I'+str(HERE/'host'),'-I'+str(RESOLVER.parent),str(HERE/'host/probe.cpp'),'-o',str(output)],check=True)


def manifest_icon(text):
    stack = []
    package = None
    icon = 0
    line_number = None
    for number,line in enumerate(text.splitlines(),1):
        body=line.lstrip();depth=len(line)-len(body)
        if body.startswith('E: '):
            while stack and stack[-1][0]>=depth:
                stack.pop()
            stack.append((depth,body.split()[1]))
        elif body.startswith('A: ') and stack:
            if stack[-1][1]=='manifest' and body.startswith('A: package='):
                package=body.split('"')[1]
            if stack[-1][1]=='application' and '(0x01010002)=' in body:
                found=re.search(r'=(@0x[0-9a-fA-F]+)',body)
                icon=int(found[1][1:],16) if found else 0
                line_number=number
    if not package:
        raise ValueError('Manifest package unavailable')
    return dict(package=package,icon_id=f'0x{icon:08x}',manifest_line=line_number)


def signature(data):
    if not data:
        return 'missing'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'PNG'
    if data.startswith(b'RIFF') and data[8:12]==b'WEBP':
        return 'WebP'
    if data.startswith(b'\xff\xd8\xff'):
        return 'JPEG'
    if data.startswith(b'\x03\x00\x08\x00') or data.lstrip().startswith((b'<?xml',b'<vector',b'<adaptive-icon',b'<shape')):
        return 'XML'
    return 'other-unknown'


def format_details(data):
    family=signature(data)
    result=dict(family=family,validity='signature-only-not-decoder-tested',prefix_hex=data[:24].hex())
    if data.startswith(b'RIFF'):
        declared=struct.unpack_from('<I',data,4)[0]+8 if len(data)>=8 else None
        result['RIFF_declared_file_bytes']=declared
        result['actual_file_bytes']=len(data)
        result['validity']='WebP-header-and-RIFF-size-valid' if family=='WebP' and declared==len(data) else 'RIFF-header-or-length-invalid'
        if result['validity']!='WebP-header-and-RIFF-size-valid':
            try:
                diagnostic=data.decode('utf8').encode('latin1')
            except (UnicodeDecodeError,UnicodeEncodeError):
                diagnostic=None
            if diagnostic and signature(diagnostic)=='WebP' and len(diagnostic)>=12 and struct.unpack_from('<I',diagnostic,4)[0]+8==len(diagnostic):
                result.update(family='WebP',validity='malformed-UTF8-expanded-WebP',diagnostic_reversed_bytes=len(diagnostic),
                    diagnostic_reversed_prefix_hex=diagnostic[:24].hex(),diagnostic_reversed_sha256=sha(diagnostic),
                    limitation='Reversible encoding pattern identifies malformed input, not its upstream producer; no repaired file was written')
    return result


def file_format(data):
    return format_details(data)['family']


def resource_block(text, resource_id):
    lines=text.splitlines();result=[];active=False;depth=0
    for number,line in enumerate(lines,1):
        if re.match(r'\s*resource '+re.escape(resource_id)+r'\b',line):
            active=True;depth=len(line)-len(line.lstrip())
        elif active and line.strip() and len(line)-len(line.lstrip())<=depth:
            active=False
        if active:
            result.append(dict(line=number,text=line))
    return result


def tiles(tree, package, activity):
    exact='AppIconCommonView_'+package+'.'+activity if activity else None
    matches=[];all_tiles=[]
    def visit(node, launcher=False, visible=True):
        attrs=node.get('attributes') or {}
        if attrs.get('bundleName'):
            launcher=attrs['bundleName']=='com.ohos.sceneboard'
        visible=visible and attrs.get('visible') not in (False,'false')
        identifiers={str(attrs.get('id') or ''),str(attrs.get('key') or '')}
        if launcher:
            all_tiles.extend(identifier for identifier in identifiers if identifier.startswith('AppIconCommonView_'))
            if exact and exact in identifiers:
                matches.append(dict(id=exact,visible=visible,enabled=attrs.get('enabled'),clickable=attrs.get('clickable')))
        for child in node.get('children') or []:
            visit(child,launcher,visible)
    visit(tree)
    return dict(matches=matches,all_tile_ids=sorted(set(all_tiles)))


def tile_status(snapshots, activity):
    if not snapshots:
        return 'unknown-no-snapshots'
    if not activity:
        return 'unknown-desktop-activity'
    if any(row['matches'] for row in snapshots):
        return 'found'
    if not any(row['all_tile_ids'] for row in snapshots):
        return 'unknown-cold-desktop'
    return 'not-found-in-captured-pages'


def observe(directory, entry, workspaces):
    record_path=directory/'record.json';payload=record_path.read_bytes();record=json.loads(payload)
    if record.get('key')!=entry['key'] or record.get('package')!=entry['package'] or record.get('apk_sha256')!=entry['apk_sha256']:
        raise ValueError('U8 record APK/package/key drift')
    snapshots=[]
    activity=record.get('desktop_activity')
    for file in sorted(directory.glob('icons-*.json')):
        data=file.read_bytes()
        snapshots.append(dict(file=str(file.relative_to(workspaces)),sha256=sha(data),**tiles(json.loads(data),entry['package'],activity)))
    log=directory/'install-hilog.txt';install=[]
    if log.is_file():
        data=log.read_bytes()
        for number,line in enumerate(data.decode(errors='replace').splitlines(),1):
            if any(token in line for token in ['ReadIconByManifest:','icon normalize:','ICONLESS_APK_TEMPLATE_PLACEHOLDER','icon.png']):
                install.append(dict(line=number,text=line.replace(str(workspaces),'$WORKSPACES').replace(str(Path.home()),'$HOME')))
    status=tile_status(snapshots,activity)
    for snapshot in snapshots:
        snapshot['launcher_tile_count']=len(snapshot.pop('all_tile_ids'))
    return dict(directory=str(directory.relative_to(workspaces)),record_sha256=sha(payload),desktop_activity=activity,
        record_status=record.get('status'),error=record.get('error'),tile_status=status,
        tile_found=any(row['matches'] for row in snapshots),snapshots=snapshots,
        install_hilog_sha256=sha(log.read_bytes()) if log.is_file() else None,install_icon_lines=install,
        limits='Own tile is existence in captured pages, not screenshot UI or global launcher-database absence; hidden/nonactionable tiles remain separately visible in witnesses')


def inspect(entry, probe, aapt, framework, output, workspaces, original, signed, supplement):
    apk=Path(entry['path']);payload=apk.read_bytes();verify(payload,entry['apk_sha256'])
    xml=subprocess.check_output([str(aapt),'dump','xmltree',str(apk),'--file','AndroidManifest.xml'],text=True)
    parsed=manifest_icon(xml)
    if parsed['package']!=entry['package']:
        raise ValueError('APK manifest package drift')
    resource_id=int(parsed['icon_id'],16)
    owner=framework if resource_id>>24==1 else apk
    result=dict(key=entry['key'],package=entry['package'],apk_sha256=entry['apk_sha256'],cohort=entry['cohort'],**{key:value for key,value in parsed.items() if key!='package'},
        selected_file=None,selected_format='missing',selection_status='no-application-icon-reference',candidates=[],selection_scope='ReadIconByManifest resolved resource file before XML composition/fallback')
    if resource_id:
        with zipfile.ZipFile(owner) as archive:
            if 'resources.arsc' not in archive.namelist():
                result['selection_status']='no-resources.arsc'
            else:
                arsc=archive.read('resources.arsc')
                raw=output/(entry['key']+'.arsc');raw.write_bytes(arsc)
                answer=subprocess.check_output([str(probe),str(raw),parsed['icon_id']],text=True).strip();raw.unlink()
                result['resources_arsc_sha256']=sha(arsc)
                dump=subprocess.check_output([str(aapt),'dump','resources',str(owner)],text=True,errors='replace')
                result['resource_dump_sha256']=sha(dump.encode());result['candidates']=resource_block(dump,parsed['icon_id'])
                result['resource_owner']='framework-res.apk' if owner==framework else 'app APK'
                if answer.startswith('SELECTED\t'):
                    selected=answer.split('\t',1)[1];result['selected_file']=selected
                    if selected in archive.namelist():
                        data=archive.read(selected);details=format_details(data);result.update(selected_format=details['family'],format_details=details,selected_bytes=len(data),selected_sha256=sha(data),selection_status='resolved-file')
                    else:result['selection_status']='resolved-file-missing-from-zip'
                elif answer=='MISSING':result['selection_status']='unresolved-or-non-string-reference'
                else:raise ValueError('Unexpected resolver output')
    original_row=original[entry['key']]
    result['U8_full_signed']=signed[entry['key']]
    result['U8_full_tile']=observe(workspaces/original_row['source'],entry,workspaces)
    result['U8_rerun_signed']=supplement['verdicts'].get(entry['key'])
    result['U8_rerun_tile']=None
    if result['U8_rerun_signed']:
        run=workspaces/str(supplement['run']).removeprefix('$WORKSPACES/')
        matches=list(run.glob('*/'+entry['key']))
        if len(matches)!=1:raise ValueError('Supplemental run key missing/duplicate')
        result['U8_rerun_tile']=observe(matches[0],entry,workspaces)
    return result


def summarize(rows):
    if len(rows)!=166 or len({row['key'] for row in rows})!=166:
        raise ValueError('Incomplete/duplicate icon cohort')
    webp=[row for row in rows if row['selected_format']=='WebP']
    chosen=lambda row:row['U8_rerun_tile'] or row['U8_full_tile']
    return dict(keys=166,formats=dict(Counter(row['selected_format'] for row in rows)),
        selection_status=dict(Counter(row['selection_status'] for row in rows)),
        WebP_keys=[row['key'] for row in webp],WebP_count=len(webp),
        WebP_validity=dict(Counter(row.get('format_details',{}).get('validity','unprovided') for row in webp)),
        WebP_full_tile_status=dict(Counter(row['U8_full_tile']['tile_status'] for row in webp)),
        WebP_latest_tile_status=dict(Counter(chosen(row)['tile_status'] for row in webp)),
        WebP_latest_not_found_keys=[row['key'] for row in webp if chosen(row)['tile_status']=='not-found-in-captured-pages'],
        full_tile_status=dict(Counter(row['U8_full_tile']['tile_status'] for row in rows)),
        latest_tile_status=dict(Counter(chosen(row)['tile_status'] for row in rows)),
        full_signed=dict(Counter(row['U8_full_signed']['verdict'] for row in rows)),
        latest_signed=dict(Counter(row['U8_rerun_signed']['rerun'] if row['U8_rerun_signed'] else row['U8_full_signed']['verdict'] for row in rows)))


def emit(output, result):
    output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    fields=['key','package','apk_sha256','icon_id','selected_file','selected_format','selection_status','format_validity','U8_full_t20','U8_full_tile','U8_rerun_t20','U8_rerun_tile']
    with (output/'ICONS.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=fields);writer.writeheader()
        for row in result['rows']:
            flat={key:row.get(key) for key in fields[:7]}
            flat.update(format_validity=row.get('format_details',{}).get('validity','unknown'),U8_full_t20=row['U8_full_signed']['verdict'],U8_full_tile=row['U8_full_tile']['tile_status'],
                U8_rerun_t20=row['U8_rerun_signed']['rerun'] if row['U8_rerun_signed'] else '',
                U8_rerun_tile=row['U8_rerun_tile']['tile_status'] if row['U8_rerun_tile'] else '')
            writer.writerow(flat)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspaces',type=Path,default=Path(os.environ.get('WORKSPACES',ROOT.parent)))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();workspaces=args.workspaces
    facts_path=ROOT/'benchmark/2026-10-01-b10-libart-impact/bitvector-facts.json.gz.b64'
    verify(facts_path.read_bytes(),'a0443fe5bf3be9b8e1cbf8b75726ef47f786ee6388e118f3a712639c4c892b23')
    originals=json.loads(gzip.decompress(base64.b64decode(facts_path.read_bytes())))['rows']
    original={row['key']:row for row in originals}
    signoff_path=workspaces/'westlake-harness/benchmark/2026-10-01-u8-sweep/outer-signoff.json'
    signoff=json.loads(signoff_path.read_text());signed={row['key']:row for row in signoff['keys']}
    supplemental_path=workspaces/'westlake-harness/benchmark/2026-10-01-u8-appfailed-rerun/results.json'
    supplement=json.loads(supplemental_path.read_text())
    entries=cohort.inputs(workspaces)
    if set(signed)!=set(original) or set(signed)!={row['key'] for row in entries}:
        raise ValueError('Signed original/cohort mismatch')
    aapt=Path.home()/'Library/Android/sdk/build-tools/37.0.0/aapt2'
    generation=workspaces/'westlake-generation-u8-j9-t7e'
    framework=generation/'native/payload/android/framework/framework-res.apk'
    verify(framework.read_bytes(),FRAMEWORK_SHA)
    installer=generation/'native/native-checks/system-elf/7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18'
    verify(installer.read_bytes(),installer.name)
    expected=ROOT/'benchmark/2026-10-01-b10-registration-impact/expected-u8.json'
    identity=subprocess.run(['python3',str(workspaces/'westlake-harness/scripts/lab/artifact_identity.py'),'--expected',str(expected),str(installer)],capture_output=True,text=True)
    if identity.returncode or len(identity.stdout.splitlines())!=1 or not all(line.startswith('DEPLOYED ') for line in identity.stdout.splitlines()):
        raise ValueError('U8 installer/framework identity refused: '+identity.stdout.replace(str(workspaces),'$WORKSPACES'))
    with tempfile.TemporaryDirectory(prefix='icon-resource-') as temporary:
        scratch=Path(temporary);probe=scratch/'probe';build_probe(probe)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures=[pool.submit(inspect,entry,probe,aapt,framework,scratch,workspaces,original,signed,supplement) for entry in entries]
            rows=[]
            for future in futures:
                row=future.result();rows.append(row);print('ICON',len(rows),row['key'],row['selected_file'],row['selected_format'],row['U8_full_tile']['tile_status'],flush=True)
        result=dict(schema='b10-icon-format-scan-v1',rows=sorted(rows,key=lambda row:row['key']),summary=summarize(rows),
            identity=dict(exit=identity.returncode,receipt=identity.stdout.replace(str(workspaces),'$WORKSPACES'),framework_sha256=sha(framework.read_bytes()),framework_status='Outer independently read three boards and supplied exact deployed SHA; outside runtime/boot fingerprint, not added to frozen expected map',installer_sha256=installer.name),
            dependencies={str(file.relative_to(ROOT)):sha(file.read_bytes()) for file in [Path(__file__),RESOLVER,RESOLVER.with_suffix('.h'),THEME/'collect.py',HERE/'host/probe.cpp',HERE/'host/unzip.h',HERE/'host/hilog/log.h']},
            evidence_sources=dict(selected_U8_attempts_sha256=sha(facts_path.read_bytes()),full_signoff_sha256=sha(signoff_path.read_bytes()),supplemental_signoff_sha256=sha(supplemental_path.read_bytes()),aapt2_sha256=sha(aapt.read_bytes())),
            probe_sha256=sha(probe.read_bytes()),limitations=['Resolver resource-file format only; XML composition/fallback may produce a PNG later',
                'Tile observations are not UI signoff or global tile absence; all selected original attempts exclude invalid concurrent directories',
                'Host resolver I/O uses exact extracted resources.arsc bytes, not an Android configuration chooser; path-based density scoring and stable ties are intentional parity'])
        emit(args.output,result)
        print(json.dumps(result['summary'],sort_keys=True))


if __name__=='__main__':
    main()
