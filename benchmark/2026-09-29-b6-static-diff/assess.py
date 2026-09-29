#!/usr/bin/env python3
"""Attach explicit, bounded static dispositions to every task53 difference."""
import collections, json, re, struct
from pathlib import Path
import compare as c
R=c.ROOT
TOP={(x['component'],x['name']):x for x in json.loads((R/'top20.json').read_text())}
ELFS={k:[c.ELF(*p) for p in pair] for k,pair in c.INPUTS.items()}
def diff_lines(f):
 if 'diff' not in f:return [],[]
 lines=(R/f['diff']).read_text().splitlines()
 return ([x[1:] for x in lines if x.startswith('-') and not x.startswith('---')],[x[1:] for x in lines if x.startswith('+') and not x.startswith('+++')])
def literal_equivalent(kind,a,b):
 if len(a)!=len(b) or not a:return False
 for old,new in zip(a,b):
  pat=r'<\.rodata\+(0x[0-9a-f]+)>'
  x,y=re.search(pat,old),re.search(pat,new)
  if not x or not y or re.sub(pat,'<CONST>',old)!=re.sub(pat,'<CONST>',new):return False
  reg=re.match(r'ldr\w* ([qdxwsb])',old)
  if not reg:return False
  width={'q':16,'d':8,'x':8,'w':4,'s':4,'b':1}[reg[1]]
  bs=[e.bytes(e.byname['.rodata'])[int(m[1],16):int(m[1],16)+width] for e,m in zip(ELFS[kind],(x,y))]
  if bs[0]!=bs[1]:return False
 return True

