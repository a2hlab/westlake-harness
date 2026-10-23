from pathlib import Path
from decimal import Decimal
import json,re,hashlib
out=Path(__file__).resolve().parent
root=Path.home()/'.local/share/westlake/host-lifecycle-after-retry-limit-20261023';raw=root/'raw'
source=json.loads((out/'source-results.json').read_text())
def pin(p):return {'path':str(p).replace(str(Path.home()),'$HOME'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
ident={}
for when in ['pre','post']:
 lines=(raw/f'ident_{when}.stdout').read_text().splitlines();hosts=[{'line':i,'pid':int(m.group(1))} for i,l in enumerate(lines,1) if (m:=re.match(r'^\s*(\d+)\s+org\.westlake\.imehost\s*$',l))]
 stat=(raw/f'birth_{when}.stdout').read_text();pid=int(stat.split()[0]);birth=int(stat[stat.rindex(')')+2:].split()[19]);assert len(hosts)==1 and hosts[0]['pid']==pid
 ident[when]={'boot':lines[0],'pid':pid,'birth_ticks':birth,'ps_line':hosts[0]['line']}
assert ident['pre']['boot']==ident['post']['boot']=='ecb84d86-f22f-4622-9501-143a26f39cf1'
assert ident['pre']['pid']==ident['post']['pid']==5074 and ident['pre']['birth_ticks']==ident['post']['birth_ticks']==9930
for name in ['ident_pre','ident_post','birth_pre','birth_post','hilog']:assert (raw/(name+'.rc')).read_text().strip()=='0'
text=(raw/'hilog.stdout').read_text();assert not re.search(r'\bCODE\s*[:=]|Invalid argument|Unknown option',text)
assert (raw/'hilog.stderr').stat().st_size==0
lines=text.splitlines();epochs=[];events=[]
for i,l in enumerate(lines,1):
 m=re.match(r'^(\d+\.\d+)\s+(\d+)\s+(\d+)\s+',l)
 if m:epochs.append((m.group(1),i))
 if 'WL_IME_HOST:' not in l:continue
 body=l.split('WL_IME_HOST:',1)[1].strip()
 try:d=json.loads(body)
 except ValueError:continue
 assert m and int(m.group(2))==5074
 details=d.get('details',{});event={'raw_line':i,'hilog_epoch':m.group(1),'pid':int(m.group(2)),'tid':int(m.group(3)),'event':d['event'],'record_time_epoch_ms':d['time']}
 if d['event']=='stage-event':event.update(stage_event=details.get('event'),window_id=details.get('window',{}).get('id'))
 events.append(event)
selected=[x for x in events if 1792766934000<=x['record_time_epoch_ms']<=1792766940000]
assert [(x['raw_line'],x['event']) for x in selected]==[(901,'foreground'),(904,'stage-event'),(917,'stage-event')]
window=(raw/'window_state.stdout').read_text();missing=[{'line':i,'text':l} for i,l in enumerate(window.splitlines(),1) if 'No such file or directory' in l];assert missing
lo=min(epochs,key=lambda x:Decimal(x[0]));hi=max(epochs,key=lambda x:Decimal(x[0]));click=source['t112_click'];assert Decimal(lo[0])<Decimal(str(click['start_epoch']))<Decimal(hi[0])
result={'task':'T114','status':'host_foreground_and_stage_callbacks_observed_no_candidate','identity':ident,'identity_stable':True,'source':source['source'],'t112_click':click,'hilog':{'pin':pin(raw/'hilog.stdout'),'lines':len(lines),'first_epoch':lo[0],'first_epoch_line':lo[1],'last_epoch':hi[0],'last_epoch_line':hi[1],'wl_ime_host_json_events':len(events),'click_within_epoch_range':True,'command_rc':0,'transport_stderr_bytes':0,'code_error_detected':False},'events_at_click':selected,'window_state':{'pin':pin(raw/'window_state.stdout'),'transport_rc':int((raw/'window_state.rc').read_text()),'read_success':False,'observations':missing,'mtime':'unknown','event':'unknown','reason':'stat/head reported missing file; rc0 does not establish content acquisition'},'candidate':None,'conclusion':'Ordinary foreground and stage callbacks were recorded for host5074/window29 near the T112 single click. T112 no-new-child observation is a separate downstream fact, not evidence that host callback was absent.','limitations':['No causal attribution beyond normal host callback arrival.','Host-command and device clocks have no measured offset here: do not turn their timestamp difference into exact input latency.','Hilog first/last timestamps establish retained range, not lossless history. Positive callback records are direct evidence.','Stage enum numeric values are retained without inferring undocumented labels.','Window-state path absence does not identify why the path is absent and does not invalidate positive hilog callbacks.','No onNewWant override is not a demonstrated defect.','T89 source binding reused; no fresh HAP deployment comparison or device/REA/source expansion.']}
(out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(out/'callback-events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n')
files=[p for p in raw.iterdir() if p.is_file() and p.name.split('.')[0] in ['ident_pre','ident_post','birth_pre','birth_post','hilog','window_state']]
(out/'raw-pins.json').write_text(json.dumps([pin(p) for p in sorted(files)],indent=2)+'\n')
source['status']='source_facts_complete; superseded_for_alignment_by_results.json';(out/'source-results.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'identity':ident,'events':selected,'range':[lo,hi],'window_state_read_success':False},ensure_ascii=False))
