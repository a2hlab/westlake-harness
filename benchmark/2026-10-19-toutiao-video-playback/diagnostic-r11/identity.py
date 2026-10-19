"""Serial-qualified, read-only bookended identity collection. Executed by outer only."""
import json, shlex, subprocess, time
from pathlib import Path
from core import need, path, sha, SERIAL, SERVER_SHA, stat_fields, parse_maps, mapped_module
class Guard:
    def __init__(self,admission,out,deadline):self.a=admission;self.out=Path(out);self.deadline=deadline;self.n=0;self.initial_maps=None
    def capture(self,phase,after=False):
        a=self.a;e=a['identity'];server=a['server'];self.n+=1
        dest=self.out/('identity-%03d-%s'%(self.n,phase));dest.mkdir()
        # No lock mutation: this command reads the existing owner line only.
        held=subprocess.run(['bash',str(path(a['lock_script']['path'])),'held',SERIAL],capture_output=True,timeout=5)
        (dest/'held.stdout.txt').write_bytes(held.stdout);(dest/'held.stderr.txt').write_bytes(held.stderr)
        if not after:need(held.returncode==0 and held.stdout.decode().strip()==a['holder'],'lock owner changed')
        chunks=['set -eu']
        def section(name,cmd):chunks.extend(["printf '%s\\n' "+shlex.quote('R11_'+name),cmd])
        section('BOOT','cat /proc/sys/kernel/random/boot_id')
        processes=[('PARENT',e['parent']),('CHILD',e['child'])]+([] if after else [('SERVER',server['pid'])])
        for name,pid in processes:
            section(name+'_STAT','cat /proc/%d/stat'%pid)
            section(name+'_STATUS','cat /proc/%d/status'%pid)
        if not after:section('SERVER_SHA','sha256sum /proc/%d/exe'%server['pid'])
        section('PARENT_EXE','sha256sum /proc/%d/exe'%e['parent'])
        section('CHILD_EXE','sha256sum /proc/%d/exe'%e['child'])
        section('MAPS','cat /proc/%d/maps'%e['child'])
        for role,m in sorted(a['modules'].items()):
            target=shlex.quote('/proc/%d/root%s'%(e['child'],m['remote_path']))
            section('SHA_'+role,'sha256sum '+target)
            section('INODE_'+role,"stat -L -c '%d:%i' "+target)
        for name,pid in processes:section(name+'_END','cat /proc/%d/stat'%pid)
        section('BOOT_END','cat /proc/sys/kernel/random/boot_id')
        chunks.append("printf '%s\\n' 'R11_REMOTE_RC=0'")
        cmd='; '.join(chunks)
        argv=[str(path(a['hdc']['path'])),'-t',SERIAL,'shell',cmd]
        (dest/'command.json').write_text(json.dumps({'argv':argv,'phase':phase})+'\n')
        timeout=10 if after else min(10,max(.1,self.deadline-time.monotonic()))
        try:p=subprocess.run(argv,capture_output=True,timeout=timeout)
        except subprocess.TimeoutExpired as ex:
            (dest/'stdout.txt').write_bytes(ex.stdout or b'');(dest/'stderr.txt').write_bytes(ex.stderr or b'');(dest/'rc.json').write_text('{"timeout":true}\n');raise
        (dest/'stdout.txt').write_bytes(p.stdout);(dest/'stderr.txt').write_bytes(p.stderr);(dest/'rc.json').write_text(json.dumps({'rc':p.returncode})+'\n')
        text=p.stdout.decode('utf-8','strict');need(p.returncode==0 and text.splitlines()[-1]=='R11_REMOTE_RC=0','remote rc absent/nonzero')
        parts={};key=None
        for line in text.splitlines()[:-1]:
            if line.startswith('R11_'):
                key=line[4:];need(key not in parts,'duplicate identity section');parts[key]=[]
            else:
                need(key is not None,'unexpected remote preamble');parts[key].append(line)
        one=lambda k:'\n'.join(parts[k])
        need(one('BOOT')==e['boot']==one('BOOT_END'),'boot drift')
        def status(k):
            fields={x.split(':',1)[0]:x.split(':',1)[1].strip() for x in parts[k] if ':' in x}
            return fields
        for name,pid,birth,uid in [('PARENT',e['parent'],e['parent_birth'],e['parent_uid']),('CHILD',e['child'],e['child_birth'],e['uid']),* ([] if after else [('SERVER',server['pid'],server['birth'],server['uid'])])]:
            s=stat_fields(one(name+'_STAT'));t=stat_fields(one(name+'_END'))
            need((s['pid'],s['birth'])==(pid,birth)==(t['pid'],t['birth']),'birth/PID '+name)
            need(s['state'] not in ('Z','X') and t['state'] not in ('Z','X'),'dead '+name)
            st=status(name+'_STATUS');need([int(v) for v in st['Uid'].split()]==[uid]*4,'UID '+name)
            if name=='CHILD':need(s['ppid']==e['parent']==t['ppid'],'child PPID')
        tracer=int(status('CHILD_STATUS')['TracerPid']);need(tracer==(0 if after else server['pid']),'wrong tracer for phase')
        if after:need(tracer==0 and stat_fields(one('CHILD_END'))['state'] not in ('T','t'),'still traced/stopped')
        if not after:need(one('SERVER_SHA').split()[0]==SERVER_SHA,'server bytes')
        need(one('PARENT_EXE').split()[0]==e['parent_exe_sha256'],'parent exe drift')
        need(one('CHILD_EXE').split()[0]==e['child_exe_sha256'],'child exe drift')
        rows=parse_maps(one('MAPS'))
        for role,m in a['modules'].items():
            need(one('SHA_'+role).split()[0]==m['sha256'],'actual module SHA '+role)
            need(tuple(int(v) for v in one('INODE_'+role).split(':'))==(m['device'],m['inode']),'actual private inode '+role)
            mapped_module(rows,m)
        selected=sorted(r['raw'] for r in rows if r['path'] in {m['remote_path'] for m in a['modules'].values()})
        if self.initial_maps is None:self.initial_maps=selected
        else:need(selected==self.initial_maps,'mapped instance drift')
        result={'phase':phase,'boot':e['boot'],'child':e['child'],'child_birth':e['child_birth'],'parent':e['parent'],'parent_birth':e['parent_birth'],'tracer_pid':tracer,'state':stat_fields(one('CHILD_END'))['state'],'rows':rows,'lock_matches':held.returncode==0 and held.stdout.decode().strip()==a['holder']}
        (dest/'verified.json').write_text(json.dumps(result,indent=2)+'\n');return result
