#!/usr/bin/env python3
"""T136 single-library, single-owner observation. Requires a separate outer receipt.
No old executor/controller is imported. All visual decisions are external receipts.
"""
import argparse, datetime, hashlib, json, os, re, shlex, subprocess, sys, time, uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=next(p for p in HERE.parents if (p/'scripts/lab/lab_paths.py').is_file())
sys.path.insert(0,str(REPO/'scripts/lab'))
import lab_paths
MAIN=lab_paths.harness()
INPUT=REPO/'.private/t136-native-validation-input'
HDC='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
SERIAL='61b0657200000000000000000324012c'
CANDIDATE='3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819'
BASELINE='b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4'
SYSTEM_SHA='8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e'
TARGET='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/liboh_adapter_bridge.so'
SYSTEM='/system/android/lib64/liboh_adapter_bridge.so'
MAPPED='/data/local/tmp/asx/liboh_adapter_bridge.so'
UID=20011206
LABEL='u:object_r:appdat:s0'
IDLE_SOURCE=HERE/'.private/execute-20261025-034802-6bb129/restored-idle-binding.json'
IDLE_SOURCE_SHA='c1697eb76fe710437390236a931044eaf3ae62e2bb7fba5ebb4d6f901769daef'
NOTE=MAIN/'scripts/lab/board_note.sh'
BOARD=MAIN/'.octos/boards/app-lighting.md'
LANE='codex-t136-native-validation'
q=shlex.quote

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def parse_identity(s):
    lines=s.splitlines();procs=[]
    for i,line in enumerate(lines):
        if line.startswith('PROC:'):
            _,pid,parent,uid,name=line.split(':',4)
            rest=lines[i+1].rsplit(')',1)[1].split()
            procs.append(dict(pid=int(pid),parent=int(parent),uid=int(uid),name=name,birth=int(rest[19])))
    return dict(boot=lines[lines.index('BOOT')+1],processes=procs)
def one(identity,name):
    rows=[p for p in identity['processes'] if p['name']==name]
    if len(rows)!=1:raise RuntimeError('non-unique/missing '+name)
    return rows[0]
def same_process(a,b):return all(a[k]==b[k] for k in ('pid','birth','uid'))
def linux_device_pair(dev):
    return (((dev>>8)&0xfff)|((dev>>32)&0xfffff000), (dev&0xff)|((dev>>12)&0xffffff00))

def select_parent(identity):
    roots=[p for p in identity['processes'] if p['name']=='appspawn-x' and p['parent']==1 and p['uid']==0]
    if len(roots)!=1:raise RuntimeError('require exactly one appspawn root PPID1 UID0')
    return roots[0]


def select_main(identity, allow_empty=False):
    named=[p for p in identity['processes'] if p['name']=='com.ss.android.article.news']
    if not named and allow_empty:return None,[]
    parent=select_parent(identity)
    direct=[p for p in named if p['parent']==parent['pid']]
    if len(direct)!=1:raise RuntimeError('require exactly one appspawn direct main child')
    main=direct[0]; bypid={p['pid']:p for p in named}; descendants=[]
    if len(bypid)!=len(named):raise RuntimeError('duplicate PID')
    for item in named:
        if item['uid']!=UID:raise RuntimeError('application UID mismatch')
        if item==main:continue
        chain=[item['pid']]; current=item
        while current['pid']!=main['pid']:
            if current['parent'] not in bypid or current['parent'] in chain:
                raise RuntimeError('same-name process lineage unknown or cyclic')
            current=bypid[current['parent']];chain.append(current['pid'])
        descendants.append({'process':item,'lineage_to_main':chain})
    return main,descendants


class DescendantSetChanged(RuntimeError):
    pass


def core_identity(identity):
    main,_=select_main(identity)
    return {'boot':identity['boot'],'host':one(identity,'org.westlake.imehost'),'parent':select_parent(identity),'main':main}


