"""Test-only transport injection; invokes the unchanged successor CLI parser/action."""
import importlib.util,json,shlex,subprocess,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('tested_successor',Path(__file__).with_name('successor.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
fixture=Path(sys.argv[1]);sys.argv=[str(Path(__file__).with_name('successor.py'))]+sys.argv[2:]
f=json.loads(fixture.read_text());state=f['state'];stages={};events=[];original_load=m.load
class FakeDevice:
 def __init__(self,*a):pass
 def command(self,name,argv):events.append(name);return ''
 def probe(self,p):self.command('probe',[p]);return dict(state[p]) if p in state else {'exists':False}
 def send(self,name,source,target):
  self.command(name,[str(source),target]);state[target]=dict(exists=True,sha256=m.sha(source));stages[target]=str(source)
 def shell(self,name,script):
  self.command(name,[script])
  if name=='boot':return f['boot']
  if name=='stage-absence':return ''
  if name=='stage-metadata':
   for p in stages:
    state[p].update(f['metadata'][p.split('.successor-')[0]])
   return ''
  if name=='atomic-replace':
   words=shlex.split(script);i=words.index('mv');src,dst=words[i+1:i+3];state[dst]=state.pop(src);stages.pop(src);return ''
  raise AssertionError('Unexpected live gate or command during source-only rollback: '+name)
def load(ref,name):
 mod=original_load(ref,name)
 if name=='successor_core':mod.Device=FakeDevice
 return mod
m.load=load
original_run=m.subprocess.run
def run(argv,**kw):
 if argv[:1]==['bash'] and len(argv)>2 and argv[2]=='held':return subprocess.CompletedProcess(argv,0,'outer(codex) 123 2026-10-13T00:00:00\n','')
 raise AssertionError('unexpected subprocess '+str(argv))
m.subprocess.run=run
try:m.main()
finally:
 fixture.with_suffix('.result.json').write_text(json.dumps(dict(state=state,events=events,live=f['live'])))
