#!/usr/bin/env python3
"""Index only existing CC method evidence, never invokes REA or devices."""
from pathlib import Path
import hashlib,json
O=Path(__file__).resolve().parent;C=Path.home()/'.claude/projects'/('-Users-'+Path.home().name+'-orca-workspaces-westlake-harness-video')/'7f25f2f3-9c80-48b3-9d33-751b56041b1e/tool-results';wanted={'play','c0','h1','k1','a1','C1','e1','i1','d1','f1','w1','a0','N0'};out=[]
for p in sorted(C.glob('mcp-rea-inspect_android_method-*.txt')):
 try:d=json.loads(p.read_text())
 except ValueError:continue
 par=d.get('parameters',{})
 if par.get('class_name')!='X.C4cC' or par.get('method_name') not in wanted:continue
 n=d['normalized_result'];body=n['source']['text'];assert d['subject']['digest']['sha256']=='a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395'
 out.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'evidence_id':d['evidence_id'],'method':par['method_name'],'descriptor':n['method']['dex_descriptor'],'source_text_sha256':hashlib.sha256(body.encode()).hexdigest(),'body_lines':len(body.splitlines()),'markers':n.get('markers'),'body_status':n.get('body_status'),'fallback':n.get('fell_back'),'warnings':[x.strip() for x in body.splitlines() if 'JADX WARN' in x or 'Type inference failed' in x],'selected_call_lines':[{'line':i,'text':l.strip()} for i,l in enumerate(body.splitlines(),1) if any(s in l for s in ['setDataSource(','prepareAsync(','this.d.','C1(','e1(','i1(','d1(','f1(','a1(','k1(','h1(','this.O3.','qjn.','O1(true)','isIP(str)','indexOf("http")'])]})
(O/'method-index.json').write_text(json.dumps({'apk_sha256':'a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395','cache_session':'7f25f2f3-9c80-48b3-9d33-751b56041b1e','line_scope':'1-based normalized_result.source.text, not Java original source lines','methods':out,'device_calls':0,'REA_calls':0},indent=2)+'\n');print([(x['method'],x['body_lines']) for x in out])
