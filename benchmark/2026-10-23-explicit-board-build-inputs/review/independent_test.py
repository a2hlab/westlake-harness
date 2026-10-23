from pathlib import Path
import hashlib,json,re,subprocess,shlex,sys
out=Path(__file__).resolve().parent
ws=out.parents[3];rel=Path('benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh')
sha=lambda b:hashlib.sha256(b).hexdigest()
label=sys.argv[1];run=out/'.private'/label;run.mkdir(parents=True,exist_ok=False)
sourcepath=ws/'westlake-harness-g10-env'/rel;basepath=ws/'westlake-harness'/rel
source=sourcepath.read_text();baseline=basepath.read_text();(run/'candidate-wrapper.sh').write_text(source);(run/'baseline-wrapper.sh').write_text(baseline)
def fixture(text,tag):
 root=run/(tag+' fixture');gb=root/'benchmark/2026-10-19-toutiao-icon-reentry';gen=gb/'generator';gen.mkdir(parents=True)
 dirs={'SRC':gb/'src','V':root/'benchmark/2026-10-12-v1-seal-assembly/restore-v6/package-composed-disabled/payload','R':root/'benchmark/2026-10-12-recovery-executor/payload'}
 for p in dirs.values():p.mkdir(parents=True)
 old='2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a';inert=b'# inert historical fixture, no executable controller\n';(dirs['V']/'watchdog.sh').write_bytes(inert);replace={old:sha(inert)}
 plan=text.split("<<'PLAN'\n",1)[1].split('\nPLAN',1)[0]
 for line in plan.splitlines():
  dst,kind,area,name,pin,mode,member=line.split();body=f'# inert fixture {area}/{name}\n'.encode()
  if kind=='sed-root':body+=b'ROOT=/fixture/old\n'
  if kind=='sed-wd':body+=('EXPECTED='+sha(inert)+'\n').encode()
  if kind=='sed-recovery':body+=b'{"service":"westlake-u13-toutiao-overlay","path":"/data/westlake-demo/toutiao/recovery-attempts/r1-9763171a-preview/entry.sh","ready":"sys.westlake.demo.u13.ready"}\n'
  (dirs[area]/name).write_bytes(body)
  if kind not in ['src','src-new']:replace[pin]=sha(body)
 parent=sha((dirs['R']/'real-start-parent-bounded.sh').read_bytes());bref=gen/'base-ref';bref.mkdir()
 values={'APPROVED_BY':'outer(codex)','ENABLED':'1','SERIAL':'61b0657200000000000000000324012c','OLD_STOP_SHA':'NONE','MEMBERS_SHA':'a'*64,'JIT_SHA':'b'*64,'NAMESPACE_SHA':'c'*64,'START_PARENT_SHA':parent,'HOST_SPAWN_SHA':'d'*64,'REQUEST_SHA':'e'*64,'DECODER_SHA':'f'*64,'PROBE_SHA':'1'*64,'TAP_WAIT_POLICY':'until-human-or-stop-or-boot-change'}
 template=''.join(f"STARTUP_{k}='{v}'\n" for k,v in values.items());(bref/'startup.env').write_text(template)
 replace['551169f521be3d9a20c0eae5821099eeb1b102c1812148fc8d8b06acacb461eb']=sha(template.encode())
 for n in ['members.tsv','startup.expected.sha256']:(bref/n).write_text('inert fixture\n')
 for k,v in replace.items():text=text.replace(k,v)
 script=gen/'derive-candidate.sh';script.write_text(text);(run/(tag+'-pin-map.json')).write_text(json.dumps(replace,indent=2)+'\n')
 return root,script,template,parent