def classify(kind,f):
 name=f['name'];state=f['state'];a,b=diff_lines(f)
 if state=='normalized_equal':return 'unchanged-code','Address-resolved instructions match with register identities preserved. This is code-level equality only; data, bindings and callers are reviewed separately.'
 if name.startswith('block:'):
  if state=='modified':return 'harmless-layout','Same named PLT/linker block, displaced GOT/page operands; imports and relocation bindings are inventoried separately. No standalone source restoration indicated.'
  return 'restore-with-caller','Added/removed PLT stub follows the recorded import change; restore only if reverting the owning behavior, never patch a PLT entry independently.'
 if (kind,name) in TOP:return TOP[kind,name]['disposition'],TOP[kind,name]['basis']
 if name.startswith('WLEI_') or name in ('OpenVerifiedFileHex','VerifyBuildId','IsAllZeros'):
  return 'retain-hardening','Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.'
 if name=='__emutls_unregister_key':return 'restore-hardening','R155 starts with bti c; NEW omits it. Remaining instructions match. Preserve the landing-pad hardening in rebuild flags; no GNU_PROPERTY BTI requirement was observed, so device fault causality is unverified.'
 if literal_equivalent(kind,a,b):return 'harmless-constant-relocation','Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.'
 if kind=='host':
  if a and b and all(re.fullmatch(r'mov w6, #\d+',x) for x in a+b):return 'harmless-diagnostic','Only HiLogPrint source-line arguments differ; surrounding calls and control flow match.'
  if name in ('AddAppSpawnHook','AddProcessMgrHook','AddServerStageHook','AddSpawnedProcess','AppSpawnHookExecute','AppSpawningCtxTraversal','CreateAppSpawnMgr','DeleteAppSpawnMgr','GetAppSpawnHookMgr','ProcessAppSpawnDumpMsg','ProcessMgrHookExecute','ProcessTerminationStatusMsg','ServerStageHookExecute','TerminateSpawnedProcess','TraversalSpawnedProcess'):
   return 'harmless-layout','Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.'
  if name in ('AppSpawnColdRun','ProcessSpawnReqMsg'):return 'retain-diagnostics','Added WLCGATE HiLog calls preserve the prior result and gate branches. Keep for diagnosis; logging has timing/reentrancy side effects, so not strict runtime equivalence, but no mandatory functional rollback identified.'
  if name=='AppSpawnColdStartApp':return 'harmless-diagnostic','Error log line numbers and source layout move; the flags/msgSize/clientId formatting failure branches remain. Relative read-only lookup table moved with its targets. No changed cold-exec argument or error return identified.'
  if name=='HandleRecvMessage':return 'retain-hardening','Ancillary-message bound comparison changes absolute-pointer sum to offset-versus-remaining-length arithmetic. Equivalent for valid non-wrapping ranges; malformed/overflow behavior need not match. Do not undo a bounds-check hardening change to pursue loader parity.'
  if name=='InitCommonEnv':return 'harmless-layout','Pointer-table relocations move to the same environment-name strings; no getenv/setenv/selection instruction changes. Underlying relocation addends are resolved separately.'
  if name in ('fputc','fputs','AppSpawnDump'):return 'restore','Belongs to the new stdio broker: either defines a remapping wrapper or changes a call from imported vfprintf/fflush to the local wrapper. Restore with __sF and the rest of the broker.'
 if kind=='child':
  bare=name.removeprefix('P0')
  if bare.endswith('Rejected'):
   # Pair old tiny rejectors with the new P0 names; compare the full instruction bodies.
   old=next((x for x in FUNCTIONS[kind] if x['name']==bare),None);new=next((x for x in FUNCTIONS[kind] if x['name']=='P0'+bare),None)
   if old and new:
    oa,_=diff_lines(old);_,nb=diff_lines(new)
    if oa==nb:return 'harmless-rename','Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.'
  if name in ('CompleteStockChildReply','WlascGateMarker','WlascGateMarkerValue'):return 'retain-diagnostics','NEW keeps stderr write markers but removes the optional dlsym(HiLogPrint) mirror. Reply write/close/error handling remains; logging visibility and loader re-entry change. No reason to reintroduce the optional mirror for functional parity.'
  if name=='WestlakeChildBypassGuard':return 'harmless-layout','Only residual page-relative access changes; old 0x1a000+1544 and new 0x24000+464 address g_stock_host_services+0x98 in both. Guard tests and callback slots match, unlike the separate install/protocol changes.'
  if name=='VisitClosure':return 'restore-with-protocol','Graph DFS remains structurally similar, but artifact stride changes 376→400, manifest array slot 32→64 and edge slots 244/248→248/252. This consumes a different V2 schema; restore matching producer/consumer layouts together, not numeric offsets alone.'
  if name.startswith(('Wlgr','wlgr_')) or name in ('BuildIdentity','BuildRequestKey','RequestKey','BytesNonzero','DigestEqual','SourceFactsValid','MapsState','IsInheritedPreloadedProvider','CurrentChildThreadId'):
   return 'restore-with-protocol','New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.'
  if name.startswith(('westlake_child_hook_table','P0')) or name in ('CandidateValid','PublishChildHookTable','RevokeChildHookTable','DrainHookOwner','InvalidateHookOwner','RevokeHookOwner'):
   return 'restore-with-protocol','Hook table now carries callback-owner validation and drain/revoke/invalidate behavior. Same-size/similar signatures do not prove lifecycle equivalence. Keep an internally consistent ownership scheme; restore R155 lifecycle as a unit for parity.'
  if name in ('WLASC_InstallStockHostServicesV1','WLSCPL_LoadSealedProvider','WestlakeRunAndroidChild','InvokeProviderChildEntryWithResolver','RealIsMapped','RealOpenLocalNow','AbsoluteCanonicalForm','WLSCPL_GetLastArtifactIdentityDetail'):
   return 'restore-with-protocol','Part of changed sealed provider, namespace admission and caller sequence. V1 direct resolver is replaced by V2 verified artifact acquisition and A06→A02; restore the complete R155 loader/caller contract. Error diagnostics and identity hashes must match that chosen generation.'
 if kind=='runtime-provider':
  if name=='WLAR_InstallHostRuntimeServices':return 'restore-with-protocol','R155 calls WLNL_InstallSealedOpenV1(services->open_sealed_exact at +104) before publishing ADMISSION_READY. NEW moves the call into Constructors. Restore installer-time binding and fail-closed state publication, not a duplicate call.'
  if name=='WLAR_HostServicesGetNamespaceCallbacks':return 'restore-with-protocol','R155 getter has two outputs (create namespaces, open namespace); NEW adds open_sealed_exact as the first of three outputs. Restore declarations and callers together with installer-time sealed-open registration; public service fields +112/+120 remain mandatory nonzero in both artifacts.'
  if name=='WLAR_GetRuntimeIdentity':return 'retain-generation','Same output layout and null check; NEW vector-copies the 32-byte digest and emits a different generation token. Preserve identity values matching the deployed generation; do not paste R155 digest constants into NEW code.'
  if name.startswith('_ZNKSt3__h6vector'):return 'harmless-codegen','Removed local vector throw helper reflects changed template instantiation; no exported ABI entry removed. Runtime allocation/error paths are assessed with startVm/provider sequence.'
  if 'TypefaceWarmUpNoOp' in name:return 'restore-with-caller','Typeface warmup no-op already exists in correct R155; preserve the caller and native binding.'
  if 'logArtAbortAndTerminate' in name or 'ContextD' in name:return 'restore-with-protocol','New abort logging/termination or global Context destructor participates in changed VM options and lifecycle. Not an inert name change; restore with the owning VM/global-state change.'
  if 'AttachStatusString' in name:return 'harmless-layout','Only the address of the read-only relative string lookup table changes. Return-string choices and bounds logic remain the same; no ABI change.'
  return 'restore-with-protocol','Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.'
 raise ValueError('Unassessed function '+kind+':'+name)

