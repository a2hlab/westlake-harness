"""Recovery-only PPID selection; retain full identity and same-name descendants."""
from pathlib import Path
import execute_v6 as m


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
        if item['uid']!=m.UID:raise RuntimeError('application UID mismatch')
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
    return {'boot':identity['boot'],'host':m.one(identity,'org.westlake.imehost'),'parent':select_parent(identity),'main':main}


class RecoveryWindow(m.Window):
    def call(self,label,argv,allow_failure=False):
        deadline=getattr(self,'binding_deadline',None)
        if deadline is None:return super().call(label,argv,allow_failure)
        timeout=min(15,deadline-m.time.monotonic())
        if timeout<=0:raise RuntimeError('binding20s deadline')
        if self.elapsed()>=(1800 if self.recovery else 900):raise RuntimeError('window deadline')
        self.n+=1;d=self.run/(f'{self.n:04d}-'+label);d.mkdir()
        r=dict(argv=argv,start_utc=m.datetime.datetime.now(m.datetime.timezone.utc).isoformat(),start_monotonic=m.time.monotonic(),timeout_seconds=timeout)
        m.save(d/'command.json',r)
        with (d/'stdout').open('wb') as o,(d/'stderr').open('wb') as e:
            try:r['local_rc']=m.subprocess.run(argv,stdout=o,stderr=e,timeout=timeout).returncode
            except m.subprocess.TimeoutExpired:r['local_rc']=124
        r.update(end_utc=m.datetime.datetime.now(m.datetime.timezone.utc).isoformat(),end_monotonic=m.time.monotonic(),stdout_sha256=m.digest(d/'stdout'),stderr_sha256=m.digest(d/'stderr'));m.save(d/'receipt.json',r)
        out=(d/'stdout').read_text(errors='replace');err=(d/'stderr').read_text(errors='replace')
        if argv[0]==m.HDC:self.result['device_commands']+=1
        if not allow_failure and (r['local_rc']!=0 or err.strip() or any(t in out for t in ('[Fail]','Connect server failed','Permission denied','not found'))):raise RuntimeError('command failed '+d.name)
        return r,out,err
    def bind(self,label,expected):
        previous=getattr(self,'binding_deadline',None);self.binding_deadline=m.time.monotonic()+20
        try:
            for attempt in range(1,4):
                if m.time.monotonic()>=self.binding_deadline:raise RuntimeError('binding20s deadline')
                stem=label+'-attempt'+str(attempt)
                try:identity,obj=self._bind_once(stem,expected)
                except DescendantSetChanged:
                    if attempt==3:raise RuntimeError('legal descendant set unstable after3 attempts')
                    continue
                record=m.json.loads((self.run/(stem+'-binding.json')).read_text());record['successful_attempt']=attempt
                m.save(self.run/(label+'-binding.json'),record);return identity,obj
        finally:self.binding_deadline=previous
    def _bind_once(self,label,expected):
        before=self.identity(label+'-identity-before');child,descendants=select_main(before)
        host=m.one(before,'org.westlake.imehost');parent=select_parent(before)
        assert child['uid']==host['uid']==m.UID and child['parent']==parent['pid']
        backing=self.object(label+'-backing',m.TARGET)
        assert backing['sha256']==expected
        objects=[]
        for role,process in [('main',child)]+[('descendant',d['process']) for d in descendants]:
            pid=process['pid'];stem=label+'-'+role+'-'+str(pid)
            # Readable maps required; an empty exact library match is explicitly not_mapped.
            text=self.shell(stem+'-maps',f"set -e; test -r /proc/{pid}/maps; cat /proc/{pid}/maps")
            maps=[line.split() for line in text.splitlines() if 'liboh_adapter_bridge.so' in line]
            if not maps:
                if role=='main':raise RuntimeError('main child baseline not mapped')
                objects.append({'role':role,'process':process,'mapping':'not_mapped'});continue
            assert all(row[-1]==m.MAPPED and '(deleted)' not in row for row in maps)
            mount=self.shell(stem+'-mount',f"set -e; grep ' /data/local/tmp/asx ' /proc/{pid}/mountinfo; readlink /proc/{pid}/ns/mnt")
            assert str(Path(m.TARGET).parent).removeprefix('/data') in mount
            obj=self.object(stem+'-process-root',f'/proc/{pid}/root'+m.MAPPED)
            assert obj==backing and obj['sha256']==expected
            assert (obj['uid'],obj['gid'],obj['mode'],obj['selinux'])==(m.UID,m.UID,'644',m.LABEL)
            assert all(int(row[4])==obj['inode'] and tuple(int(x,16) for x in row[3].split(':'))==m.linux_device_pair(obj['dev']) for row in maps)
            objects.append({'role':role,'process':process,'mapping':'verified','object':obj})
        after=self.identity(label+'-identity-after')
        if before!=after:
            if core_identity(before)!=core_identity(after):raise RuntimeError('core identity changed during mapping bracket')
            m.save(self.run/(label+'-descendant-race.json'),{'before':before,'after':after,'reason':'core unchanged; valid descendant collection changed; retry complete binding only'})
            raise DescendantSetChanged('legal descendant collection changed')
        m.save(self.run/(label+'-binding.json'),{'identity':after,'main_child':child,'same_name_descendants':descendants,'mappings':objects,'object':backing})
        return after,backing
