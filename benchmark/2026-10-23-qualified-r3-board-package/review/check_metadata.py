#!/usr/bin/env python3
"""Offline metadata/hash audit. Never imports, sources or executes payloads."""
import hashlib,json,shlex,stat
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]; WS=REPO.parent
OWNER=WS/'westlake-harness-g10-env'; MAIN=WS/'westlake-harness'; VIDEO=WS/'westlake-harness-video'
D=OWNER/'benchmark/2026-10-23-qualified-r3-board-package'; B=D/'.private/build-02'; P=B/'package'
T34=Path.home()/'.local/share/westlake/t34-reentry-retirement-20261021'
def read(p): return json.loads(p.read_text())
def sha(p):
 with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def resolve(s):
 for a,p in [('$OWNER/',OWNER),('$VIDEO/',VIDEO),('$T34/',T34)]:
  if s.startswith(a):return p/s[len(a):]
 return MAIN/s
checks=[]
def ck(n,v):
 checks.append({'check':n,'pass':bool(v)})
r=read(D/'results.json'); manifest=read(D/'manifest.json')
for n,h in manifest.items():ck('public:'+n,sha(D/n)==h)
for n,h in r['metadata_pins'].items():ck('metadata:'+n,sha(resolve(n))==h)
chain=read(MAIN/'benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/deploy-package-r3-root/CHAIN.json')
base=read(MAIN/'benchmark/2026-10-19-toutiao-icon-reentry/generator/base-pins.json')
expected={base['source_roots'][x['source']]+'/'+x['source_name']:x['sha256'] for x in base['files']}
src='benchmark/2026-10-19-toutiao-icon-reentry/src/'
for name in ['watchdog-reentry.sh','reentry-common.sh','reentry-seams.sh','exit-verdict.sh']:
 expected[src+name]=chain['payload_manifest']['payload/'+('watchdog.sh' if name=='watchdog-reentry.sh' else name)]
builder='benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh'
expected[builder]='0862a334f863d4de3bf3d4c4dda7ab1df7c6000e3b0e3d02e6c46f014aaf84d3'
inputs=read(D/'input-manifest.json'); ck('24 approved inputs',len(inputs)==len(expected)==24)
for x in inputs:
 ck('input:'+x['staged'],sha(B/'staged'/x['staged'])==sha(resolve(x['source']))==x['sha256']==expected.get(x['staged']) and (B/'staged'/x['staged']).stat().st_size==x['bytes'])
outputs=read(D/'output-manifest.json');actual={str(p.relative_to(P)):sha(p) for p in (P/'payload').iterdir() if p.is_file()}
ck('22 exact actual outputs',actual==outputs and len(actual)==22)
fixed=[n for n,h in actual.items() if chain['payload_manifest'].get(n)==h]
ck('17 fixed historical outputs',len(fixed)==17)
changed_r3=sorted(set(actual)-set(fixed))
g=read(P/'generation.json');ck('generation receipt exact',g==r['generation'])
argv=read(B/'build/argv.json')['argv']; opts=dict(zip(argv[2::2],argv[3::2]))
for opt,key in [('--root','root'),('--serial','serial'),('--owner-uid','owner_uid'),('--service','service'),('--startup-template-sha256','startup_template_sha256')]:ck('argv:'+opt,opts[opt]==g[key])
ck('argv exact staged builder',Path(argv[1]).resolve()==(B/'staged'/builder).resolve())
recorded=shlex.split((P/'build-command.txt').read_text());ck('complete recorded argv',recorded[1:]==argv[1:] and Path(recorded[0]).name==Path(argv[0]).name)
ck('template SHA',sha(B/'startup-5cd.disabled.env')==g['startup_template_sha256'])
fields={}
for line in (P/'payload/startup.env').read_text().splitlines():
 if line and not line.startswith('#'):
  k,v=line.split('=',1);fields[k]=shlex.split(v)[0]
ck('disabled data',fields['STARTUP_ENABLED']=='0' and fields['STARTUP_APPROVED_BY']=='DISABLED-PENDING-OUTER' and g['armed'] is False and g['deployable'] is False)
ck('serial data',fields['STARTUP_SERIAL']==g['serial'])
for field,file in [('STARTUP_START_PARENT_SHA','real-start-parent-bounded.sh'),('STARTUP_MEMBERS_SHA','members.tsv'),('STARTUP_DECODER_SHA','screen-gate'),('STARTUP_PROBE_SHA','decoder-probe.jpeg')]:ck('cascade:'+field,fields[field]==actual['payload/'+file])
ck('startup expected SHA',(P/'payload/startup.expected.sha256').read_text().strip()==actual['payload/startup.env'])
members=[]
for line in (P/'payload/members.tsv').read_text().splitlines():
 h,n,m=line.split();members.append(n);ck('member:'+n,actual['payload/'+n]==h)
