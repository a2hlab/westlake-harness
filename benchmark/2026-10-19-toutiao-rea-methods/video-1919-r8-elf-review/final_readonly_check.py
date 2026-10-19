"""Read existing exact outer outputs only; no build, derivation output or device call."""
from pathlib import Path
import hashlib,json,runpy,struct,subprocess
root=Path(__file__).resolve().parents[3]
out=Path(__file__).resolve().parent
base=Path.home()/'.local/share/westlake/toutiao-resume-20261019'
main=root.parent/'westlake-harness'
build=base/'r8-build-outer-2329/build'; der=base/'r8-derive-outer-2328'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
script=main/'benchmark/2026-10-19-toutiao-video-playback/candidate-r8/derive_ttmplayer_logmirror.py'
assert sha(script)=='5b76ba54262ba7e5c90f00e44772a83f85a7083654a80aea4bdf49105435d098'
m=runpy.run_path(str(script),run_name='review_readonly')
before=main/'benchmark/2026-10-19-toutiao-video-playback/candidate-r4/deploy-inputs/libttmplayer.so'; after=der/'libttmplayer.so'
a=before.read_bytes(); b=after.read_bytes()
assert sha(before)==m['IN_SHA'] and sha(after)==m['OUT_SHA']
f1,o1,l1=m['analyze'](a,m['OLD'],m['NEW']); f2,o2,l2=m['analyze'](b,m['NEW'],m['OLD'])
expect=dict(l1);expect[m['OLD'].decode()]=(0,0);expect[m['NEW'].decode()]=(227,0);assert l2==expect
assert [i for i,(x,y) in enumerate(zip(a,b)) if x!=y]==list(range(0xa6f3,0xa704)) and len(a)==len(b)
# Independent equality of complete hash/version/RELA section byte ranges.
u64=lambda d,o:struct.unpack_from('<Q',d,o)[0];u16=lambda d,o:struct.unpack_from('<H',d,o)[0]
shoff=u64(a,0x28);se=u16(a,0x3a);count=u16(a,0x3c);stridx=u16(a,0x3e)
headers=[struct.unpack_from('<IIQQQQIIQQ',a,shoff+i*se) for i in range(count)]
ns=headers[stridx];names=a[ns[4]:ns[4]+ns[5]]
sections=[];rela_records=0
for h in headers:
    name=names[h[0]:].split(b'\0')[0].decode()
    if name in ('.hash','.gnu.hash','.gnu.version','.gnu.version_r') or h[1]==4:
        x=a[h[4]:h[4]+h[5]];y=b[h[4]:h[4]+h[5]];assert x==y
        sections.append({'name':name,'size':len(x),'sha256':hashlib.sha256(x).hexdigest()})
        if h[1]==4:rela_records+=h[5]//h[9]
assert rela_records==20591
proof=json.loads((der/'proof.json').read_text())
assert f1==proof['binding_facts_input'] and f2==proof['binding_facts_output']
assert (der/'rc').read_text().strip()=='0'
inputpins={'src/opensles_android_compat.c':'cf45ad430a08cbe090f030357a346be7a0bac49f48c06196a11c7818de3f9351','src/ttplayer_log_mirror.c':'3becb0f688e9dba9f5626a8453756848dd51e2f5347c4688672de0fbe3384e8e','inputs/liblog.so':'d8ad176b41b820a4868b74394188429ad2dc69025661d320d0986dd713048ca4','inputs/original-compat.so':'9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f'}
for p,s in inputpins.items():assert sha(build/p)==s
rcs={p.stem:int(p.read_text()) for p in sorted((build/'raw').glob('*.rc'))}
expected_steps={'00-frozen','01-inputs','02-recipe-tools','03-image','04-tools','05-liblog-abi','10-anchor','20-link','21-strip','30-old-abi','31-new-abi','32-relocations','33-abi-compare','34-inputs-after','40-output-sha'}
assert set(rcs)==expected_steps and all(v==0 for v in rcs.values())
receipt=json.loads((build/'build-receipt.json').read_text());checked=0
for row in receipt['files']:
    p=build/row['path'];assert p.stat().st_size==row['size'] and sha(p)==row['sha256'];checked+=1
