"""Target-process registration attempts and explicit JNI ULEs; no board access."""
import collections,gzip,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
MASTER=Path('/Users/zhaoyue/orca/workspaces/westlake-harness')
ROOTS=[MASTER/'benchmark/2026-09-30-r16-sweep/runs',MASTER/'benchmark/2026-09-30-r17a-sweep/runs']
REG=re.compile(r'OH_RegHook:\s+([\w.$/]+)::([\w$<>]+)(\([^\s]*\)\S+) -> fn=(\S+) \(lib=(\S+) pageOff=')
MISS=re.compile(r'No implementation found for ([\w.$\[\]/]+) ([\w.$/]+)\.([\w$<>]+)\(([^)]*)\)')
PID=re.compile(r'^\d\d-\d\d \S+\s+(\d+)\s+\d+\s+')
def descriptor(name):
    name=name.strip();array=''
    while name.endswith('[]'):array+='[';name=name[:-2]
    return array+dict(void='V',boolean='Z',byte='B',char='C',short='S',int='I',long='J',float='F',double='D').get(name,'L'+name.replace('.','/')+';')
def missing_id(line):
    m=MISS.search(line)
    if not m:return None
    ret,owner,name,args=m.groups()
    return owner.replace('.','/')+'.'+name+'('+''.join(descriptor(a) for a in args.split(',') if a.strip())+')'+descriptor(ret)
def registration_id(line):
    m=REG.search(line)
    if not m:return None
    owner,name,sig,fn,lib=m.groups()
    return owner.replace('.','/')+'.'+name+sig,lib,fn

def main():
    attempts=collections.defaultdict(list);missing=collections.defaultdict(list);inputs=[];coverage=[]
    for root in ROOTS:
      for path in sorted(root.rglob('hilog.txt')):
        rp=path.parent/'record.json'
        if not rp.is_file():continue
        record=json.loads(rp.read_text());pkg=record.get('package');data=path.read_bytes();lines=data.decode(errors='replace').splitlines()
        pids={int(m[1]) for line in lines if pkg and ('resolved ApplicationInfo pkg='+pkg+' ') in line and (m:=PID.match(line))}
        coverage.append({'path':str(path),'key':record['key'],'serial':record['serial'],'boot_id':record.get('boot_id'),'target_pids':sorted(pids),'status':'target_identified' if pids else 'unknown_target'})
        inputs.append({'path':str(path),'sha256':hashlib.sha256(data).hexdigest(),'record_sha256':hashlib.sha256(rp.read_bytes()).hexdigest()})
        seen_reg=set();seen_miss=set()
        for n,line in enumerate(lines,1):
          m=PID.match(line)
          if not m or int(m[1]) not in pids:continue
          ev={'path':str(path),'line':n,'key':record['key'],'serial':record['serial'],'boot_id':record.get('boot_id'),'pid':int(m[1]),'run':str(path.relative_to(root).parts[0]),'text':line}
          reg=registration_id(line)
          if reg and reg[0] not in seen_reg:
            seen_reg.add(reg[0]);attempts[reg[0]].append({**ev,'library':reg[1],'function_address':reg[2],'strength':'pre-call_registration_attempt'})
          mid=missing_id(line)
          if mid and mid not in seen_miss:seen_miss.add(mid);missing[mid].append(ev)
        print(root.parent.name,record['key'],'pids',pids,'registered-attempt',len(seen_reg),'missing',len(seen_miss),flush=True)
    result={'inputs':inputs,'coverage':coverage,'attempts':attempts,'missing':missing,'semantics':'OH_RegHook logs before g_orig_register_natives; presence is not a success receipt. Missing is explicit ULE in identified target process, scoped to the run.'}
    with gzip.open(HERE/'evidence/observations.json.gz','wt') as f:json.dump(result,f)
    print('unique attempts',len(attempts),'unique explicit missing',len(missing),flush=True)
if __name__=='__main__':main()
