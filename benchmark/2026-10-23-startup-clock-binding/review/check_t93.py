#!/usr/bin/env python3
"""Local independent field/privacy review; no device or source-chain commands."""
import argparse,hashlib,json,re,subprocess,sys,time
from pathlib import Path

def need(value,message):
    if not value: raise RuntimeError(message)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    a=argparse.ArgumentParser();a.add_argument('--owner',type=Path,required=True);a.add_argument('--raw',type=Path,required=True);a.add_argument('--out',type=Path,required=True);x=a.parse_args()
    x.out.mkdir(parents=True,exist_ok=False)
    script=x.owner/'extract_evidence.py';published=x.owner/'results.json';pins={('owner/'+p.name if p in [script,published] else 'raw/'+p.name):sha(p) for p in [script,published,x.raw/'head.stdout',x.raw/'head.json',x.raw/'boot.stdout',x.raw/'results.json']}
    data=(x.raw/'head.stdout').read_bytes();lines=data.decode().splitlines();need(pins['raw/head.stdout']=='3eabb43dff55b5f6ca31569a25131ba7f8474487f9daf29c5c21f4621407202d','raw hash');need(len(data)==21154 and len(lines)==300,'raw bounds')
    need(not sys.flags.optimize,'run checks without Python optimization')
    argv=[sys.executable,str(script),'--input',str(x.raw),'--output',str(x.out/'reextracted.json')]
    (x.out/'command.json').write_text(json.dumps({'argv':argv,'start_ns':time.time_ns(),'python_optimization':sys.flags.optimize})+'\n')
    p=subprocess.run(argv,capture_output=True,timeout=15);(x.out/'stdout').write_bytes(p.stdout);(x.out/'stderr').write_bytes(p.stderr);(x.out/'receipt.json').write_text(json.dumps({'rc':p.returncode,'end_ns':time.time_ns()})+'\n');need(p.returncode==0,'extractor execution')
    d=json.loads(published.read_text());need(json.loads((x.out/'reextracted.json').read_text())==d,'published result replay')
    need(d['input_sha256']==pins['raw/head.stdout'] and d['bytes']==len(data) and d['lines']==len(lines),'input fields')
    need(d['collection_rc']==json.loads((x.raw/'head.json').read_text())['rc']==0,'collection rc')
    need(d['boot']==(x.raw/'boot.stdout').read_text().strip(),'boot field')
    for s in d['untimed_stage_sequence']:
        need(s['excerpt']==lines[s['line']-1],'stage original line');need(s['timestamp'] is None and s['duration'] is None,'untimed stage fabricated')
    for s in d['wall_clock_pid_anchors']:
        t=lines[s['line']-1].split();need([s['month_day'],s['wall_time'],str(s['pid']),str(s['tid'])]==t[2:6],'anchor fields');need(set(s)=={'line','month_day','wall_time','pid','tid','precision','message_omitted'},'anchor payload exposed')
    for s in d['raw_time_counters']:
        line=lines[s['line']-1];fields=dict(re.findall(r'\b(now|tid)=(\d+)',line));need(s['now_raw']==int(fields['now']) and s['tid']==int(fields['tid']),'counter fields');need(s['event'] in ['[TOUCH21-POLL] enter','[TOUCH21-POLL] exit','[TOUCH21-WAKE]'],'counter prefix');need(s['unit']==s['clock_domain']=='unknown','unbound clock');need(set(s)=={'line','event','now_raw','tid','unit','clock_domain','pointer_fields_omitted'},'counter payload exposed')
    public=published.read_text();privacy_patterns={'personal_home':r'/Users/|/home/','pointer':r'0x[0-9a-fA-F]{6,}','url':r'https?://','secret_assignment':r'(?i)(?:password|passwd|token|cookie|ssid|session_id)\s*[=:]\s*[^\s,}]+'}
    hits={k:bool(re.search(v,public)) for k,v in privacy_patterns.items()};need(not any(hits.values()),'published sensitive-shaped data')
    need(d['trace_comparison']['now_counter_delta_to_trace'] is None,'unbound counter delta');need(d['optimization_candidate'] is None,'fabricated optimization')
    need(sha(script)==pins['owner/extract_evidence.py'] and sha(published)==pins['owner/results.json'],'owner changed during review')
    result={'status':'T93_EXTRACTION_FIELDS_PRIVACY_PASS_T94_OWNER_PENDING','pins':pins,'raw_bytes':len(data),'raw_lines':len(lines),'stage_lines_verified':[s['line'] for s in d['untimed_stage_sequence']],'anchors_verified':len(d['wall_clock_pid_anchors']),'counters_verified':len(d['raw_time_counters']),'privacy_pattern_hits':hits,'privacy_scope':'All 25 exported stage excerpts read; anchors expose only date/time/PID/TID, five counters expose only event/now/TID and omit original pointer fields. No raw log copied to public output. Pattern scans support this concrete review, not a general secret-detection guarantee.','owner_clock_binding':'pending','clock_domain':'unknown until source and deployed artifact binding independently reviewed','actions':{'device':0,'deployment':0,'REA':0,'restricted_source':0},'limits':['T93 extractor uses Python assert guards: this review ran unoptimized Python; -O is not a supported verified execution.','Wall-clock/trace relation is an inherited T92 statement, not established by this extractor or the five now values.','No complete startup-stage duration inferred.'],'author_commit':None}
    (x.out/'review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'stages':len(d['untimed_stage_sequence']),'anchors':len(d['wall_clock_pid_anchors']),'counters':len(d['raw_time_counters']),'rc':p.returncode}))
if __name__=='__main__': main()
