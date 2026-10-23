#!/usr/bin/env python3
import argparse,collections,hashlib,json,re
from pathlib import Path
RX=re.compile(r'^\[TOUCH21-POLL\] (enter|exit) now=(-?\d+) tid=(\d+) ptr=(\S+)(?: looper=\S+ timeout=(-?\d+))?$')
def need(v,m):
    if not v:raise RuntimeError(m)
def union(rows):
    spans=[]
    for a,b in sorted((r['start_ms'],r['end_ms']) for r in rows):
        if spans and a<=spans[-1][1]:spans[-1][1]=max(b,spans[-1][1])
        else:spans.append([a,b])
    return {'merged_segment_count':len(spans),'first_last_counter_ms':[spans[0][0],spans[-1][1]] if spans else None,'covered_ms':sum(b-a for a,b in spans)}
def parse(text):
    stacks=collections.defaultdict(list);last={};complete=[];excluded=[];counts=collections.Counter();lines=text.splitlines();partial=not text.endswith('\n')
    def public(b):return {k:v for k,v in b.items() if k!='ptr'}
    for n,l in enumerate(lines,1):
        if n==len(lines) and partial:
            counts['partial_final_line']+=1;continue
        if l.startswith('[TOUCH21-WAKE]'):counts['wake_not_endpoint']+=1;continue
        if not l.startswith('[TOUCH21-POLL]'):continue
        m=RX.fullmatch(l)
        if not m:
            counts['malformed_poll']+=1
            for stack in stacks.values():
                for row in stack:row['issues'].append('malformed_poll_unknown_identity')
            continue
        kind,now,tid,ptr,timeout=m.groups();now=int(now);tid=int(tid);counts['poll_'+kind]+=1;stack=stacks[tid];bad=now<0 or (tid in last and now<last[tid]);last[tid]=max(last.get(tid,now),now)
        if bad:
            counts['negative_or_out_of_order']+=1
            for row in stack:row['issues'].append('negative_or_out_of_order')
        if kind=='enter':
            issues=['negative_or_out_of_order'] if bad else []
            if stack:
                counts['nested_enter']+=1;issues.append('nested')
                for row in stack:row['issues'].append('nested')
            stack.append({'tid':tid,'start_line':n,'start_ms':now,'timeout_raw':int(timeout) if timeout is not None else None,'ptr':ptr,'issues':issues});continue
        if not stack:counts['orphan_exit']+=1;excluded.append({'tid':tid,'end_line':n,'issues':['orphan_exit'],'duration_ms':None});continue
        row=stack.pop();row.update(end_line=n,end_ms=now)
        if bad:row['issues'].append('negative_or_out_of_order')
        if row['ptr']!=ptr:row['issues'].append('pointer_identity_mismatch')
        if row['issues'] or now<row['start_ms']:
            row['duration_ms']=None;excluded.append(public(row))
        else:row['duration_ms']=now-row['start_ms'];row['pointer_identity_equal']=True;complete.append(public(row))
    for stack in stacks.values():
        for row in stack:row['issues'].append('missing_exit');row['duration_ms']=None;excluded.append(public(row));counts['missing_exit']+=1
    return {'complete':complete,'excluded':excluded,'counts':dict(counts)}
