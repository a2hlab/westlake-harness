from pathlib import Path
import json,re,statistics
R=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/speed-delivery50'
reviews=json.loads(Path(__file__).with_name('visual-review.json').read_text())
rows=[]
for r in sorted(R.glob('*-r*')):
 if not (r/'instance.json').exists():continue
 d=json.loads((r/'instance.json').read_text());s=(r/'child.stderr').read_text(errors='replace') if (r/'child.stderr').exists() else ''
 row={'trial':r.name,**d};row.pop('host_start',None)
 inp=r/'input.txt';start=float(inp.read_text().split()[0]) if inp.exists() else None;row['click_uptime']=start
 if start is not None:
  ent=re.search(r'^\[B47-SLA\] ENTRY .*?ability=(\S*NewDetailActivity|\S*ArticleInflowActivity).*$',s,re.M)
  row['activity']=ent[1] if ent else None
  resumed=re.search(r'^\[ABILITY38-RESUMED\] uptime=(\d+)',s[ent.end():],re.M) if ent else None
  row['resumed_s']=round(int(resumed[1])/1000-start,3) if resumed else None
 if r.name in reviews:
  v=reviews[r.name];row['visual']=v
  if start is not None and (r/'frames.json').exists():
   frames={f['label']:f for f in json.loads((r/'frames.json').read_text())}
   lo=v.get('last_without_body');hi=v.get('first_body')
   if hi in frames:row['body_s_interval']=[round(float(frames[lo]['before'].split()[0])-start,3) if lo else 0,round(float(frames[hi]['after'].split()[0])-start,3)]
 row['aot_loaded']=bool(re.search(r'^\[IMG\] Loaded /data/local/tmp/asx/oat/arm64/toutiao.art',s,re.M))
 row['file_jit']='using app-private unlinked file with dual RW/RX views' in s
 row['anonymous_jit']='using ART anonymous cache with RWX' in s
 row['sig6_banners']=len(re.findall(r'^Fatal signal 6',s,re.M))
 row['ule']=s.count('UnsatisfiedLinkError');row['layout79']=s.count('Layout: -79');row['main_throw']=s.count('J_invokeStaticMain_main_threw')
 row['faults']=[]
 for f in (r/'faults').glob('*.txt'):
  t=f.read_text(errors='replace')
  if 'signal=0xb' not in t:continue
  sig={k:v for k,v in re.findall(r'^\[CRASH42\] (\w+)=(.*)$',t,re.M)}
  pc=int(sig['pc'],16);maps=f.with_suffix('.maps');hit=None
  if maps.exists():
   for l in maps.read_text().splitlines():
    a=l.split();span=a[0].split('-')
    if len(span)!=2:continue
    lo,hi=map(lambda h:int(h,16),span)
    if lo<=pc<hi:hit={'mapping':l,'file_offset':hex(pc-lo+int(a[2],16))}
  row['faults'].append({'file':f.name,'signal':sig,'mapped_pc':hit,'life_s':round(int(sig['monotonic_ns'],16)/1e9-int(d['birth'])/100,6)})
 final=r/'final-state.txt'
 if final.exists():
  txt=final.read_text();row['final_uptime']=float(txt.split()[0]);row['age_at_final']=round(row['final_uptime']-int(d['birth'])/100,3);row['alive_final']=bool(re.search(r'^'+str(d['child'])+r' \(.+\) [RSID]',txt,re.M))
 rows.append(row)
(R/'summary.json').write_text(json.dumps(rows,indent=2))
for r in rows:print(r['trial'],r.get('resumed_s'),r.get('body_s_interval'),r.get('age_at_final'),r.get('alive_final'),'SIG11',len(r['faults']),'aot/filejit/anon',r['aot_loaded'],r['file_jit'],r['anonymous_jit'])