FUNCTIONS={k:json.loads((R/'evidence'/k/'functions.json').read_text()) for k in c.INPUTS}
results=json.loads((R/'results.json').read_text());report=[]
for kind,fs in FUNCTIONS.items():
 for f in fs:
  d,why=classify(kind,f);f.update(disposition=d,basis=why,causality='unverified')
  if f['state']!='normalized_equal':
   report.append(dict(component=kind,name=f['name'],state=f['state'],register_state=f['register_state'],disposition=d,basis=why,diff=f.get('diff'),register_diff=f.get('register_diff'),evidence=[f"evidence/{kind}/{v}/disassembly.txt:{f[v]['line']}" for v in ('r155','new') if f[v]]))
 c.save(R/'evidence'/kind/'functions.json',fs)
 results['artifacts'][kind]['function_dispositions']=dict(collections.Counter(f['disposition'] for f in fs))
 # Semantic projections distinguish harmless address movement from actual lifecycle changes.
 md=results['artifacts'][kind]
 for key in ('tls','arrays'):
  vals=md[key]
  if key=='tls':project=lambda xs:[{k:x[k] for k in ('flags','filesz','memsz','align','initial_bytes')} for x in xs]
  else:project=lambda xs:{k:[i['target'] for i in v] for k,v in xs.items()}
  vals['semantic_equal']=project(vals['r155'])==project(vals['new'])
  vals['disposition']='harmless-layout' if vals['semantic_equal'] else 'restore-with-protocol'
  vals['basis']='Compare TLS sizes/alignment/initial bytes or relocated constructor target order; ignore numeric placement only.'
 for key in ('imports','exports'):
  md[key]['assessments']=[dict(change=change,symbol=s,disposition='restore-with-owner',basis='Dynamic ABI/binding change; follow the stdio, namespace, identity or provider function family above. Symbol addition alone is not evidence of a fault.') for change in ('added','removed') for s in md[key][change]]
 for key in ('relocations','relocations_by_section'):
  md[key]['disposition']='restore-with-owner' if not md[key]['equal'] else 'unchanged'
  md[key]['basis']='Changed target/count belongs to explicit symbol/data/function changes. Never restore raw relocation addresses independently.'
 a,b=[json.loads((R/'evidence'/kind/v/'inventory.json').read_text()) for v in ('r155','new')]
 sec={v:{s['name']:s for s in x['sections']} for v,x in [('r155',a),('new',b)]};sd=[]
 for name in sorted(set(sec['r155'])|set(sec['new'])):
  x,y=sec['r155'].get(name),sec['new'].get(name)
  if x==y:continue
  alloc=bool((x or y)['flags']&2);decision='harmless-metadata' if not alloc else 'reviewed-in-owner-inventory'
  sd.append(dict(name=name,r155=x,new=y,disposition=decision,basis='Non-allocated debug/symbol metadata.' if not alloc else 'Code: functions.json; bindings: relocations/symbols; paths/config: strings-diff.json; state/arrays/TLS: inventory.json. Placement alone is harmless.'))
 c.save(R/'evidence'/kind/'sections-diff.json',sd)
 ss=json.loads((R/'evidence'/kind/'strings-diff.json').read_text())
 for x in ss:
  t=x['text']
  if not x['allocated']:d,w='harmless-metadata','Non-allocated debug/symbol/compiler strings; no runtime mapping.'
  elif re.fullmatch('[a-f0-9]{28,64}',t) or '/route-a/' in t:d,w='retain-generation','Generation/artifact identity or generation-qualified path. Must match the chosen coherent deployment; do not revert a hash/path alone.'
  elif x['section']=='.dynstr':d,w='restore-with-owner','Dynamic string belongs to exact imported/exported names or library dependencies; see metadata and function dispositions.'
  elif ('WLCGATE' in t or t.startswith(('[','ART ')) or t in ('%{public}s','%{public}s:%{public}u','APPSPAWN')):d,w='retain-diagnostic-text','Diagnostic string itself is harmless; owning function may change control flow. Keep useful observability unless deliberately restoring that entire protocol.'
  elif len(t)<=5 and not re.search('[A-Za-z_]{3}',t):d,w='harmless-printable-run','Short printable run in a constant table is not established to be a string/configuration key; raw section hash remains available.'
  else:d,w='restore-with-owner','Runtime name/path/configuration or constant change. Follow owning namespace/VM/identity behavior; absence in this binary does not prove absence in the whole generation.'
  x.update(disposition=d,basis=w)
 c.save(R/'evidence'/kind/'strings-diff.json',ss)
 md['strings']['dispositions']=dict(collections.Counter(x['disposition'] for x in ss))
 c.save(R/'evidence'/kind/'metadata-diff.json',md)
