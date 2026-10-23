#!/usr/bin/env python3
"""Exercise production wrapper with entirely synthetic files and fixture-only SHA substitution."""
from pathlib import Path
import hashlib,json,re,subprocess,tempfile,shlex,time,argparse
P=Path(__file__).resolve().parent
REPO=P.parents[1]
SCRIPT=REPO/'benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh'
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest()
source=SCRIPT.read_text();assert 'SENV_PIN=551169f521be3d9a20c0eae5821099eeb1b102c1812148fc8d8b06acacb461eb' in source
reports=[]
with tempfile.TemporaryDirectory(prefix='t118-fixture-') as tmp:
 root=Path(tmp);gb=root/'benchmark/2026-10-19-toutiao-icon-reentry';gen=gb/'generator';gen.mkdir(parents=True)
 dirs={'V':root/'benchmark/2026-10-12-v1-seal-assembly/restore-v6/package-composed-disabled/payload','R':root/'benchmark/2026-10-12-recovery-executor/payload','SRC':gb/'src'}
 for d in dirs.values():d.mkdir(parents=True)
 plan=source.split("<<'PLAN'\n",1)[1].split('\nPLAN',1)[0]
 old='2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a';basewd=b'# synthetic inert base\n';replacements={old:sha(basewd)}
 (dirs['V']/'watchdog.sh').write_bytes(basewd)
 for line in plan.splitlines():
  dst,transform,sr,name,pin,mode,member=line.split()
  b=('# synthetic inert fixture '+sr+'/'+name+'\n').encode()
  if transform=='sed-root':b+=b'ROOT=/synthetic/old\n'
  if transform=='sed-wd':b+=('EXPECTED='+sha(basewd)+'\n').encode()
  (dirs[sr]/name).write_bytes(b)
  if transform not in ['src','src-new']:replacements[pin]=sha(b)
 bref=gen/'base-ref';bref.mkdir()
 parent=sha((dirs['R']/'real-start-parent-bounded.sh').read_bytes())
 keys=['MEMBERS_SHA','JIT_SHA','NAMESPACE_SHA','START_PARENT_SHA','HOST_SPAWN_SHA','REQUEST_SHA','DECODER_SHA','PROBE_SHA']
 template="STARTUP_APPROVED_BY='outer(codex)'\nSTARTUP_ENABLED='1'\nSTARTUP_SERIAL='61b0657200000000000000000324012c'\nSTARTUP_OLD_STOP_SHA='NONE'\n"+''.join("STARTUP_%s='%s'\n"%(k,parent if k=='START_PARENT_SHA' else 'a'*64) for k in keys)+"STARTUP_TAP_WAIT_POLICY='until-human-or-stop-or-boot-change'\n"
 (bref/'startup.env').write_text(template);replacements['551169f521be3d9a20c0eae5821099eeb1b102c1812148fc8d8b06acacb461eb']=sha(template.encode())
 for n in ['members.tsv','startup.expected.sha256']:(bref/n).write_text('synthetic\n')
 fixture=source
 for k,v in replacements.items():fixture=fixture.replace(k,v)
 script=gen/'derive-candidate.sh';script.write_text(fixture)
 (a.out/'fixture-pin-substitutions.json').write_text(json.dumps(replacements,indent=2))
 explicit=template.replace('61b0657200000000000000000324012c','5cd1e3dd00000000000000000923012c');cfg=root/"board ' config.env";cfg.write_text(explicit)
 def case(name,args,ok,config=None):
  target=root/(name+' output');c=cfg
  if config is not None:c=root/(name+'.env');c.write_text(config)
  ext=[str(c) if x=='CFG' else sha(c.read_bytes()) if x=='SHA' else x for x in args]
  cmd=['/bin/sh',str(script),'--out',str(target)]+ext
  log=a.out/name;log.mkdir();(log/'argv.json').write_text(json.dumps(cmd));(log/'start').write_text(str(time.time()));r=subprocess.run(cmd,capture_output=True)
  for suffix,b in [('stdout',r.stdout),('stderr',r.stderr),('rc',str(r.returncode).encode()),('end',str(time.time()).encode())]:(log/suffix).write_bytes(b)
  passed=(r.returncode==0)==ok
  if ok and r.returncode==0:
   argv=shlex.split((target/'build-command.txt').read_text());passed &= argv==['sh']+cmd[1:]
   g=json.loads((target/'generation.json').read_text());passed &= g['deployable'] is False
   if '--startup-template' in ext:passed &= g['armed'] is False and g['startup_template_sha256']==sha(c.read_bytes())
  if not ok:passed &= not (target/'generation.json').exists()
  reports.append(dict(case=name,rc=r.returncode,expected_success=ok,pass_=bool(passed)))
 explicit_args=['--serial','5cd1e3dd00000000000000000923012c','--owner-uid','20011300','--root','/data/westlake-demo/toutiao/recovery-attempts/icon-manual-fixture','--service','fixture-service','--startup-template','CFG','--startup-template-sha256','SHA']
 case('default',[],True)
 case('explicit',explicit_args,True)
 case('missing_sha',['--startup-template','CFG'],False)
 case('missing_template',['--startup-template-sha256','a'*64],False)
 case('wrong_sha',explicit_args[:-1]+['0'*64],False)
 case('wrong_parent',explicit_args,False,explicit.replace(parent,'b'*64))
 case('unknown_jit',explicit_args,False,explicit.replace("STARTUP_JIT_SHA='"+'a'*64+"'","STARTUP_JIT_SHA='unknown'"))
 case('unknown_old_stop',explicit_args,False,explicit.replace("STARTUP_OLD_STOP_SHA='NONE'","STARTUP_OLD_STOP_SHA='unknown'"))
 case('missing_field',explicit_args,False,explicit.replace("STARTUP_REQUEST_SHA='"+'a'*64+"'\n",''))
 case('duplicate_field',explicit_args,False,explicit+"STARTUP_JIT_SHA='"+'a'*64+"'\n")
 case('shell_data',explicit_args,False,explicit+"$(touch NEVER)\n")
 case('serial_mismatch',explicit_args,False,template)
 for name,flag,value in [('root_ampersand','--root','/data/westlake-demo/toutiao/recovery-attempts/icon-manual-a&b'),('root_traversal','--root','/data/westlake-demo/toutiao/recovery-attempts/icon-manual-a/../b'),('service_ampersand','--service','a&b'),('service_quote','--service','a"b'),('service_pipe','--service','a|b'),('uid_quote','--owner-uid','20"011300'),('uid_negative','--owner-uid','-1'),('serial_ampersand','--serial','board&test')]:
  case(name,[flag,value],False)
 case('explicit_enable',explicit_args+['--enable','--approved-by','outer(codex)'],False)
 # Tamper only the synthetic default input; production default validation must reject.
 (bref/'startup.env').write_text(template+'# drift\n');case('default_pin_drift',[],False)
result={'production_wrapper_sha256':sha(SCRIPT.read_bytes()),'fixture_scope':'Only wrapper read; every runtime payload synthesized as inert text; fixture-only pin substitutions recorded. No real controller executed.','cases':reports,'passed':sum(x['pass_'] for x in reports),'total':len(reports)}
(a.out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(0 if all(x['pass_'] for x in reports) else 1)
