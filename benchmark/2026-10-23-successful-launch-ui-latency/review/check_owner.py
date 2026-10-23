#!/usr/bin/env python3
"""Offline checks of the owner's actual parser, never device commands."""
import argparse,hashlib,json,runpy
from pathlib import Path

def need(ok,msg):
    if not ok: raise RuntimeError(msg)
def mark(tid,t,payload):
    return f' <...>-{tid} (-------) [005] ..... {t:.6f}: tracing_mark_write: {payload}'
def main():
    p=argparse.ArgumentParser();p.add_argument('--owner',type=Path,required=True);p.add_argument('--trace',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=a.owner/'parse_trace.py';before=source.read_bytes();parse=runpy.run_path(str(source))['parse'];rows=[]
    def test(name,events,expected,excluded=0):
        r=parse('\n'.join(mark(*e) for e in events));pairs=sorted((x['start_line'],x['end_line']) for x in r['complete_spans']);need(pairs==expected,name+': pairing');need(len(r['excluded_spans'])==excluded,name+': excluded');need(all(x['duration_ms'] is None for x in r['excluded_spans']),name+': invented duration');rows.append({'case':name,'status':'PASS','complete_pairs':pairs,'excluded_count':excluded});return r
    r=test('nested',[(1,1,'B|6291|outer'),(1,2,'B|6291|inner'),(1,3,'E|6291|inner'),(1,5,'E|6291|outer')],[(1,4),(2,3)])
    need(r['complete_span_wall_union_seconds']==4,'nested union');need(sum(x['duration_ms'] for x in r['complete_spans'])==5000,'inclusive fixture')
    test('unclosed_and_orphan',[(1,1,'E|6291|orphan'),(1,2,'B|6291|unfinished')],[],1)
    test('thread_isolation',[(1,1,'B|6291|x'),(2,2,'E|6291|x'),(1,4,'E|6291|x')],[(1,3)])
    test('pid_mismatch_conservative_reset',[(1,1,'B|6291|x'),(1,2,'E|9999|x'),(1,4,'E|6291|x')],[],1)
    test('bare_end_excludes_parent',[(1,1,'B|6291|outer'),(1,2,'B|6291|inner'),(1,3,'E'),(1,5,'E|6291|outer')],[],2)
    test('named_mismatch',[(1,1,'B|6291|x'),(1,2,'E|6291|other')],[],1)
    data=a.trace.read_bytes();text=data.decode();actual=parse(text);saved=json.loads((a.owner/'intervals.json').read_text());need(saved.pop('trace_sha256')==hashlib.sha256(data).hexdigest(),'trace SHA');need(actual==saved,'owner result differs from actual parser replay')
    lines=text.splitlines();raw=[]
    for s in actual['top10']:
        b,e=lines[s['start_line']-1],lines[s['end_line']-1]
        def fields(line):
            left,marker=line.split(': tracing_mark_write: ',1);timestamp=float(left.split()[-1]);tid=int(left.split(' (',1)[0].rsplit('-',1)[1]);parts=marker.split('|');return tid,timestamp,parts
        bt,bs,bp=fields(b);et,es,ep=fields(e)
        need(bt==et==s['tid'] and bp[0]=='B' and ep[0]=='E' and bp[1]==ep[1]=='6291' and bp[2]==ep[2]==s['name'],'top raw identity')
        need(round((es-bs)*1000,6)==s['duration_ms'],'raw duration');raw.append({'start_line':s['start_line'],'end_line':s['end_line'],'begin':b,'end':e,'duration_ms':s['duration_ms']})
    need(source.read_bytes()==before,'owner source changed during review')
    result={'status':'PARSER_AND_TOP10_OFFLINE_CHECKS_PASS_NOT_CAUSAL_ATTRIBUTION','parser_sha256':hashlib.sha256(before).hexdigest(),'intervals_sha256':hashlib.sha256((a.owner/'intervals.json').read_bytes()).hexdigest(),'trace_sha256':hashlib.sha256(data).hexdigest(),'cases':rows,'complete_count':actual['complete_count'],'excluded_count':len(actual['excluded_spans']),'union_seconds':actual['complete_span_wall_union_seconds'],'top10_raw':raw,'device_calls':0,'limitations':['PID mismatch conservatively resets that thread stack; this loses evidence rather than cross-pairing.','Review fixtures thread_and_pid_isolation expected pair is superseded by this explicitly tested conservative reset policy.','No device-shell, first-frame, CPU-time or root-cause inference.']}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['top10_raw','limitations']}))
if __name__=='__main__':main()
