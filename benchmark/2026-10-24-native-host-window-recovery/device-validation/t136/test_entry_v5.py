"""T146: entry-version regression; runs on public fixtures + synthetic bytes, fresh-clone safe."""
"""Offline production-path checks; never constructs a live Window."""
import importlib.util,json,tempfile
from pathlib import Path
P=Path(__file__).resolve().parent
import t146_patch as _t146
spec=importlib.util.spec_from_file_location('t136_entry',P/'execute_v5.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
import t146_patch as _t146
_t146.patch_module(m)
checks=[]
assert m.linux_device_pair(66352)==(259,48)==tuple(int(x,16) for x in '103:30'.split(':'))
checks.append('actual_linux_stat66352_matches_maps103_30_and_mount259_48')
text=(P/'execute_v5.py').read_text()
assert 'enumerate((5,30,60,90))' in text and '((30,60,90,120)[index])' in text
checks.append('last_frame90_review_deadline120')
def case(name,fn):fn();checks.append(name)
assert not m.same_process(dict(pid=1,birth=2,uid=3),dict(pid=1,birth=4,uid=3));checks.append('same_pid_new_birth_is_different')
# Exercise the actual power-maintenance method against deterministic device replies.
for initial,verify,fail in [(None,600000,False),(10000,600000,False),(None,None,True),(600000,600000,False)]:
 w=object.__new__(m.Window);w.prepower={'base':30000,'override':10000};w.held=lambda:None;seq=iter([dict(base=30000,override=initial,state='AWAKE'),dict(base=30000,override=verify,state='AWAKE')]);w.power=lambda label:next(seq);calls=[];w.shell=lambda label,cmd:calls.append(cmd)
 try:w.keepawake('synthetic');failed=False
 except AssertionError:failed=True
 assert failed==fail
 if initial is None:assert calls==['power-shell timeout -o 600000']
 checks.append('override_'+str(initial)+'_post_'+str(verify))
# Run the actual try/finally path with a stopped publication and synthetic recovery.
with tempfile.TemporaryDirectory(prefix='entry-test-') as d:
 w=object.__new__(m.Window);w.run=Path(d);w.owner=None;w.start=None;w.n=0;w.recovery=False;w.publish_attempted=False;w.backup=None;w.prepower=None;w.published=None;w.original=None;w.result={}
 obj=dict(dev=66352,inode=560578,uid=20011206,gid=20011206,mode='644',size=2023136,mtime=1,selinux=m.LABEL,sha256=m.BASELINE)
 ident={'boot':'original','processes':[]};actions=[]
 w.bind=lambda label,expected:(ident,obj.copy());w.admit=lambda label:(ident,obj.copy());w.power=lambda label:dict(base=30000,override=10000,state='AWAKE');w.held=lambda:None;w.elapsed=lambda:1
 def call(label,argv,allow_failure=False):
  actions.append(label)
  if label in ('held-before','final-held'):return {'local_rc':1},'', ''
  if label=='held-acquired':return {'local_rc':0},m.LANE+' 123 now',''
  if label=='preimage-recv':(w.run/'baseline.so').write_bytes((m.INPUT/'rollback.so').read_bytes())
  return {'local_rc':0},'', ''
 w.call=call
 def object_(label,path):
  if label.startswith('system'):return dict(obj,sha256=m.SYSTEM_SHA)
  if label in ('staged','rollback-current'):return dict(obj,sha256=m.CANDIDATE,inode=560579)
  return obj.copy()
 w.object=object_
 def shell(label,command):
  actions.append(label)
  if label=='atomic-publish':raise RuntimeError('synthetic publication result unknown')
  return ''
 w.shell=shell;w.reboot=lambda label:actions.append(label);w.stage=lambda *a:ident;w.screen=lambda label:actions.append(label)
 w.run_window()
 assert actions.index('atomic-publish')<actions.index('atomic-rollback')<actions.index('rollback-reboot')<actions.index('power-restore')<actions.index('unlock')
 assert w.result['rollback']=='verified' and w.result['released']
 checks.append('actual_finally_after_unknown_publish_restores_before_unlock')

# Actual reboot path: boot completion, power readiness, failed UI dump, bad JSON, then valid JSON.
with tempfile.TemporaryDirectory(prefix='boot-test-') as d:
    w=object.__new__(m.Window);w.run=Path(d);w.n=0;w.held=lambda:None;w.identity=lambda label:{'boot':'old'};attempt=[0];seen=[]
    w.keepawake=lambda label:seen.append(label+'-keepawake')
    def call(label,argv,allow_failure=False):
        w.n+=1;seen.append(label)
        if label.endswith('-boot-completion-poll'):
            attempt[0]+=1
            return {'local_rc':0},'12345678-1234-1234-1234-123456789abc\n'+('false' if attempt[0]==1 else 'true')+'\n',''
        if label.endswith('-power-service-poll'):return {'local_rc':0},('' if attempt[0]==2 else 'Current State: SLEEP\nScreenOffTime: Timeout=30000ms'),''
        if label.endswith('-layout-readiness'):
            assert seen[-2]=='synthetic-boot-ui-keepawake', 'wake must precede each readiness dump'
            return {'local_rc':0},('DumpLayout failed:Get window nodes failed\nT136_UI_RC:1' if attempt[0]==3 else 'T136_UI_RC:0'),''
        if label.endswith('-layout-recv'):
            Path(argv[-1]).write_text('{' if attempt[0]==4 else '{"attributes":{"bounds":"[0,0][1200,1920]"}}')
        return {'local_rc':0},'',''
    w.call=call;sleep=m.time.sleep;m.time.sleep=lambda seconds:None
    try:assert w.reboot('synthetic')=='12345678-1234-1234-1234-123456789abc' and attempt[0]==5 and seen.count('synthetic-boot-ui-keepawake')==3
    finally:m.time.sleep=sleep
checks.append('boot_false_power_missing_then_awake_before_each_dump_failure_bad_json_ready')
# Actual desktop path handles the ordinary charge-only dialog and one fresh page swipe.
with tempfile.TemporaryDirectory(prefix='desktop-test-') as d:
    w=object.__new__(m.Window);w.run=Path(d);actions=[];w.ui=lambda label,command:actions.append(command)
    target={'attributes':{'id':'AppIconCommonView_org.westlake.imehost.EntryAbility','bounds':'[53,98][326,371]','visible':'true','enabled':'true','clickable':'true'}}
    tree={'attributes':{'bounds':'[0,0][1200,1920]','bundleName':'com.ohos.sceneboard'},'children':[{'attributes':{'id':'SwiperPage_Grid_WorkSpace0'}}]}
    def screen(label):
        t=json.loads(json.dumps(tree))
        if label.endswith('-page-1'):t['children'].append(target)
        (w.run/(label+'.layout.json')).write_text(json.dumps(t));return {'label':label}
    w.screen=screen
    def review(pic,deadline):
        if pic['label']=='synthetic':return {'verdict':'usb_dialog','xy':[600,1183]}
        return {'verdict':'desktop'}
    w.review=review;m.time.sleep=lambda seconds:None
    try:assert w.desktop('synthetic',m.time.monotonic()+120)==[189,234]
    finally:m.time.sleep=sleep
    assert actions==['click 600 1183','swipe 960 960 240 960 600']
checks.append('production_desktop_usb_confirmation_and_fresh_page_target')

source=json.loads(m.IDLE_SOURCE.read_text())
base_identity=dict(source['identity'],processes=[x for x in source['identity']['processes'] if x['name']!='com.ss.android.article.news'])
for name in ['idle_exact','wrong_boot','host_birth','parent_uid','wrong_inode','wrong_mtime','identity_drift','two_children','one_child_strict']:
    with tempfile.TemporaryDirectory(prefix='idle-test-') as d:
        w=object.__new__(m.Window);w.run=Path(d);w.result={};identity=json.loads(json.dumps(base_identity));source['object']['sha256']=m.BASELINE;obj=source['object'].copy();strict=[]
        if name=='wrong_boot':identity['boot']='wrong'
        if name=='host_birth':identity['processes'][0]['birth']+=1
        if name=='parent_uid':identity['processes'][1]['uid']=20011206
        if name=='wrong_inode':obj['inode']+=1
        if name=='wrong_mtime':obj['mtime']+=1
        if name in ('two_children','one_child_strict'):
            child=source['identity']['processes'][-1];identity['processes'].append(child)
            if name=='two_children':identity['processes'].append(dict(child,pid=99999))
        def identify(label):
            if name=='identity_drift' and label.endswith('identity-after'):return dict(identity,boot='changed')
            return identity
        w.identity=identify;w.object=lambda label,path:obj
        def strict_bind(label,expected):strict.append(expected);return identity,obj
        w.bind=strict_bind
        try:w.admit('fixture');failed=False
        except (AssertionError,RuntimeError):failed=True
        assert failed==(name not in ('idle_exact','one_child_strict')),name
        if name=='idle_exact':assert w.result['mapping_now']=='not_running' and not strict
        if name=='one_child_strict':assert strict==[m.BASELINE] and w.result['mapping_now']=='strict_current_mapping_verified'
        checks.append(name)
print(json.dumps({'synthetic_only':True,'checks':checks,'passed':len(checks)}))