abi=json.loads((build/'abi-comparison.json').read_text())
assert abi['exports_added']==['__wl_ttlog_00000659']
assert set(abi['undefined_added'])=={'__android_log_vprint','__errno_location','snprintf','vsnprintf','write'}
obj='/opt/homebrew/opt/llvm/bin/llvm-objdump';binary=build/'artifacts/libopensles_android_compat.so'
assert sha(binary)=='6e83e924aae709f0c90ba2a966910febb63471b7a9a6294c6dee585a73ff3b4b'
argv=[obj,'-d','--start-address=0x1aac','--stop-address=0x1f00',str(binary)]
r=subprocess.run(argv,capture_output=True)
assert r.returncode==0 and b'ldxr' in r.stdout and b'stxr' in r.stdout
public=r.stdout.replace(str(binary).encode(),b'$BASE/r8-build-outer-2329/build/artifacts/libopensles_android_compat.so')
(out/'compat-atomics.sanitized.txt').write_bytes(public)
(out/'disassembly-receipt.json').write_text(json.dumps({'argv':argv[:-1]+['$BASE/r8-build-outer-2329/build/artifacts/libopensles_android_compat.so'],'rc':r.returncode,'tool_sha256':sha(Path(obj)),'artifact_sha256':sha(binary),'raw_stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'public_stdout_sha256':hashlib.sha256(public).hexdigest(),'stderr':r.stderr.decode(),'transformation':'Input path alias substitution only'},indent=2)+'\n')
report={'token':'video-1919-r8-elf-review','verdict':'ACCEPT_OFFLINE_CANDIDATE_NOT_RUNTIME_ADMISSION','derive_sha256':sha(script),'main_recipe_sha256':sha(main/'benchmark/2026-10-19-toutiao-video-playback/candidate-r8/build_candidate.sh'),'executed_recipe_sha256':sha(build/'recipe.sh'),'player_sha256':sha(after),'compat_sha256':sha(binary),'compat_unstripped_sha256':sha(build/'unstripped/libopensles_android_compat.so'),'blockers':[],
'derivation':{'exact_17_byte_diff':True,'all_relocations_unchanged':rela_records,'r4_cache105_preserved':f2['cache_relocs'],'bss_relative_total_not_cache_count':f2['bss_addend_relatives'],'lookup_names_checked':len(l2),'non_target_lookup_equal':True,'non_symbol_dynstr_references':f2['non_symbol_dynstr_references'],'dynstr_linked_section_types':f2['dynstr_linked_section_types'],'hash_version_relocation_sections':sections,'output_paths':'realpath alias refusal + lexists + exclusive output/proof reservations; fixed SHA, sentinel disabled'},
'build':{'input_pins':inputpins,'step_rcs':rcs,'receipt_files_rehashed':checked,'abi':abi,'atomics':'Actual0x1b50-0x1b78 ldxr/stxr inline CAS, counter0x42d4; no atomic helper import/library','forwarding_abi':'Actual0x1bc0-0x1bd8 passes original priority/tag/format and AArch64 va_list address to vprint PLT; entry errno restored0x1bbc.','opensl':'Exactcf45 original C and both8-byte IID exports preserved; unchanged ctor source. Runtime OpenSL behavior not re-tested.','unwind':'Prior2324 had unwind definitions after linking real liblog.2329 --unwindlib=none has no unwind exports/imports/library in final compat. Default archive extraction attribution was not independently captured; -zdefs alone is not established as the cause.'},
'runtime_unknown':['player0x471f88 must resolve to exact new compat export0x1aac','compat vprint GOT0x3258 must resolve to exact intended d8ad liblog+0x7450 in actual namespace','real liblog adds transitive libc++.so/libc.so resolution; -zdefs is not runtime closure proof','errno/write/format imports actual provider instances','mirror execution/diagnostic visibility/playback/audio'],
'no_actions':{'device_calls':0,'production_builds_by_reviewer':0,'C_oracle_repeated':False},'docker_limit':'Local Docker socket denied before any container started; outer executed2329 build.'}
(out/'final-review.json').write_text(json.dumps(report,indent=2)+'\n')
inputs=[p for p in (build/'raw').iterdir() if p.is_file()]+[build/'build-receipt.json',build/'abi-comparison.json']+[p for p in der.iterdir() if p.is_file() and p.name!='libttmplayer.so']
rows=[{'path':'$BASE/'+str(p.relative_to(base)),'size':p.stat().st_size,'sha256':sha(p)} for p in sorted(inputs)]
(out/'raw-source-manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({'verdict':report['verdict'],'rc_steps':len(rcs),'receipt_files_rehashed':checked,'player':sha(after),'compat':sha(binary),'derive':sha(script)},indent=2))
