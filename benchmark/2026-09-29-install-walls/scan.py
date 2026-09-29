#!/usr/bin/env python3
"""Offline byte-level prediction. Header acceptance is not install success."""
import csv, hashlib, json, re, struct, zipfile
from pathlib import Path
from prepare import HERE, ROOT, sha
BASE=ROOT.parent
B69=BASE/'westlake-harness-b4/benchmark/2026-09-29-manifest-classes'
INPUTS=BASE/'westlake-inputs/apks'

def elf_reason(b,abi,ident_zero=True):
    if len(b)<16 or b[:4]!=b'\x7fELF': return 'not-ELF'
    if b[5]!=1: return 'not-little-endian'
    width,machine=(64,183) if abi=='arm64-v8a' else (52,40)
    if len(b)<width: return 'truncated-ELF'
    if b[4]!=(2 if abi=='arm64-v8a' else 1): return 'wrong-ELF-class'
    if b[6] not in ([0,1] if ident_zero else [1]): return 'wrong-EI_VERSION'
    typ,mach,ver=struct.unpack_from('<HHI',b,16)
    if ver!=1:return 'wrong-e_version'
    if typ!=3:return 'not-ET_DYN'
    if mach!=machine:return 'wrong-machine'
    return ''

def scan_apk(key,path):
    r={'key':key,'path':str(path),'sha256':sha(path),'entries':[]}
    with zipfile.ZipFile(path) as z:
        infos=z.infolist()
        abis={i.filename.split('/')[1] for i in infos if re.fullmatch(r'lib/[^/]+/[^/]+\.so',i.filename)}
        abi=next((a for a in ['arm64-v8a','armeabi-v7a'] if a in abis),'')
        r['selected_abi']=abi;r['abis']=sorted(abis)
        for i in sorted(infos,key=lambda i:i.filename):
            if not abi or not i.filename.startswith('lib/'+abi+'/') or i.filename.endswith('/'):continue
            name=i.filename.split('/')[-1]
            with z.open(i) as f:b=f.read(64)
            reason=elf_reason(b,abi)
            if not re.fullmatch('lib[^/]*[.]so',i.filename[len('lib/'+abi+'/'):]):reason='unsafe-selected-name'
            e={'entry':i.filename,'bytes':i.file_size,'crc32':f'{i.CRC:08x}','magic':b[:16].hex(),
               'strict_reason':reason,'old_without_vendor_exception_reason':elf_reason(b,abi,False)}
            if reason:
                # Full read validates outer CRC and gives exact bytes for bounded exceptions.
                full=z.read(i);e['sha256']=hashlib.sha256(full).hexdigest();e['outer_crc_verified']=True
            r['entries'].append(e)
    return r

def main():
    pinned=json.loads((HERE/'evidence/inputs.json').read_text())
    paths=[(x['key'],Path(x['path'])) for x in pinned]
    for x in json.loads((B69/'results.json').read_text())['apps']:
        paths.append((x['key'],B69/'apks'/x['key']/(x['key']+'.apk')))
    for p in sorted((INPUTS/'fdroid100').glob('*.apk')):paths.append((p.stem,p))
    for p in sorted((BASE/'vm-copies/apks-77/x').glob('x.config.*.apk')):paths.append((p.stem,p))
    exceptions=json.loads((HERE/'native-data-exceptions.json').read_text())
    allowed={(x['bundle'],x['filename'],x['sha256']) for x in exceptions}
    results=[];seen={};duplicates=[]
    for key,p in paths:
        digest=sha(p)
        if digest in seen:
            duplicates.append({'key':key,'path':str(p),'same_as':seen[digest]});continue
        seen[digest]=key;r=scan_apk(key,p)
        for e in r['entries']:
            e['candidate_reason']=e['strict_reason']
            if r['selected_abi']=='arm64-v8a' and ({'fd-seal':'com.junkfood.seal','toutiao':'com.ss.android.article.news'}.get(key),Path(e['entry']).name,e.get('sha256')) in allowed:
                e['candidate_reason']='';e['candidate_exception']='draft-exact-payload'
        r['strict_rejected']=[e['entry'] for e in r['entries'] if e['strict_reason']]
        r['candidate_rejected']=[e['entry'] for e in r['entries'] if e['candidate_reason']]
        # APK manifests are not proxy JSON sizes. Only actual producer log sizes count.
        r['manifest_json_bytes']={'fd-seal':2245,'x':99625,'toutiao':242663}.get(key)
        n=r['manifest_json_bytes']
        r['manifest_old_capacity']='unknown' if n is None else ('reject' if n+1>65536 else 'fit')
        r['manifest_new_capacity']='unknown' if n is None else ('reject' if n+1>1048576 else 'fit')
        r['install_after_patch']='unverified'
        results.append(r)
    out={'apps':results,'duplicate_inputs':duplicates,'summary':{
        'unique_apk_files':len(results),'aliases_deduplicated':len(duplicates),
        'selected_native_entries':sum(len(x['entries']) for x in results),
        'strict_header_reject_apps':[x['key'] for x in results if x['strict_rejected']],
        'candidate_header_reject_apps':[x['key'] for x in results if x['candidate_rejected']],
        'known_manifest_overflow_apps':[x['key'] for x in results if x['manifest_old_capacity']=='reject'],
        'manifest_size_unknown':sum(x['manifest_json_bytes'] is None for x in results)}}
    (HERE/'evidence/apk-scan.json').write_text(json.dumps(out,indent=2)+'\n')
    fields=['key','sha256','selected_abi','native_entries','strict_rejected','candidate_rejected',
            'manifest_json_bytes','manifest_old_capacity','manifest_new_capacity','install_after_patch']
    with (HERE/'app-impact.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in results:w.writerow({k:len(r['entries']) if k=='native_entries' else
            '|'.join(r[k]) if isinstance(r.get(k),list) else r.get(k) for k in fields})
    print(json.dumps(out['summary'],indent=2))
if __name__=='__main__':main()
