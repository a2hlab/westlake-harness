#!/usr/bin/env python3
"""Compare sampled child identities, scoped by the UID from each reinstall receipt."""
import argparse,gzip,json
from pathlib import Path
H=Path(__file__).resolve().parent;SERIAL='61b0657200000000000000000324012c'
LIBS=['liboh_adapter_bridge.so','liboh_android_runtime.so','libappexecfwk_base.z.so','liblog.so','libbionic_compat.so']
def collect(run,key,phase):
 record=H/'runs'/run/SERIAL/key/'record.json'
 if not record.exists():return {'status':'unknown','reason':'record absent'}
 d=json.loads(record.read_text());uid=d.get('bms',{}).get('uid');pids=set(d.get('observed_pids',[]));samples=[]
 path=H/('maps-observations.jsonl' if phase=='n7' else 'maps-observations-'+phase+'.jsonl')
 if not path.exists():return {'status':'unknown','reason':'maps absent'}
 for line in path.read_text().splitlines():
  obs=json.loads(line);raw=gzip.decompress((H/obs['file']).read_bytes()).decode(errors='replace')
  seen={int(f[0]) for l in raw.split('MAPS_BEGIN:')[0].splitlines() if len(f:=l.split())>=4 and f[0].isdigit() and f[2].isdigit() and int(f[2])==uid}
  for proc in obs['processes']:
   if proc['pid'] in seen|pids:
    paths={lib:sorted({l.split()[-1] for l in raw.split('MAPS_BEGIN:'+str(proc['pid'])+'\n')[-1].split('MAPS_END:')[0].splitlines() if l.split() and Path(l.split()[-1]).name==lib}) for lib in LIBS}
    samples.append({'file':obs['file'],'time':obs['time'],'pid':proc['pid'],'libraries':proc['libraries'],'paths':paths})
 counts={lib:max([len(s['libraries'][lib]) for s in samples] or [0]) for lib in LIBS}
 return {'status':'observed' if samples else 'unknown','uid':uid,'counts':counts,'samples':samples}
def compare(key,run):
 old=collect('n7-u5-baseline',key,'u5')
 if old['status']!='observed':
  old=collect('n7-u5-localsend','localsend','u5');old['representative_key']='localsend';old['scope']='same-board same-window U5 representative, per outer 04:30'
 new=collect(run,key,'n7');added=[]
 if old['status']=='observed' and new['status']=='observed':
  added=[lib for lib in LIBS if new['counts'][lib]>max(1,old['counts'][lib])]
  status='fail' if added else 'no_added_duplicate_in_samples'
 else: status='unknown'
 out=dict(key=key,status=status,added=added,baseline=old,candidate=new,constructor_once='unknown')
 (H/('maps-compare-'+key+'.json')).write_text(json.dumps(out,indent=2)+'\n')
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('key');p.add_argument('run');a=p.parse_args();d=compare(a.key,a.run);print(json.dumps({k:v for k,v in d.items() if k not in ['baseline','candidate']}));raise SystemExit(1 if d['status'] in ['fail','unknown'] else 0)
