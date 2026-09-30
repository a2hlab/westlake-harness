#!/usr/bin/env python3
"""Check actual DEX/source/input provenance; no device or runtime operation."""
import copy,hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((P/'results.json').read_text())
assert d['candidate_modified'] is False and d['board_commands'] is False
assert len(d['clusters'])==8 and d['primary_keys']==20
assert len({k for c in d['clusters'] for k in c['keys']})==20
assert sha(Path(d['input_table']))==d['input_sha256']
for s in json.loads((P/'sources.json').read_text()):
 assert sha(P/s['snapshot'])==s['sha256'] and s['git_identical']
for e in json.loads((P/'evidence.json').read_text()):
 f=Path(e['path']);assert sha(f)==e['sha256']
 lines=f.read_text(errors='replace').splitlines()
 for m in e['matches']:assert lines[m['line']-1]==m['text']
rows=json.loads((P/'webview-dex.json').read_text())
assert len(rows)==3
for r in rows:assert sha(Path(r['input']))==r['sha256']
methods={m['class']+'->'+m['method']:m for r in rows for m in r['methods']}
factory='Landroid/webkit/WebViewFactory;->'
def feature_branch(m):
 ins=m['instructions'];at={x['offset']:x for x in ins}
 i=next(i for i,x in enumerate(ins) if '->isWebViewSupported()Z' in x['operands'])
 branch=ins[i+2];assert branch['opcode']=='if-eqz'
 target=branch['offset']+2*int(re.search(r'\+([0-9a-f]+)h',branch['operands'])[1],16)
 assert at[target]['opcode']=='new-instance' and 'Ljava/lang/UnsupportedOperationException;' in at[target]['operands']
 assert at[target+4]['opcode']=='invoke-direct' and '-><init>()V' in at[target+4]['operands']
feature_branch(methods[factory+'getProvider'])
supported=methods[factory+'isWebViewSupported']['instructions']
assert any('android.software.webview' in x['operands'] for x in supported)
pm=methods['Ladapter/packagemanager/PackageManagerAdapter;->hasSystemFeature']['instructions']
features=[x['operands'] for x in pm if x['opcode']=='const-string' and 'android.' in x['operands']]
assert len(features)==6 and all('android.hardware.' in x for x in features)
assert any(x['opcode']=='return' and x['operands']=='v1' for x in pm)
assert any(x['opcode']=='const/4' and x['operands']=='v1, 0' for x in pm)
# Reject an evidence mutation that would send the condition to a different exception.
bad=copy.deepcopy(methods[factory+'getProvider'])
for x in bad['instructions']:
 if x['opcode']=='new-instance' and 'UnsupportedOperationException' in x['operands']:x['operands']=x['operands'].replace('UnsupportedOperationException','IllegalStateException')
try:feature_branch(bad)
except AssertionError:pass
else:raise AssertionError('mutated branch incorrectly accepted')
print('PASS 8 clusters/20 primary keys, 4 pinned donor sources, 3 real JARs, feature branch and negative, exact log excerpts')