ck('16 unique members',len(members)==len(set(members))==16)
statrows=[{'path':n,'sha256':h,'bytes':(P/n).stat().st_size,'mode':oct(stat.S_IMODE((P/n).stat().st_mode))} for n,h in sorted(actual.items())]
for n,x in r['build_receipts'].items():ck('raw build:'+n,sha(B/'build'/n)==x['sha256'] and (B/'build'/n).stat().st_size==x['bytes'])
ck('raw rc0 empty stderr',(B/'build/rc').read_text().strip()=='0' and (B/'build/stderr').stat().st_size==0)
ck('raw start end',float((B/'build/end').read_text())>=float((B/'build/start').read_text()))
index=read(VIDEO/'benchmark/2026-10-23-current-control-fingerprint/index.json')['boards']['5cd']
depbase=VIDEO/'benchmark/2026-10-23-board-package-dependency-identities'
t119=read(depbase/'results.json');add=read(depbase/'addendum/results.json')
ck('same boot evidence',len({index['boot_pre'],index['boot_post'],t119['boot_pre'],t119['boot_post'],add['boot_pre'],add['boot_post'],r['external_evidence_boot']})==1)
ck('UID metadata matches observed',set(t119['host']['uid']+add['host']['uid'])=={g['owner_uid']})
ck('target serial',index['serial']==g['serial']==t119['device'])
deps={x['field']:x for x in t119['declared_vs_actual']+add['declared_vs_actual']}
external=[]
for x in read(D/'external-bindings.json'):
 e=deps[x['field']];h=e.get('sha256',e.get('actual_sha256'));ck('external:'+x['field'],fields[x['field']]==h and x['path']==e['path'] and e['stable'])
 short=x['field'].removeprefix('STARTUP_').removesuffix('_SHA');sub='addendum/raw' if short in ['JIT','REQUEST'] else 'raw'
 raw=depbase/sub/('dep_'+short+'.stdout'); rc=raw.with_suffix('.rc')
 ck('external raw:'+short,raw.exists() and h in raw.read_text() and e['path'] in raw.read_text() and rc.read_text().strip()=='0')
 external.append({'field':x['field'],'path':e['path'],'sha256':h,'evidence':str(raw.relative_to(VIDEO)),'evidence_sha256':sha(raw)})
current={x['path']:x['sha256'] for x in index['hash_only_files']+index['config_files'] if x.get('exists') and x.get('sha256')}
diffs=[]
for n,h in sorted(actual.items()):
 name=Path(n).name;old=current.get(index['root']+'/'+name)
 diffs.append({'name':name,'current_root_sha':old,'candidate_sha':h,'comparison':'not_in_current_index' if old is None else 'same' if h==old else 'different'})
ck('exact current-root difference',diffs==read(D/'changes.json'))
init=r['init_proposal'];svc=next(x for x in index['init_cfg']['services'] if x['name']==g['service'])
ck('init preimage and single argv proposal',init['current_sha256']==index['init_cfg']['sha256'] and init['current_path']==index['init_cfg']['path'] and init['before_argv']==svc['path'] and init['proposed_argv']==[svc['path'][0],g['root']+'/boot-entry.sh'] and init['apply'] is False)
result={'status':'PASS_DISABLED_PACKAGE_METADATA' if all(x['pass'] for x in checks) else 'FAIL','scope':'One build-02 candidate; hash/stat and data only; zero controller execution/device calls; no implementation text read','builder_sha256':expected[builder],'author_manifest_sha256':sha(D/'manifest.json'),'checks':checks,'counts':{'passed':sum(x['pass'] for x in checks),'total':len(checks),'inputs':len(inputs),'outputs':len(actual),'historically_fixed':len(fixed),'members':len(members)},'changed_vs_r3':changed_r3,'outputs':statrows,'external_bindings':external,'boot':r['external_evidence_boot'],'identity':{k:g[k] for k in ['root','serial','owner_uid','owner_uid_scope','service','startup_enabled','armed','deployable']},'startup_parent_sha256':fields['STARTUP_START_PARENT_SHA'],'current_root_differences':diffs,'difference_counts':dict(Counter(x['comparison'] for x in diffs)),'rollback_scope':{'old_root':index['root'],'old_root_written_or_deleted':False,'only_overwrite':'current init single argv; restore exact original init bytes to return to old ROOT','init_preimage':init,'unknown_index_entries':'Five not_in_current_index entries remain unknown; not evidence of absence, not overwritten by separate new ROOT','promotion':'T121 separately reviewed; exact byte restoration not executed or certified by this offline package audit'},'limitations':['UID metadata does not prove runtime UID behavior','Historical61b success does not prove5cd behavior','Hash bindings do not establish controller semantics or deployment readiness']}
(HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'counts':result['counts'],'differences':result['difference_counts'],'failed':[x for x in checks if not x['pass']]}))
raise SystemExit(0 if result['status'].startswith('PASS') else 1)