def tests():
    def line(k,t,tid=6311):return f'[TOUCH21-POLL] {k} now={t} tid={tid} ptr=opaque'+(' looper=opaque timeout=-1' if k=='enter' else '')
    cases=[('pair',[line('enter',10),line('exit',14)],1,4),('wake_not_exit',[line('enter',10),'[TOUCH21-WAKE] now=11 tid=6311 ptr=opaque looper=opaque'],0,0),('nested',[line('enter',10),line('enter',11),line('exit',12),line('exit',13)],0,0),('out_of_order',[line('enter',10),line('exit',9)],0,0),('thread_isolation',[line('enter',10),line('exit',11,2),line('exit',12)],1,2),('missing_begin',[line('exit',10)],0,0),('negative',[line('enter',-2),line('exit',1)],0,0)]
    out=[]
    for name,ls,num,ms in cases:
        r=parse('\n'.join(ls)+'\n');need(len(r['complete'])==num and union(r['complete'])['covered_ms']==ms,name);need(all(x['duration_ms'] is None for x in r['excluded']),name+' excluded duration');out.append({'case':name,'status':'PASS'})
    r=parse(line('enter',10)+'\n'+line('exit',12));need(not r['complete'] and r['counts']['partial_final_line']==1,'partial');out.append({'case':'partial_final_exit','status':'PASS'});return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--t99',type=Path,required=True);p.add_argument('--t100',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();pins=[]
    def read(q):
        b=q.read_bytes();pins.append({'path':str(q.resolve()).replace(str(Path.home()),'$HOME'),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)});return b
    raw=read(a.input);need(hashlib.sha256(raw).hexdigest()=='2ee3a988406296170b4ce6511b097a8d3836a21d456f21ca6a18b2bf53219cc6','log SHA');manifest=json.loads(read(a.t99/'raw-manifest.json'));idx=json.loads(read(a.t99/'evidence-index.json'));summary=json.loads(read(a.t99/'results.json'));t100=json.loads(read(a.t100));need(summary['target_sha256_before_and_after']=='8ab6742d58de5b9df94a2bfa80cebed46f136c0251083793fcbef8293cc23ab1','target')
    verified=[]
    for name in ['search','02-poll-xrefs','03-poll-decompile','04-wake-xrefs','05-wake-decompile']:
        docs={}
        for suffix in ['receipt.json','stdout']:
            rel=f'.private/logs/{name}.{suffix}';b=read(a.t99/rel);need(hashlib.sha256(b).hexdigest()==manifest[rel]['sha256'],'T99 raw SHA');docs[suffix]=json.loads(b)
        need(docs['receipt.json']['rc']==0,'T99 rc');ev=docs['stdout'];need(ev['subject']['digest']['sha256']==summary['target_sha256_before_and_after'] and ev['evidence_id']==idx['records'][name]['evidence_id'],'T99 identity')
        if name.endswith('decompile'):
            ls=ev['raw_result']['value'].splitlines()
            for row in idx['records'][name]['timing_excerpt']:need(ls[row['line']-1]==row['text'],'T99 exact timing excerpt')
        verified.append({'name':name,'rc':0,'evidence_id':ev['evidence_id']})
    parsed=parse(raw.decode());mainrows=[x for x in parsed['complete'] if x['tid']==6311];top=sorted(mainrows,key=lambda x:(-x['duration_ms'],x['start_line']))[:10];lines=raw.decode().splitlines()
    for row in top:
        b=RX.fullmatch(lines[row['start_line']-1]);e=RX.fullmatch(lines[row['end_line']-1]);need(b[1]=='enter' and e[1]=='exit' and b[3]==e[3]=='6311' and b[4]==e[4],'top raw identity');need(int(e[2])-int(b[2])==row['duration_ms'],'top delta');row['safe_begin']=f'[TOUCH21-POLL] enter now={b[2]} tid=6311 timeout={b[5]}';row['safe_end']=f'[TOUCH21-POLL] exit now={e[2]} tid=6311'
    counters=[]
    for i,l in enumerate(lines,1):
        if i==len(lines):continue
        m=RX.fullmatch(l)
        if m and m[3]=='6311':counters.append({'line':i,'event':m[1],'now_integer_ms':int(m[2])})
    stages=[]
    for n in [1419,2036,5023,5868,6945,6965]:
        bef=[x for x in counters if x['line']<n];aft=[x for x in counters if x['line']>n];stages.append({'stage_line':n,'previous_main_poll_in_file':bef[-1] if bef else None,'next_main_poll_in_file':aft[0] if aft else None,'limit':'File-neighbor counters only, not stage timestamps or duration.'})
    r={'task':'T102 relative POLL intervals','status':'OFFLINE_SAME_THREAD_INTERVALS_VERIFIED_NO_DEFECT_ATTRIBUTION','clock_evidence':{'target_sha256':summary['target_sha256_before_and_after'],'clock_id_argument':1,'expression':'tv_sec * 1000 + tv_nsec / 1000000','unit':'integer milliseconds','verified_T99_receipts':verified,'runtime_clock_gettime_provider':'unknown','cross_clock_alignment':'not performed'},'input_pins':pins,'tests':tests(),'policy':'Same-TID LIFO with all overlapping/nested frames excluded; malformed rows taint open frames. Per-TID backward/negative values excluded; missing endpoints excluded; WAKE never closes. Internal pointer equality additionally checked, pointers never exported. Partial final line excluded.','counts':parsed['counts'],'complete_all_tid':len(parsed['complete']),'complete_main6311':len(mainrows),'excluded':parsed['excluded'],'main6311_top10':top,'main6311_union':union(mainrows),'all_tid_union':union(parsed['complete']),'stage_adjacent_counters':stages,'limits':['POLL elapsed intervals may contain waiting or other work; neither timeout=-1 nor a long interval establishes a defect or CPU use.','Union is elapsed observed coverage in this counter domain, not summed parallel work or startup critical path.','No subtraction from trace/wall time, no birth-tick conversion, and missing records are not blocking evidence.','Integer endpoints quantize durations; zero ms does not establish zero execution time.'],'actions':{'device':0,'REA':0,'stopped_source':0,'git':0},'author_commit':None}
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'main_complete':len(mainrows),'all_complete':len(parsed['complete']),'excluded':len(parsed['excluded']),'main_union_ms':r['main6311_union']['covered_ms'],'top10':[(x['start_line'],x['end_line'],x['duration_ms']) for x in top],'tests':len(r['tests'])}))
if __name__=='__main__':main()
