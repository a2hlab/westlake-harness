"""Exact existing5cd sources; no61b control-root or WID substitution, no device calls."""
import functools,hashlib,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
SERIAL='5cd1e3dd00000000000000000923012c'
CONTROL='/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012'

def need(ok,msg):
    if not ok:raise ValueError(msg)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def path(text):
    p=Path(os.path.expandvars(text));return p if p.is_absolute() else HERE/p

def validate_sources():
    refs=read(HERE/'source-pins.json')
    docs={}
    for key in ('selfcheck','activation_binding','realization','prepared_manifest','prepared_plan','full_readonly','preinstall_capture','live_selfcheck'):
        ref=refs[key];p=path(ref['path']);need(sha(p)==ref['sha256'],'5cd source pin drift: '+key);docs[key]=read(p)
    # These three fixed receipts, not a mutable candidate field, establish the board-specific source.
    for key,h in FIXED.items():need(refs[key]['sha256']==h,'unreviewed5cd source: '+key)
    checked=docs['selfcheck'];binding=docs['activation_binding'];proof=docs['realization'];full=docs['full_readonly'];prepared=docs['prepared_plan']
    need(checked['serial']==SERIAL and checked['passed'] is True and checked['status']=='PASS' and checked['mode']=='live-readonly' and checked['synthetic'] is False,'original5cd actual R5 required')
    need(checked['activation']['binding']==refs['activation_binding'] and binding['realization']==refs['realization'] and binding['prepared_manifest']==refs['prepared_manifest'],'5cd activation origin binding')
    parameters=proof['parameters']
    need(parameters['serial']==SERIAL and parameters['host_uid']==parameters['host_gid']==20011300 and parameters['control_root']==CONTROL,'actual5cd host/control scope')
    entry=next(x for x in docs['prepared_manifest']['files'] if x['path']=='plan.json')
    need(entry['sha256']==refs['prepared_plan']['sha256'],'prepared487 plan manifest pin')
    checks=checked['checks'];expected={x['target']:x['actual'] for x in checks}
    need(len(checks)==len(expected)==940 and all(x['equal'] is True and x['expected']==x['actual'] for x in checks),'all original940 checks')
    need(full['serial']==SERIAL and full['boot_before']==full['boot_after']==checked['current_boot'] and full['status']=='READONLY_HASH_INVENTORY_COMPLETE' and full['differences']=={},'sameboot complete5cd inventory')
    need(full['expected']==full['actual']==expected and set(full['metadata'])==set(expected),'full940 exact membership/SHA/metadata')
    need(full['source']['sha256']==refs['selfcheck']['sha256'],'full readout originalR5 reference')
    live=docs['live_selfcheck']
    need(live['serial']==SERIAL and live['status']=='PASS' and live['passed'] is True and live['mode']=='live-readonly' and live['synthetic'] is False,'actual current5cd full live R5 required')
    need(live['boot_before']==live['boot_after']==full['boot_before'] and live['activation']['binding']==refs['activation_binding'],'current5cd live boot/binding')
    live_checks=live['checks']
    need(len(live_checks)==940 and {x['target']:x['actual'] for x in live_checks}==expected and all(x['equal'] is True and x['expected']==x['actual'] for x in live_checks),'live940 exact source match')
    targets=[x['target'] for x in prepared['members']]
    need(prepared['serial']==SERIAL and len(targets)==len(set(targets))==487,'original5cd487 target membership')
    controls=[x for x in targets if x.startswith('/data/westlake-demo/toutiao/recovery-attempts/')]
    need(controls and all(x.startswith(CONTROL+'/') for x in controls),'do not inherit61b control directory')
    hap='/data/app/el1/bundle/public/org.westlake.imehost/entry.hap'
    protected={t:expected[t] for t in targets+[hap]};need(len(protected)==488,'487 plus HAP')
    dynamic=checked['dynamic_receipt'];ev=dynamic['parameter_evidence']
    need(ev['serial']==SERIAL and ev['boot_id']==checked['current_boot'] and ev['host_uid']==ev['host_gid']==20011300 and ev['control_root']==CONTROL,'actual5cd dynamic observation')
    need(dynamic['current_boot']==checked['current_boot'] and expected[dynamic['target']]==dynamic['sha256'],'observed full run.sh SHA')
    return dict(protected=protected,metadata=full['metadata'],all940=expected,control_root=CONTROL,host_uid=20011300,placement_boot=parameters['boot_id'],current_boot=full['boot_before'],historical_observed_window_id=ev['window_id'],refs=refs)

# Fixed accepted source content; new boot/WID changes require a separately reviewed exact source.
FIXED={'selfcheck': '542c5176572dcde4ad8a89718bed486dca585457a3326dd5924b6e02026bceff', 'activation_binding': 'c151abb82d8ca127010e0ad93fd9cbb79b1b71ac31465d46bc1667a481df7869', 'full_readonly': '5ec97261c5bcc9c1b885616def1aeb3309a7be7cd1ea83494b30bb15377d94cf', 'live_selfcheck': '0c80b5032dc53ac2928faed89d649d5f150aae72b80b560e801e9ff2bc2fc921'}
