#!/usr/bin/env python3
"""Conservative synchronous trace parser. No target/device operations."""
import argparse,hashlib,json,re
from collections import defaultdict
from pathlib import Path
LINE=re.compile(r'-(\d+)\s+\([^)]*\).*?\s(\d+\.\d+): tracing_mark_write: (.*)$')
def union(intervals):
    result=[]
    for a,b in sorted(intervals):
        if result and a<=result[-1][1]:result[-1][1]=max(result[-1][1],b)
        else:result.append([a,b])
    return result
def parse(text,pid=6291):
    stacks=defaultdict(list); complete=[]; excluded=[]; anomalies=[]; async_marks=[]; metadata=[]; target_marks=[]; times=[]
    def invalidate(tid,reason,line):
        for s in stacks[tid]:s['issues'].append({'reason':reason,'line':line})
    for lineno,line in enumerate(text.splitlines(),1):
        m=LINE.search(line)
        if not m:continue
        tid,ts,mark=m.groups();tid=int(tid);ts=float(ts);times.append(ts)
        parts=mark.split('|');kind=parts[0]
        rec={'line':lineno,'tid':tid,'time':ts,'marker':mark}
        if mark.startswith('trace_event_clock_sync:'):
            metadata.append(rec);continue
        if kind in ['S','F','C','I','b','e','n']:
            async_marks.append(rec);continue
        if kind=='E' and len(parts)==1:
            if stacks[tid]:
                s=stacks[tid].pop();s.update(end=ts,end_line=lineno,status='excluded_bare_end',duration_ms=None)
                excluded.append(s)
                # Parent pairing can proceed, but its coverage is not fully PID-qualified.
                invalidate(tid,'nested_bare_end',lineno)
            else:anomalies.append(dict(rec,reason='orphan_bare_end'))
            continue
        if len(parts)<2 or kind not in ['B','E'] or not parts[1].isdigit():
            anomalies.append(dict(rec,reason='unparsed_marker'));invalidate(tid,'unparsed_marker',lineno);continue
        recorded_pid=int(parts[1]);name=parts[2] if len(parts)>2 else ''
        if recorded_pid==pid:target_marks.append(rec)
        if kind=='B':
            stacks[tid].append({'pid':recorded_pid,'tid':tid,'name':name,'full_begin_marker':mark,'start':ts,'start_line':lineno,'issues':[]})
            continue
        end_has_name=bool(name and not re.fullmatch(r'I\d+',name))
        if not stacks[tid]:
            anomalies.append(dict(rec,reason='orphan_explicit_end',pid=recorded_pid));continue
        top=stacks[tid][-1]
        if top['pid']!=recorded_pid or (end_has_name and top['name']!=name):
            reason='pid_mismatch' if top['pid']!=recorded_pid else 'name_mismatch'
            anomalies.append(dict(rec,reason=reason,pid=recorded_pid,open_pid=top['pid'],open_name=top['name']))
            # Never search down the stack or let this end close an unrelated begin.
            for s in stacks[tid]:
                s.update(status='excluded_stack_reset_'+reason,problem_line=lineno,duration_ms=None);excluded.append(s)
            stacks[tid]=[];continue
        s=stacks[tid].pop();s.update(end=ts,end_line=lineno,end_pid=recorded_pid,end_name=name)
        if ts<s['start']:s['issues'].append({'reason':'negative_duration','line':lineno})
        if s['issues']:
            s.update(status='excluded_tainted_interval',duration_ms=None);excluded.append(s)
        else:
            s.update(status='complete_explicit_pid_lifo',duration_ms=round((ts-s['start'])*1000,6));complete.append(s)
    for stack in stacks.values():
        for s in stack:s.update(status='unclosed_at_trace_end',duration_ms=None);excluded.append(s)
    spans=[s for s in complete if s['pid']==pid]
    # Inclusive ranking only; union, not a sum of nested or parallel spans, measures coverage.
    intervals=union([(s['start'],s['end']) for s in spans]);covered=sum(b-a for a,b in intervals)
    gaps=[]
    if target_marks:
        cursor=target_marks[0]['time']
        for a,b in intervals:
            if a>cursor:gaps.append([cursor,a])
            cursor=max(cursor,b)
        if cursor<target_marks[-1]['time']:gaps.append([cursor,target_marks[-1]['time']])
    return {'pid':pid,'trace_first_last':[min(times),max(times)] if times else None,'complete_count':len(spans),'top10':sorted(spans,key=lambda s:(-s['duration_ms'],s['start_line']))[:10],'complete_spans':spans,'excluded_spans':[s for s in excluded if s['pid']==pid],'anomalies':anomalies,'async_and_counter_markers':async_marks,'clock_metadata':metadata,'first_last_target_marker':[target_marks[0],target_marks[-1]] if target_marks else [],'complete_span_wall_union_seconds':covered,'complete_span_wall_union':intervals,'gaps_without_complete_span_within_target_markers':gaps,'limitations':['Bare E has no recorded PID/name: unwind same-thread top only as excluded; taint enclosing spans.','PID/name mismatch clears that thread stack; never search backwards for a convenient match.','Unparsed fragments taint enclosing spans; no duration assigned to excluded/unclosed intervals.','Top10 is inclusive elapsed time; do not sum rows. Union is elapsed coverage, not CPU time, critical path, or evidence that unmarked time was idle.','Counter/async markers are retained separately, not synchronously paired.']}
def main():
    p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,default=Path.home()/'.local/share/westlake/current-boot-manual-reopen-20261023/raw/04/t87-61aa5791.trace');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=a.trace.read_bytes();r=parse(data.decode());r['trace_sha256']=hashlib.sha256(data).hexdigest()
    expected='f9a2fe0a760e61cd5833d683e1c95f7feaf4ee91624f5d73e27a68bf4197ac94'
    if r['trace_sha256']!=expected:raise SystemExit('T87 trace SHA mismatch')
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'sha256':r['trace_sha256'],'complete':r['complete_count'],'excluded':len(r['excluded_spans']),'top10':[(x['name'],x['duration_ms'],x['start_line'],x['end_line']) for x in r['top10']]}))
if __name__=='__main__':main()
