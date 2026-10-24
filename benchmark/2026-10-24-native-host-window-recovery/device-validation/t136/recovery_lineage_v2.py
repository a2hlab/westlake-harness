"""Recovery-only PPID selection; retain full identity and same-name descendants."""
from pathlib import Path
import execute_v6 as m


def select_main(identity):
    parent=m.one(identity,'appspawn-x')
    named=[p for p in identity['processes'] if p['name']=='com.ss.android.article.news']
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


class RecoveryWindow(m.Window):
    def bind(self,label,expected):
        before=self.identity(label+'-identity-before');child,descendants=select_main(before)
        host=m.one(before,'org.westlake.imehost');parent=m.one(before,'appspawn-x')
        assert child['uid']==host['uid']==m.UID and child['parent']==parent['pid']
        backing=self.object(label+'-backing',m.TARGET)
        assert backing['sha256']==expected
        objects=[]
        for role,process in [('main',child)]+[('descendant',d['process']) for d in descendants]:
            pid=process['pid'];stem=label+'-'+role+'-'+str(pid)
            # Readable maps required; an empty exact library match is explicitly not_mapped.
            text=self.shell(stem+'-maps',f"set -e; test -r /proc/{pid}/maps; map_rc=0; grep 'liboh_adapter_bridge[.]so' /proc/{pid}/maps || map_rc=$?; test \"$map_rc\" -le 1")
            maps=[line.split() for line in text.splitlines() if line.strip()]
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
        after=self.identity(label+'-identity-after');assert before==after,'full process identity changed during mapping bracket'
        m.save(self.run/(label+'-binding.json'),{'identity':after,'main_child':child,'same_name_descendants':descendants,'mappings':objects,'object':backing})
        return after,backing
