"""Exact BMS identity from original same-boot raw receipts, and fresh checks before writes."""
import json,re,shlex
PACKAGE='com.Unity3d.BoatAttackDay'
DUMP='bm dump -n '+PACKAGE
BOOT='cat /proc/sys/kernel/random/boot_id'
def need(ok,msg):
    if not ok:raise ValueError(msg)
def parse(text):
    prefix=PACKAGE+':'
    need(text.strip().startswith(prefix),'BMS package prefix missing')
    obj=json.loads(text.strip()[len(prefix):].strip())
    uid=obj.get('uid');app=obj.get('applicationInfo',{})
    need(obj.get('name')==PACKAGE and app.get('name')==PACKAGE,'BMS package mismatch')
    need(type(uid) is int and 20000000<=uid<20200000 and app.get('uid')==uid,'BMS application UID invalid/inconsistent')
    users=[u for u in obj.get('userInfo',[]) if u.get('bundleUserInfo',{}).get('userId')==100]
    need(len(users)==1 and users[0].get('bundleName')==PACKAGE and users[0].get('uid')==uid,'BMS user100 identity mismatch')
    need(obj.get('versionCode')==1 and obj.get('versionName')=='0.9','fixed Boat APK version mismatch')
    return uid

def observation(ref,command,serial,pin,read):
    need(set(ref)=={'receipt','stdout','stderr'},'dedicated BMS/boot triplet required')
    receipt=read(pin(ref['receipt']));stdout=pin(ref['stdout']).read_text();stderr=pin(ref['stderr']).read_text()
    need(receipt.get('rc')==0 and not stderr.strip(),'capture transport failed')
    argv=receipt['argv'];need(len(argv)==5 and argv[1:4]==['-t',serial,'shell'],'capture serial/argv')
    prefix='/system/bin/sh -c '+shlex.quote(command)+'; capture_rc=$?; printf '
    need(argv[4].startswith(prefix),'capture logical command differs')
    tail=shlex.split(argv[4][len(prefix):]);need(len(tail)==2 and tail[1]=='$capture_rc','capture rc command')
    match=re.fullmatch(r'\\n(__CAPTURE_RC_[a-f0-9]+__)%s\\n',tail[0]);need(match,'capture marker command')
    marker=match[1];end=re.search(r'\n'+re.escape(marker)+r'([0-9]+)\s*$',stdout)
    need(end and end[1]=='0','remote capture failed/missing marker')
    start,finish=receipt['started'],receipt['finished']
    need(type(start) in (int,float) and type(finish) in (int,float) and start<=finish,'capture time ordering')
    return stdout[:end.start()].strip(),start,finish

def validate(ref,serial,boot,uid,pin,read):
    need(set(ref)=={'boot_before','bundle','boot_after'},'dedicated bookended Boat identity required')
    before=observation(ref['boot_before'],BOOT,serial,pin,read)
    bundle=observation(ref['bundle'],DUMP,serial,pin,read)
    after=observation(ref['boot_after'],BOOT,serial,pin,read)
    need(before[0]==after[0]==boot and before[2]<=bundle[1]<=bundle[2]<=after[1],'BMS observation not same boot/ordered')
    need(parse(bundle[0])==uid,'captured UID not derived from BMS')

def fresh(plan,dev):
    need(dev.shell('boat-uid-boot-before',BOOT)==plan.get('_active_boot',plan['boot_id']),'UID boot before')
    need(parse(dev.shell('boat-uid-readonly',DUMP))==plan['boat_uid'],'actual BMS UID changed; no writes allowed')
    need(dev.shell('boat-uid-boot-after',BOOT)==plan.get('_active_boot',plan['boot_id']),'UID boot after')
