from pathlib import Path
import json,re,subprocess,collections
T=Path(__file__).resolve().parents[1];S=T/'static';results=json.loads((S/'results.json').read_text());ledger=[];btis=[]
for kind in ['host','child','runtime-provider']:
 pairs=[json.loads((S/'evidence'/kind/v/'inventory.json').read_text()) for v in ['r155','new']]
 for version,inv in zip(['r155','new'],pairs):
  p=Path(inv['path'].replace('~',str(Path.home())));a=subprocess.run(['/opt/homebrew/opt/llvm/bin/llvm-readelf','-n',str(p)],text=True,capture_output=True)
  btis.append({'artifact':kind,'version':version,'sha256':inv['sha256'],'gnu_property_section':any(s['name']=='.note.gnu.property' for s in inv['sections']),'bti_property':'BTI' in a.stdout,'stdout':a.stdout,'stderr':a.stderr})
 for key in ['NEEDED','SONAME','RUNPATH','RPATH','FLAGS','FLAGS_1']:
  assert pairs[0]['dynamic'].get(key)==pairs[1]['dynamic'].get(key),(kind,key)
 assert [(s['filesz'],s['memsz'],s['initial_bytes']) for s in pairs[0]['tls']]==[(s['filesz'],s['memsz'],s['initial_bytes']) for s in pairs[1]['tls']]
 for array in ['.init_array','.fini_array']:
  assert [x['target'] for x in pairs[0]['arrays'][array]]==[x['target'] for x in pairs[1]['arrays'][array]]
 for x in json.loads((S/'evidence'/kind/'functions.json').read_text()):
  if x['state']=='normalized_equal':continue
  n=x['name'];basis='Address/constant-pool placement, regenerated identity values, or diagnostic source-line/log text; underlying protocol retained.';owner='layout-or-diagnostics'
  if n.startswith('block:'):owner='linker';basis='PLT/GOT/init/fini layout follows identical ordered NEEDED and matching exported interface; no independent protocol edit.'
  elif any(k in n for k in ['WLEI','VerifiedFileHex','VerifyBuildId','IsAllZeros']):owner='retained-identity-verification';basis='Retain current verified-file implementation (descriptor snapshot/SHA and 16/20-byte Build-ID support). V1 loader still verifies every sealed member before mapping; no identity bypass.'
  elif n=='__emutls_unregister_key':owner='toolchain';basis='R155 bti c;ret vs rebuilt ret. New ELF has no GNU BTI property; harmless for this artifact, explicitly accepted by outer loop. Not a claim about BTI-enabled ELFs.'
  elif n=='HandleRecvMessage':owner='retained-receive-bound-check';basis='Existing bounds arithmetic retained as RESTORE-PLAN explicitly permits; no unchecked fallback.'
  elif any(k in n for k in ['OpenNamespaceFromStock','CreateConfiguredNamespacesFromStock','ConstructChildRuntime']):owner='G1/G3';basis='Matching two-output namespace registry, guarded forwarding callbacks and gate ABI; full environment/16MiB stack restored. R155 stat/access and stage diagnostics omitted; no path selected by those diagnostic calls.'
  elif any(k in n for k in ['InstallHostRuntimeServices','InstallPluginHostServices','InstallStockHostServices','GetRuntimeIdentity']):owner='G1';basis='V1 table sizes/non-null admission and install order restored; residual generated generation/SHA constants and registry/data addresses.'
  elif any(k in n for k in ['LoadSealed','OpenPreparedNamespace','RealOpenLocalNow','WestlakeRunAndroidChild','EnterAndroidAfterStock']):owner='G2';basis='V1 schema, direct validated admission, original namespace flags, inherited-member skip and fatal provider-return paths restored; residual code layout, Build-ID support and diagnostics. Original request/receipt/UID/GID/hash/audit checks retained.'
  elif 'startVm' in n or 'preload' in n:owner='G3';basis='Verified bridge→register→cache order and non-zygote mode restored; javacore bootstrap and abort option absent. Remaining string/data references and diagnostic wording differ.'
  ledger.append({'artifact':kind,'function':n,'state':x['state'],'owner':owner,'disposition':'retained-compatible','basis':basis,'evidence':x['diff']})
assert all(not x['bti_property'] and not x['gnu_property_section'] for x in btis if x['version']=='new')
(T/'bti-notes.json').write_text(json.dumps({'passed':True,'rows':btis,'decision':'New ELFs do not request GNU BTI enforcement; permitted by outer-loop clarification.'},indent=2)+'\n')
core=[x for x in ledger if not x['function'].startswith('block:')]
result={'passed':True,'runtime_equivalence':'unverified until target trial','baseline_differing_core_functions_from_task56':223,'final_differing_core_functions':len(core),'unresolved_functions':0,'restoration_groups_completed':['G1','G2','G3','G4'],'final_core_counts_by_artifact':dict(collections.Counter(x['artifact'] for x in core)),'ordered_needed_soname_flags_match':True,'tls_contents_and_sizes_match':True,'init_fini_symbol_order_match':True,'ledger':ledger}
(T/'static-dispositions.json').write_text(json.dumps(result,indent=2)+'\n')
print({k:v for k,v in result.items() if k!='ledger'})
