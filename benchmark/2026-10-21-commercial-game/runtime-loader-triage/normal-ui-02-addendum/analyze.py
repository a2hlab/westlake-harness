#!/usr/bin/env python3
"""Offline receipt reconciliation; no device/environment/process reads."""
import argparse,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent
PINS={'libapp_native_loader.so':'eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c','libnativeloader.so':'b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stat(text):
 m=re.fullmatch(r'(\d+) \((.*)\) ([A-Za-z]) (.*)\n?',text.strip());
 if not m:return None
 t=m[4].split()
 try:return {'pid':int(m[1]),'comm':m[2],'state':m[3],'ppid':int(t[0]),'birth':int(t[18])}
 except (ValueError,IndexError):return None
def identity(s):return None if s is None else (s['pid'],s['ppid'],s['birth'])
def dev(d):return ((d>>8)&0xfff)|((d>>32)&0xfffff000),(d&0xff)|((d>>12)&0xffffff00)
def object_record(text):
 m=re.fullmatch(r'(\d+):(\d+) (\d+)\n([a-f0-9]{64})  (/proc/10946/root/[^\n]+)\n?',text)
 if not m:return None
 return {'device_decimal':int(m[1]),'device_major_minor':list(dev(int(m[1]))),'inode':int(m[2]),'bytes':int(m[3]),'sha256':m[4],'path':m[5].removeprefix('/proc/10946/root')}
def map_rows(text):
 rows=[]
 for n,line in enumerate(text.splitlines(),1):
  t=line.split(maxsplit=5)
  if len(t)!=6 or Path(t[5]).name not in PINS:continue
  begin,end=t[0].split('-');major,minor=t[3].split(':')
  rows.append({'line':n,'text':line,'path':t[5],'range':[begin,end],'offset':t[2],'device_major_minor':[int(major,16),int(minor,16)],'inode':int(t[4])})
 return rows
def analyze(p):
 commands=json.loads((p/'commands.json').read_text());cm={x['name']:x for x in commands};order={x['name']:i for i,x in enumerate(commands)};rounds=[]
 for i in range(3):
  before=stat((p/f'{i}-stat-before.stdout').read_text());after=stat((p/f'{i}-stat-after.stdout').read_text());maps=map_rows((p/f'{i}-maps.stdout').read_text());valid=identity(before)==identity(after)==(10946,6274,598912) and before['state'] not in 'ZX' and after['state'] not in 'ZX'
  assert order[f'{i}-stat-before']<order[f'{i}-maps']<order[f'{i}-stat-after']
  objects=[]
  for f in sorted(p.glob(f'{i}-object-*.stdout')):
   tag=f.stem;r=object_record(f.read_text());matched=False
   if r:
    hits=[m for m in maps if m['path']==r['path']];matched=bool(hits) and all(m['device_major_minor']==r['device_major_minor'] and m['inode']==r['inode'] for m in hits) and r['sha256']==PINS[Path(r['path']).name]
   following=stat((p/f'{i+1}-stat-before.stdout').read_text()) if i<2 else None
   bracket=identity(following)==identity(before)==(10946,6274,598912) and order[f'{i}-stat-after']<order[tag]<order[f'{i+1}-stat-before'] if i<2 else False
   objects.append({'file':f.name,'transport_rc':cm[tag]['rc'],'parsed':r,'matches_maps_dev_inode_and_known_SHA':matched,'later_stat_identity_bracket':bracket,'accepted':bool(valid and matched and bracket and cm[tag]['rc']==0),'limitation':'stat then path hash, not atomic mapped-memory hash; later next-round stat brackets object collection, not same-round stat-after'})
  rounds.append({'round':i,'before':before,'after':after,'maps_identity_bracket':bool(valid),'maps_rows':maps,'objects':objects,'verdict':'ACCEPT_POINT_IN_TIME_IDENTITY' if valid and all(x['accepted'] for x in objects) else 'INCOMPLETE_REJECT_IDENTITY_AND_OBJECT_CLOSURE'})
 return {'pid':10946,'ppid':6274,'birth':598912,'rounds':rounds,'loader_entry_winner':'UNKNOWN','namespace_owner_per_mapping':'UNKNOWN','same_bytes_not_same_instance':True,'device_calls':0,'claim':'Round1 maps contains two inode-distinct file mappings per loader; no function-pointer, relocation winner or namespace membership evidence.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--write',action='store_true',required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 data=analyze(a.input);(a.out/'results.json').write_text(json.dumps(data,indent=2)+'\n');provenance=[]
 names=['commands.json','child-hilog.json','final-boot.stdout']+[f'{i}-stat-{phase}.stdout' for i in range(3) for phase in ['before','after']]+[f.name for f in a.input.glob('*-object-*.stdout')]
 for name in names:
  p=a.input/name;target=a.out/'evidence'/(name+'.txt' if name.endswith('.stdout') else name);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes());provenance.append({'raw_alias':'$COMMERCIAL_PRIVATE/normal-ui-02/attempt2/'+name,'sha256':sha(p),'bytes':p.stat().st_size,'public':str(target.relative_to(a.out)),'exact_copy':True})
 for i in range(3):
  p=a.input/f'{i}-maps.stdout';rows=data['rounds'][i]['maps_rows'];target=a.out/'evidence'/f'{i}-maps-excerpt.txt';target.write_text(''.join(f"{x['line']}: {x['text']}\n" for x in rows));provenance.append({'raw_alias':'$COMMERCIAL_PRIVATE/normal-ui-02/attempt2/'+p.name,'sha256':sha(p),'bytes':p.stat().st_size,'public':str(target.relative_to(a.out)),'original_lines':[x['line'] for x in rows]})
 p=a.input/'child-hilog.stdout';lines=p.read_text().splitlines();selected=[433,3181,3318,3380,3381,3406,3407,3521,3522,3523,3524,3525,3526,3928,3979];target=a.out/'evidence/child-hilog-excerpt.txt';target.write_text(''.join(f'{n}: {lines[n-1]}\n' for n in selected));provenance.append({'raw_alias':'$COMMERCIAL_PRIVATE/normal-ui-02/attempt2/'+p.name,'sha256':sha(p),'bytes':p.stat().st_size,'public':str(target.relative_to(a.out)),'original_lines':selected})
 for r in provenance:r['public_sha256']=sha(a.out/r['public'])
 (a.out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n');print(json.dumps({'round_verdicts':[r['verdict'] for r in data['rounds']],'winner':data['loader_entry_winner']}))
if __name__=='__main__':main()
