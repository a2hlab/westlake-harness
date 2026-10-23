from pathlib import Path
import re,json,hashlib
root=Path(__file__).resolve().parent
p=Path.home()/'.local/share/westlake/startup-stage-coverage-20261023/extended-01/head.stdout'
b=p.read_bytes(); sha=hashlib.sha256(b).hexdigest()
assert sha=='2ee3a988406296170b4ce6511b097a8d3836a21d456f21ca6a18b2bf53219cc6'
lines=b.decode(errors='replace').splitlines()
rx=re.compile(r'^nullptr\s+\w\s+(\d\d-\d\d)\s+(\d\d:\d\d:\d\d)\s+(\d+)\s+(\d+)\s+')
anchors=[]; groups={}; durations=[]
for n,line in enumerate(lines,1):
 m=rx.match(line)
 if m:
  d,t,pid,tid=m.groups(); a=dict(line=n,date=d,time=t,pid=int(pid),tid=int(tid)); anchors.append(a)
  groups.setdefault(pid+'/'+tid,[]).append(a)
  vals=re.findall(r'\b(took|paused|total|for)\s+(\d+(?:\.\d+)?(?:ms|us|ns|s))\b',line)
  if vals:
   rec=dict(a,fields=[dict(label=k,value=v) for k,v in vals],interpretation='Original logged scalars only; no aggregation or causal attribution.')
   if 'Verification of ' in line:
    rec['operation']=line[line.index('Verification of '):].split(' took ')[0]
   else: rec['operation']='Other runtime duration fields (payload omitted; not analyzed)'
   durations.append(rec)
ui=[]
for n in [1172,4326]:
 ui.append({'line':n,'text':lines[n-1],'completion_evidence':False})
r={'status':'bounded-independent-review','input':{'path':'$HOME/.local/share/westlake/startup-stage-coverage-20261023/extended-01/head.stdout','sha256':sha,'bytes':len(b),'lines':len(lines),'final_newline':b.endswith(b'\n')},'owner_output_read':False,'wall_clock':{'first':anchors[0],'last':anchors[-1],'count':len(anchors),'pid_tid_groups':{k:{'count':len(v),'first':v[0],'last':v[-1],'anchors':v} for k,v in groups.items()},'limitations':['Year/timezone are not printed in these prefixes.','Last timestamp is not the end time of this truncated prefix.','Time-anchor span is not an operation duration; log order is not elapsed time.']},'original_duration_records':durations,'ui_completion':{'explicit_first_frame_or_activity_completion':'not_found_in_this_prefix','near_matches_not_completion':ui,'limitation':'Absence of an explicit completion record does not prove the operation did not occur.'},'coverage_end':{'line':len(lines),'partial_record_tag':'[TOUCH21-POLL]','wall_clock':'unknown','first_frame_time':'unknown'},'scope':'Offline specified ordinary log only; no native/source/device/REA/fault analysis.'}
(root/'results.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'sha':sha,'lines':len(lines),'anchors':len(anchors),'groups':len(groups),'duration_records':len(durations),'first':anchors[0],'last':anchors[-1]},ensure_ascii=False))