results['provider_baseline_caveat']=json.loads((R/'provider-baseline-caveat.json').read_text())
results.update(stage='final-static-assessment',r2={'inventories':'verified','function_semantic_assessment':'partially','runtime_causality':'unverified'},reference_identity=json.loads((R/'reference-identity.json').read_text()))
c.save(R/'results.json',results);c.save(R/'function-assessments.json',report)
lines=['# All differing functions and supplemental linker blocks','','Provider rows now compare sealed R155 80c9aee0 against NEW 8d109259 (task56); the former 977fb347 provider interpretation is superseded. Each row has a bounded static recommendation. `restore` means restore to reproduce R155, not a proven fix. `retain-*` differences are intentional or useful changes that are not proven harmless and should not be blindly reverted. `unchanged-code` records remain in each functions.json. Raw line references and a register-erased diff accompany every changed row.','']
for k in c.INPUTS:
 lines += ['## '+k,'','| Function | State | Disposition | Evidence |','|---|---|---|---|']
 for x in report:
  if x['component']==k:lines.append(f"| `{x['name']}` | {x['state']} | {x['disposition']} | [{x['diff']}]({x['diff']}) |")
 lines+=['']
for i,x in enumerate(report,1):
 if x['name'].startswith('block:'):continue
 lines += [f"### {x['component']} `{x['name']}`",'',x['basis'],'','Evidence: '+', '.join('`'+e+'`' for e in x['evidence'])+'.','']
(R/'ALL-FUNCTIONS.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({k:v['function_dispositions'] for k,v in results['artifacts'].items()},indent=2))

# Version-qualified dynamic symbol names and object sizes must not be hidden by a base-name set.
for kind in c.INPUTS:
 def dynsym(v):
  text=(R/'evidence'/kind/v/'symbols.txt').read_text().split("Symbol table '.dynsym'",1)[1].split("Symbol table '.symtab'",1)[0]
  out={}
  for line in text.splitlines():
   m=re.match(r'\s*\d+:\s+[0-9a-f]+\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)',line)
   if m:
    name=re.sub(r' \(\d+\)$','',m[6]);out[name]=dict(type=m[2],bind=m[3],visibility=m[4],defined=m[5]!='UND',object_size=int(m[1]) if m[2] in ('OBJECT','TLS') else None)
  return out
 a,b=dynsym('r155'),dynsym('new');delta=[]
 for name in sorted(set(a)|set(b)):
  if a.get(name)!=b.get(name):delta.append(dict(name=name,r155=a.get(name),new=b.get(name),disposition='restore-with-owner',basis='Version-qualified ABI/data-size change; see corresponding stdio, loader, or provider family. No exported symbol removal in any pair.'))
 c.save(R/'evidence'/kind/'versioned-symbols-diff.json',delta)
 results['artifacts'][kind]['versioned_symbol_differences']=len(delta)
 # Mechanical coverage is based on decoded bytes as well as ELF function symbols.
 for v in ('r155','new'):
  inv=json.loads((R/'evidence'/kind/v/'inventory.json').read_text());cov=results['artifacts'][kind]['functions']['coverage'][v]
  cov['executable_section_bytes']=sum(s['size'] for s in inv['sections'] if s['flags']&4)
  cov['decoded_bytes']=cov['decoded_instructions']*4
  assert cov['executable_section_bytes']==cov['decoded_bytes']
  c.save(R/'evidence'/kind/v/'coverage.json',cov)
c.save(R/'results.json',results)
