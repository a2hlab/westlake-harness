"""Execute the real reader's final binding/receipt block with synthetic reads only."""
import argparse, ast, contextlib, hashlib, io, json, re, sys, textwrap
from pathlib import Path
from types import SimpleNamespace
p=argparse.ArgumentParser();p.add_argument('--reader',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
s=a.reader.read_text();tree=ast.parse(s);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
slots=ast.literal_eval(next(n.value for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='slots' for t in n.targets)))
expected=[0x48f978,0x48fb60,0x490728,0x48fb88,0x490340,0x48f218,0x5d08,0x5d10,0x5d18,0x5d20,0x5d28]
assert [v[2] for v in slots]==expected and all(v[3]==8 for v in slots)
start=s.index("    values = {r['label']");end=s.index('\n\n\nif __name__',start)
block=textwrap.dedent(s[start:end]);a.out.mkdir(parents=True,exist_ok=False)
results=[]
for left,right in [(True,True),(True,False),(False,True),(False,False)]:
 out=a.out/f'{int(left)}{int(right)}';out.mkdir()
 env=dict(json=json,sys=sys,re=re,out=out,a=SimpleNamespace(parent=123),after_rows=[],biases={'libandroid_native_network_compat.so':(0x100000,'')},read=lambda cmd:'export WESTLAKE_ANDROID_NATIVE_NET_TARGETS=libsscronet.so:libmffmpeg.so\n',result={'reads':[{'label':'media_getaddrinfo_GOT','value':hex(0x1023f4 if left else 0x200000)},{'label':'media_freeaddrinfo_GOT','value':hex(0x102a00 if right else 0x200000)}]})
 buf=io.StringIO();exit_message=None
 with contextlib.redirect_stdout(buf):
  try:exec(compile(block,'actual-reader-tail','exec'),env)
  except SystemExit as e:exit_message=str(e)
 assert (exit_message is None)==(left and right)
 if exit_message:assert 'NETWORK_BINDING_MISMATCH' in exit_message
 assert (out/'reads.json').is_file() and buf.getvalue()
 (out/'stdout.txt').write_text(buf.getvalue())
 results.append({'get_match':left,'free_match':right,'exit_message':exit_message,'receipt_preserved':True})
result={'status':'PASS_OFFLINE_ONLY','reader_sha256':hashlib.sha256(s.encode()).hexdigest(),'offsets_exact':11,'cases':results,'scope':'real final source block with synthetic values; no Board import or transport; provider identity branches reviewed statically','device_calls':0}
(a.out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