class Window:
    def __init__(self):
        self.run=HERE/'.private'/('execute-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]);self.run.mkdir()
        self.start=None;self.owner=None;self.n=0;self.recovery=False;self.publish_attempted=False;self.backup=None;self.prepower=None;self.published=None;self.original=None
        self.result={'status':'running','runtime_result':'pending_review','device_commands':0}
        print('RUN '+str(self.run),flush=True)
    def elapsed(self):return time.monotonic()-self.start if self.start is not None else 0
    def call(self,label,argv,allow_failure=False):
        if self.start is not None and self.elapsed()>=(1800 if self.recovery else 900):raise RuntimeError('window deadline')
        binding_deadline=getattr(self,'binding_deadline',None);timeout=15 if binding_deadline is None else min(15,binding_deadline-time.monotonic())
        if timeout<=0:raise RuntimeError('binding20s deadline')
        self.n+=1;d=self.run/(f'{self.n:04d}-'+label);d.mkdir();r=dict(argv=argv,start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),start_monotonic=time.monotonic(),timeout_seconds=timeout)
        save(d/'command.json',r)
        with (d/'stdout').open('wb') as o,(d/'stderr').open('wb') as e:
            try:r['local_rc']=subprocess.run(argv,stdout=o,stderr=e,timeout=timeout).returncode
            except subprocess.TimeoutExpired:r['local_rc']=124
        r.update(end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),end_monotonic=time.monotonic(),stdout_sha256=digest(d/'stdout'),stderr_sha256=digest(d/'stderr'));save(d/'receipt.json',r)
        s=(d/'stdout').read_text(errors='replace');e=(d/'stderr').read_text(errors='replace')
        if argv[0]==HDC:self.result['device_commands']+=1
        if not allow_failure and (r['local_rc']!=0 or e.strip() or any(t in s for t in ('[Fail]','Connect server failed','Permission denied','not found'))):raise RuntimeError('command failed '+d.name)
        return r,s,e
    def shell(self,label,script):
        # Captures remote outcome separately from the transport return code.
        token='T136_REMOTE_'+uuid.uuid4().hex
        command='( '+script+' ); r=$?; echo '+token+':$r'
        r,s,e=self.call(label,[HDC,'-t',SERIAL,'shell',command])
        if not s.rstrip().endswith(token+':0'):raise RuntimeError('remote/body failure '+label)
        return s.rsplit(token+':',1)[0]
    def held(self):
        r,s,e=self.call('held-owned',['bash',str(NOTE),'held',SERIAL],True)
        if r['local_rc']!=0 or e.strip() or s.strip()!=self.owner:raise RuntimeError('self lock lost')
    def identity(self,label):
        s=self.shell(label,"set -e; echo BOOT; cat /proc/sys/kernel/random/boot_id; echo UPTIME; cat /proc/uptime; ps -A -o PID,PPID,UID,NAME | while read p pp uid name; do case \"$name\" in org.westlake.imehost|com.ss.android.article.news|appspawn-x) echo PROC:$p:$pp:$uid:$name; cat /proc/$p/stat;; esac; done")
        return parse_identity(s)
    def object(self,label,path):
        s=self.shell(label,'set -e; stat -L -c '+q('%d|%i|%u|%g|%a|%s|%Y')+' '+q(path)+'; ls -ldZ '+q(path)+'; sha256sum '+q(path))
        lines=s.splitlines();vals=lines[0].split('|');assert len(vals)==7 and lines[1].startswith('-'), 'object must be regular file'
        return dict(dev=int(vals[0]),inode=int(vals[1]),uid=int(vals[2]),gid=int(vals[3]),mode=vals[4],size=int(vals[5]),mtime=int(vals[6]),selinux=next(w for w in lines[1].split() if w.startswith('u:object_r:')),sha256=lines[2].split()[0])
    def bind(self,label,expected):
        previous=getattr(self,'binding_deadline',None);self.binding_deadline=time.monotonic()+20
        try:
            for attempt in range(1,4):
                if time.monotonic()>=self.binding_deadline:raise RuntimeError('binding20s deadline')
                stem=label+'-attempt'+str(attempt)
                try:identity,obj=self._bind_once(stem,expected)
                except DescendantSetChanged:
                    if attempt==3:raise RuntimeError('legal descendant set unstable after3 attempts')
                    continue
                if time.monotonic()>self.binding_deadline:raise RuntimeError('binding20s deadline')
                record=json.loads((self.run/(stem+'-binding.json')).read_text());record['successful_attempt']=attempt
                save(self.run/(label+'-binding.json'),record);return identity,obj
        finally:self.binding_deadline=previous
    def _bind_once(self,label,expected):
        before=self.identity(label+'-identity-before');child,descendants=select_main(before)
        host=one(before,'org.westlake.imehost');parent=select_parent(before)
        assert child['uid']==host['uid']==UID and child['parent']==parent['pid']
        backing=self.object(label+'-backing',TARGET)
        assert backing['sha256']==expected
        if expected==CANDIDATE and self.published is not None:
            assert (backing['dev'],backing['inode'])==(self.published['dev'],self.published['inode']), 'activation object differs from published object'
        objects=[]
        for role,process in [('main',child)]+[('descendant',d['process']) for d in descendants]:
            pid=process['pid'];stem=label+'-'+role+'-'+str(pid)
            # Readable maps required; an empty exact library match is explicitly not_mapped.
            text=self.shell(stem+'-maps',f"set -e; test -r /proc/{pid}/maps; cat /proc/{pid}/maps")
            maps=[line.split() for line in text.splitlines() if 'liboh_adapter_bridge.so' in line]
            if not maps:
                if role=='main':raise RuntimeError('main child baseline not mapped')
                objects.append({'role':role,'process':process,'mapping':'not_mapped'});continue
            assert all(row[-1]==MAPPED and '(deleted)' not in row for row in maps)
            mount=self.shell(stem+'-mount',f"set -e; grep ' /data/local/tmp/asx ' /proc/{pid}/mountinfo; readlink /proc/{pid}/ns/mnt")
            assert str(Path(TARGET).parent).removeprefix('/data') in mount
            obj=self.object(stem+'-process-root',f'/proc/{pid}/root'+MAPPED)
            assert obj==backing and obj['sha256']==expected
            assert (obj['uid'],obj['gid'],obj['mode'],obj['selinux'])==(UID,UID,'644',LABEL)
            assert all(int(row[4])==obj['inode'] and tuple(int(x,16) for x in row[3].split(':'))==linux_device_pair(obj['dev']) for row in maps)
            objects.append({'role':role,'process':process,'mapping':'verified','object':obj})
        after=self.identity(label+'-identity-after')
        if before!=after:
            if core_identity(before)!=core_identity(after):raise RuntimeError('core identity changed during mapping bracket')
            save(self.run/(label+'-descendant-race.json'),{'before':before,'after':after,'reason':'core unchanged; valid descendant collection changed; retry complete binding only'})
            raise DescendantSetChanged('legal descendant collection changed')
        save(self.run/(label+'-binding.json'),{'identity':after,'main_child':child,'same_name_descendants':descendants,'mappings':objects,'object':backing})
        return after,backing
    def admit(self,label):
        before=self.identity(label+'-presence')
        main,descendants=select_main(before,allow_empty=True)
        if main is not None:
            bound,obj=self.bind(label,BASELINE)
            self.result['mapping_now']='strict_current_mapping_verified'
            return bound,obj
        assert digest(IDLE_SOURCE)==IDLE_SOURCE_SHA, 'idle source SHA mismatch'
        source=json.loads(IDLE_SOURCE.read_text())
        assert source['status']=='restored_idle_exact_object' and source['released'] is True and source['mapping_now']=='not_running' and source['baseline_actual_mapping_verified'] is False, 'idle source is not accepted exact-object restoration'
        assert before['boot']==source['identity']['boot'] and re.fullmatch(r'[0-9a-f-]{36}',before['boot'])
        for name in ('org.westlake.imehost','appspawn-x'):
            current=select_parent(before) if name=='appspawn-x' else one(before,name);prior=select_parent(source['identity']) if name=='appspawn-x' else one(source['identity'],name)
            assert current==prior, 'idle host/parent identity changed'
        obj=self.object(label+'-idle-backing',TARGET)
        assert obj==source['object'] and obj['sha256']==BASELINE and (obj['dev'],obj['inode'])==(66352,560578), 'idle backing differs from exact restored object'
        after=self.identity(label+'-idle-identity-after');assert after==before, 'idle identity drift'
        evidence=dict(identity=after,object=obj,mapping_now='not_running',exception='T136-idle-app-same-boot-restored-object',source=IDLE_SOURCE.name,source_run=IDLE_SOURCE.parent.name,source_sha256=IDLE_SOURCE_SHA,source_kind='restored_idle_exact_object',baseline_actual_mapping_verified=False,reason='No child exists; source proves exact original-object restoration with stable roles, not current maps or application health.')
        save(self.run/(label+'-idle-admission.json'),evidence)
        self.result['mapping_now']='not_running';self.result['admission_exception']=evidence['exception'];self.result['idle_source_sha256']=IDLE_SOURCE_SHA
        return after,obj
    def power(self,label):
        s=self.shell(label,"hidumper -s PowerManagerService -a '-a' | grep -E 'ScreenOffTime|Current State'")
        b=re.search(r'ScreenOffTime: Timeout=(\d+)ms',s);v=re.search(r'OverrideTimeout=(\d+)ms',s);state=re.search(r'Current State: (\w+)',s)
        if not b or not state:raise RuntimeError('incomplete base/state')
        return dict(base=int(b.group(1)),override=int(v.group(1)) if v else None,state=state.group(1))
    def keepawake(self,label):
        self.held();p=self.power(label+'-power-read');assert p['base']==self.prepower['base']
        if p['override']!=600000:self.shell(label+'-override','power-shell timeout -o 600000');p=self.power(label+'-power-verify')
        assert p['override']==600000 and p['base']==self.prepower['base']
        if p['state']!='AWAKE':self.shell(label+'-wake','power-shell wakeup');p=self.power(label+'-awake-verify')
        assert p==dict(base=self.prepower['base'],override=600000,state='AWAKE')
    def ui(self,label,command):
        self.held();self.shell(label,'uitest uiInput '+command);self.keepawake(label+'-post-uitest')
    def screen(self,label):
        self.keepawake(label)
        remote='/data/local/tmp/t136-'+self.run.name+'-'+label
        self.shell(label+'-layout','uitest dumpLayout -p '+q(remote+'.json'));self.keepawake(label+'-post-layout')
        self.call(label+'-layout-recv',[HDC,'-t',SERIAL,'file','recv',remote+'.json',str(self.run/(label+'.layout.json'))])
        self.shell(label+'-capture','snapshot_display -f '+q(remote+'.jpeg'))
        self.call(label+'-recv',[HDC,'-t',SERIAL,'file','recv',remote+'.jpeg',str(self.run/(label+'.jpeg'))])
        pic=dict(run=self.run.name,label=label,image_sha256=digest(self.run/(label+'.jpeg')),layout_sha256=digest(self.run/(label+'.layout.json')))
        save(self.run/(label+'.image.json'),pic);print('IMAGE_READY '+json.dumps(dict(pic,path=str(self.run/(label+'.jpeg')))),flush=True);return pic
    def review(self,pic,deadline,wait=True):
        p=self.run/(pic['label']+'.review.json')
        while time.monotonic()<deadline:
            if p.exists():
                try:r=json.loads(p.read_text())
                except ValueError:time.sleep(.2);continue
                if any(r.get(k)!=pic[k] for k in ('run','label','image_sha256','layout_sha256')):raise RuntimeError('review identity mismatch')
                return r
            if not wait:return None
            time.sleep(.2)
        raise RuntimeError('visual review deadline')
    def desktop(self,label,deadline):
        pic=self.screen(label)
        for step in range(4):
            r=self.review(pic,deadline)
            if r['verdict']=='clock_no_credentials':
                xy=r['swipe'];self.coords(xy,4);self.ui(label+'-unlock','swipe '+' '.join(map(str,xy))+' 600');time.sleep(1.5);pic=self.screen(label+'-unlocked')
            elif r['verdict']=='usb_dialog':
                # Review confirms the selected charge-only mode; tap only the fresh confirmation point.
                xy=r['xy'];self.coords(xy,2);self.ui(label+'-usb-confirm','click '+' '.join(map(str,xy)));pic=self.screen(label+'-usb-dismissed')
            elif r['verdict'] in ('host_white','feed'):
                self.ui(label+'-home','keyEvent Home');pic=self.screen(label+'-desktop')
            elif r['verdict']=='desktop':break
            else:raise RuntimeError('no confirmed desktop; unknown/credentials prohibited')
        else:raise RuntimeError('bounded desktop preparation incomplete')
        for page in range(12):
            if time.monotonic()>=deadline:raise RuntimeError('desktop preparation deadline')
            tree=json.loads((self.run/(pic['label']+'.layout.json')).read_text());nodes=[];workspace=[]
            def walk(n,launcher=False,visible=True):
                at=n.get('attributes',{})
                if at.get('bundleName'):launcher=at['bundleName']=='com.ohos.sceneboard'
                visible=visible and at.get('visible') not in (False,'false') and at.get('enabled') not in (False,'false')
                if str(at.get('id','')).startswith('SwiperPage_Grid_WorkSpace') and launcher and visible:workspace.append(at)
                if at.get('id')=='AppIconCommonView_org.westlake.imehost.EntryAbility' and launcher and visible and all(at.get(k)=='true' for k in ('visible','enabled','clickable')):nodes.append(at)
                for c in n.get('children',[]):walk(c,launcher,visible)
            walk(tree);bounds=list(map(int,re.findall(r'\d+',tree['attributes']['bounds'])));assert len(bounds)==4
            if len(nodes)==1:
                v=list(map(int,re.findall(r'\d+',nodes[0]['bounds'])));assert len(v)==4 and bounds[0]<=v[0]<v[2]<=bounds[2] and bounds[1]<=v[1]<v[3]<=bounds[3]
                print('TARGET_READY '+json.dumps(dict(pic,page=page)),flush=True)
                if self.review(pic,deadline)['verdict']!='desktop':raise RuntimeError('target frame not confirmed desktop')
                return [(v[0]+v[2])//2,(v[1]+v[3])//2]
            if len(nodes)>1 or not workspace or page==11:raise RuntimeError('no unique target in12 desktop pages')
            x1,y1,x2,y2=bounds;xy=[x1+(x2-x1)*4//5,(y1+y2)//2,x1+(x2-x1)//5,(y1+y2)//2]
            self.ui(label+'-page-next-'+str(page),'swipe '+' '.join(map(str,xy))+' 600');time.sleep(.5);pic=self.screen(label+'-page-'+str(page+1))
    def coords(self,xy,n):
        assert isinstance(xy,list) and len(xy)==n and all(type(v) is int and 0<=v<=3000 for v in xy)
    def stage(self,name,expected,old=None):
        deadline=min(time.monotonic()+120,self.start+(1700 if self.recovery else 780))
        xy=self.desktop(name+'-before',deadline)
        if not self.recovery and self.elapsed()>750:raise RuntimeError('no complete120s plus cleanup reserve')
        self.ui(name+'-icon','click '+' '.join(map(str,xy)));clicked=time.monotonic();deadline=min(clicked+120,self.start+(1750 if self.recovery else 900));bound=None
        if self.recovery:
            poll=0
            while time.monotonic()<min(clicked+90,deadline):
                poll+=1;ident=self.identity(name+'-early-presence-'+str(poll))
                main,descendants=select_main(ident,allow_empty=True)
                if main is not None:
                    try:bound,obj=self.bind(name+'-early-'+str(poll),expected)
                    except RuntimeError as e:
                        if str(e)!='main child baseline not mapped':raise
                    else:
                        assert bound['boot']!=self.original['boot'], 'recovery reboot must establish new boot'
                        self.screen(name+'-bound');return bound
                time.sleep(1.5)
            raise RuntimeError('no actual baseline mapping within90s early observation')
        for index,offset in enumerate((5,30,60,90)):
            while time.monotonic()<clicked+offset:time.sleep(.2)
            if time.monotonic()>deadline+1:raise RuntimeError('stage deadline')
            ident=self.identity(name+f'-s{offset}-identity')
            main,descendants=select_main(ident,allow_empty=True)
            if main is not None:
                bound,obj=self.bind(name+f'-s{offset}',expected)
                if not self.recovery and bound['boot']==self.original['boot']:raise RuntimeError('software reboot not established')
                if old:
                    if not same_process(select_main(old)[0],select_main(bound)[0]):raise RuntimeError('old child changed; reassociation invalid')
                    if name=='recreated' and same_process(one(old,'org.westlake.imehost'),one(bound,'org.westlake.imehost')):raise RuntimeError('host not recreated')
                    if name=='samehost' and not same_process(one(old,'org.westlake.imehost'),one(bound,'org.westlake.imehost')):raise RuntimeError('same host changed')
            pic=self.screen(name+f'-s{offset}');next_at=min(deadline,clicked+((30,60,90,120)[index]))
            if self.recovery and bound:return bound
            while time.monotonic()<next_at:
                r=self.review(pic,next_at,False)
                if r:
                    if r['verdict']!='feed':break
                    if bound is None:raise RuntimeError('feed without mapped candidate')
                    kind=r.get('touch_kind');coords=r.get('touch_coordinates');self.coords(coords,2 if kind=='click' else 4)
                    if kind not in ('click','swipe'):raise RuntimeError('missing ordinary content verification')
                    if time.monotonic()+60>self.start+900:raise RuntimeError('insufficient60s content review before recovery reserve')
                    self.ui(name+'-content',kind+' '+' '.join(map(str,coords))+(' 600' if kind=='swipe' else ''))
                    after=self.screen(name+'-content-after');verified=self.review(after,min(time.monotonic()+60,self.start+900))
                    if verified['verdict']!='usable':raise RuntimeError('content not confirmed usable')
                    after_identity=self.identity(name+'-content-after-identity')
                    if core_identity(after_identity)!=core_identity(bound):raise RuntimeError('core identity changed after content interaction')
                    return after_identity
                time.sleep(2)
        raise RuntimeError('no confirmed usable feed by120s')
    def reboot(self,label):
        self.held();old=self.identity(label+'-before')['boot']
        self.call(label,[HDC,'-t',SERIAL,'target','boot'])
        # Reuse demo_seal_61b.py wait_boot: new UUID plus exact boot.completed=true.
        # Additionally require complete power fields and a successful parseable UITest dump.
        deadline=time.monotonic()+120
        while time.monotonic()<deadline-15:
            time.sleep(2)
            r,s,e=self.call(label+'-boot-completion-poll',[HDC,'-t',SERIAL,'shell','cat /proc/sys/kernel/random/boot_id; param get bootevent.boot.completed'],True)
            lines=s.strip().splitlines()
            if r['local_rc']!=0 or e.strip() or len(lines)!=2 or not re.fullmatch(r'[0-9a-f-]{36}',lines[0]) or lines[0]==old or lines[1]!='true':continue
            new_boot=lines[0]
            if time.monotonic()>=deadline-15:break
            pr,ps,pe=self.call(label+'-power-service-poll',[HDC,'-t',SERIAL,'shell',"hidumper -s PowerManagerService -a '-a' | grep -E 'ScreenOffTime|Current State'"],True)
            if pr['local_rc']!=0 or pe.strip() or not re.search(r'Current State: \w+',ps) or not re.search(r'ScreenOffTime: Timeout=\d+ms',ps):continue
            if time.monotonic()>=deadline-15:break
            self.keepawake(label+'-boot-ui')
            remote='/data/local/tmp/t136-'+self.run.name+'-'+label+'-ready-'+str(self.n)+'.json'
            ur,us,ue=self.call(label+'-layout-readiness',[HDC,'-t',SERIAL,'shell','uitest dumpLayout -p '+q(remote)+'; r=$?; echo T136_UI_RC:$r'],True)
            if ur['local_rc']!=0 or ue.strip() or not us.rstrip().endswith('T136_UI_RC:0'):continue
            if time.monotonic()>=deadline-15:break
            local=self.run/(label+'-ready-'+str(self.n)+'.json')
            fr,fs,fe=self.call(label+'-layout-recv',[HDC,'-t',SERIAL,'file','recv',remote,str(local)],True)
            if fr['local_rc']!=0 or fe.strip() or '[Fail]' in fs or not local.is_file():continue
            try:tree=json.loads(local.read_text())
            except (OSError,ValueError):continue
            if isinstance(tree,dict) and tree:return new_boot
        raise RuntimeError('newboot/boot.completed/power/parseable layout not ready within120s')
    def run_window(self):
        r,s,e=self.call('held-before',['bash',str(NOTE),'held',SERIAL],True);assert r['local_rc']==1 and not s.strip() and not e.strip()
        self.call('frozen',['python3',str(MAIN/'scripts/lab/check_frozen.py'),'--git',str(MAIN)])
        self.original,obj=self.admit('fresh');self.system_pre=self.object('system-before',SYSTEM);assert self.system_pre['sha256']==SYSTEM_SHA
        self.prepower=self.power('power-before');assert self.prepower['override'] is not None
        self.start=time.monotonic()
        try:
            self.call('lock',['bash',str(NOTE),'lock',str(BOARD),SERIAL,LANE,'T136 candidate ordinary validation unconditional rollback max1800s'])
            r,s,e=self.call('held-acquired',['bash',str(NOTE),'held',SERIAL]);self.owner=s.strip();assert self.owner.startswith(LANE+' ')
            self.held();again,original=self.admit('locked-fresh');assert again==self.original and original==obj
            self.backup=TARGET+'.'+self.run.name+'.baseline';temp=TARGET+'.'+self.run.name+'.candidate'
            self.shell('backup','set -e; test ! -e '+q(self.backup)+'; test ! -e '+q(temp)+'; ln '+q(TARGET)+' '+q(self.backup))
            assert self.object('backup-verify',self.backup)==obj
            self.call('preimage-recv',[HDC,'-t',SERIAL,'file','recv',self.backup,str(self.run/'baseline.so')]);assert digest(self.run/'baseline.so')==BASELINE
            self.call('candidate-send',[HDC,'-t',SERIAL,'file','send',str(INPUT/'candidate.so'),temp])
            self.shell('preserve-metadata',f'set -e; chown {UID}:{UID} '+q(temp)+'; chmod 0644 '+q(temp)+'; chcon '+q(LABEL)+' '+q(temp))
            staged=self.object('staged',temp);assert staged['sha256']==CANDIDATE and staged['dev']==obj['dev'] and (staged['uid'],staged['gid'],staged['mode'],staged['selinux'])==(UID,UID,'644',LABEL)
            self.held();self.publish_attempted=True;self.shell('atomic-publish','set -e; mv '+q(temp)+' '+q(TARGET));self.published=self.object('published',TARGET);assert self.published==staged
            self.reboot('candidate-reboot')
            first=self.stage('firstopen',CANDIDATE);same=self.stage('samehost',CANDIDATE,first)
            self.ui('recent','keyEvent 10011');pic=self.screen('recent-target');r=self.review(pic,min(time.monotonic()+120,self.start+780))
            if r['verdict']!='recent_host_card':raise RuntimeError('own recent card not confirmed')
            self.coords(r['swipe'],4);self.ui('recent-close','swipe '+' '.join(map(str,r['swipe']))+' 600')
            self.ui('recent-to-desktop','keyEvent Home')
            self.stage('recreated',CANDIDATE,same);self.result['runtime_result']='three_stages_outer_reviewed_usable_pending_independent_review'
        except BaseException as e:self.result.update(status='experiment_stopped',error=str(e));print('STOP '+str(e),flush=True)
        finally:
            self.recovery=True;self.result['rollback_started_elapsed']=self.elapsed()
            try:
                self.held()
                if self.publish_attempted:
                    current=self.object('rollback-current',TARGET)
                    if current['sha256'] not in (BASELINE,CANDIDATE):raise RuntimeError('unknown published object; recovery_required')
                    assert self.object('rollback-backup',self.backup)==obj
                    self.shell('atomic-rollback','set -e; mv '+q(self.backup)+' '+q(TARGET));assert self.object('rollback-disk',TARGET)==obj
                    self.reboot('rollback-reboot');restored=self.stage('baseline-restored',BASELINE);self.result['baseline_actual_mapping_verified']=True
                assert self.object('system-after',SYSTEM)==self.system_pre
                self.screen('final')
                self.result['rollback']='verified'
            except BaseException as e:self.result['recovery_error']=str(e);self.result['rollback']='recovery_required'
            finally:
                try:
                    self.held();self.shell('power-restore','power-shell timeout -o '+str(self.prepower['override']));post=self.power('power-final');assert all(post[k]==self.prepower[k] for k in ('base','override'));self.result['power_restored']=True
                    if self.result.get('rollback')=='verified':
                        self.call('unlock',['bash',str(NOTE),'unlock',str(BOARD),SERIAL,LANE]);r,s,e=self.call('final-held',['bash',str(NOTE),'held',SERIAL],True);self.result['released']=r['local_rc']==1 and not s.strip() and not e.strip()
                except BaseException as e:self.result['cleanup_error']=str(e)
                self.result['elapsed_seconds']=self.elapsed();save(self.run/'result.json',self.result);print('DONE '+json.dumps(self.result),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--outer-receipt',type=Path,required=True);a=ap.parse_args()
    plan=json.loads((HERE/'steps_v9.json').read_text());receipt=json.loads(a.outer_receipt.read_text())
    assert receipt.get('decision')=='approve_execution' and receipt.get('serial')==SERIAL
    assert receipt.get('entry_sha256')==digest(Path(__file__)) and receipt.get('steps_sha256')==digest(HERE/'steps_v9.json')
    assert receipt.get('candidate_sha256')==CANDIDATE and receipt.get('rollback_sha256')==BASELINE
    assert receipt.get('idle_source_sha256')==IDLE_SOURCE_SHA and digest(IDLE_SOURCE)==IDLE_SOURCE_SHA
    for name,expected in [('candidate.so',CANDIDATE),('rollback.so',BASELINE)]:assert digest(INPUT/name)==expected
    used=HERE/'.private'/('used-outer-receipt-'+digest(a.outer_receipt)+'.json');save(used,{'outer_receipt_sha256':digest(a.outer_receipt)})
    w=Window();save(w.run/'outer-receipt.json',receipt);w.run_window()
if __name__=='__main__':main()