root,script,template,parent=fixture(source,'candidate');br,bs,bt,bp=fixture(baseline,'baseline')
serial='5cd1e3dd00000000000000000923012c';template5=template.replace('61b0657200000000000000000324012c',serial)
cfg=root/"config ' quoted.env";cfg.write_text(template5)
common=['--serial',serial,'--root','/data/westlake-demo/toutiao/recovery-attempts/icon-manual-test','--owner-uid','20011300','--service','test-service','--startup-template',str(cfg),'--startup-template-sha256',sha(cfg.read_bytes())]
cases=[]
def test(name,args,expect='success',which=script,expect_fields=None):
 dest=run/(name+" out ' quoted");cmd=['/bin/sh',str(which),'--out',str(dest)]+args
 p=subprocess.run(cmd,capture_output=True);rec={'name':name,'argv':cmd,'rc':p.returncode,'expect':expect,'checks':{}}
 (run/(name+'.stdout')).write_bytes(p.stdout);(run/(name+'.stderr')).write_bytes(p.stderr)
 if expect=='reject':rec['checks']['rejected_without_generation']=p.returncode!=0 and not (dest/'generation.json').exists()
 else:
  rec['checks']['rc0']=p.returncode==0
  if p.returncode==0:
   try:g=json.loads((dest/'generation.json').read_text());rec['checks']['generation_json_valid']=True
   except Exception:g={};rec['checks']['generation_json_valid']=False
   if which==script:
    try:replay=shlex.split((dest/'build-command.txt').read_text());rec['checks']['argv_roundtrip']=replay==['sh']+cmd[1:]
    except Exception:rec['checks']['argv_roundtrip']=False
    rec['checks']['owner_uid_metadata_only']=g.get('owner_uid_scope')=='metadata_only'
    rec['checks']['not_deployable']=g.get('deployable') is False
   if expect_fields:
    for k,v in expect_fields.items():rec['checks']['exact_'+k]=g.get(k)==v
   if (dest/'payload/config-common.sh').exists() and '--root' in args:
    value=args[args.index('--root')+1];rec['checks']['exact_generated_root']=('ROOT='+value) in (dest/'payload/config-common.sh').read_text().splitlines()
   if '--serial' in args:
    value=args[args.index('--serial')+1];rec['checks']['exact_generated_serial']=('STARTUP_SERIAL='+"'"+value+"'") in (dest/'payload/startup.env').read_text().splitlines()
   if '--service' in args:
    try:recovery=json.loads((dest/'payload/recovery.cfg').read_text().splitlines()[-1]);rec['checks']['recovery_service_exact']=recovery['service']==args[args.index('--service')+1]
    except Exception:rec['checks']['recovery_service_exact']=False
 if expect=='safe_or_reject' and p.returncode!=0:rec['checks']={'rejected_without_output':not dest.exists()}
 rec['passed']=all(rec['checks'].values());cases.append(rec);(run/(name+'.receipt.json')).write_text(json.dumps(rec,indent=2)+'\n');return dest
bd=test('baseline_default',[],which=bs);cd=test('default',[])
basepayload={x.name:sha(x.read_bytes()) for x in (bd/'payload').iterdir()};newpayload={x.name:sha(x.read_bytes()) for x in (cd/'payload').iterdir()}
cases.append({'name':'default_payload_exact_baseline','passed':basepayload==newpayload,'checks':{'payload_hash_maps_equal':basepayload==newpayload}})
test('explicit',common,expect_fields={'serial':serial,'owner_uid':'20011300','service':'test-service','armed':False})
test('missing_sha',['--startup-template',str(cfg)],'reject')
test('missing_template',['--startup-template-sha256',sha(cfg.read_bytes())],'reject')
test('wrong_sha',common[:-1]+['0'*64],'reject')
test('short_sha',common[:-1]+['abc'],'reject')
test('uppercase_sha',common[:-1]+[sha(cfg.read_bytes()).upper()],'reject')
test('explicit_enable',common+['--enable','--approved-by','outer(codex)'],'reject')
for name,content in [('missing_jit',template5.replace("STARTUP_JIT_SHA='"+'b'*64+"'\n",'')),('duplicate_request',template5+"STARTUP_REQUEST_SHA='"+'e'*64+"'\n"),('unknown_request',template5.replace('e'*64,'unknown')),('wrong_parent',template5.replace(parent,'0'*64)),('serial_mismatch',template),('shell_expression',template5+"EXTRA=$(printf unsafe)\n")]:
 p=root/(name+'.env');p.write_text(content);test(name,common[:-4]+['--startup-template',str(p),'--startup-template-sha256',sha(p.read_bytes())],'reject')
for name,flag,value in [('root_ampersand','--root','/data/westlake-demo/toutiao/recovery-attempts/icon-manual-a&b'),('service_ampersand','--service','test&service'),('service_quote','--service','test"service'),('service_pipe','--service','test|service'),('uid_quote','--owner-uid','20"011300'),('serial_ampersand','--serial','board&test')]:
 test(name,[flag,value],'safe_or_reject',expect_fields={flag[2:].replace('-','_'):value})
test('default_enable',['--enable','--approved-by','outer(codex)'],expect_fields={'armed':True,'startup_enabled':1})
(root/'benchmark/2026-10-19-toutiao-icon-reentry/generator/base-ref/startup.env').write_text(template+'# tampered\n');test('default_pin_drift',[],'reject')
result={'candidate_sha256':sha(source.encode()),'baseline_sha256':sha(baseline.encode()),'fixture_scope':'Only wrappers read; entirely inert synthetic payloads, fixture-only pin substitution; no actual controller or prohibited source read/execution.','cases':cases,'passed':sum(x['passed'] for x in cases),'total':len(cases),'failures':[x['name'] for x in cases if not x['passed']]}
(run/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))

sys.exit(0 if all(x["passed"] for x in cases) else 1)
