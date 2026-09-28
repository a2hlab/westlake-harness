"""B1 evidence selectors: preserve a real failure for the Wikipedia gate."""
import hashlib,json,sys
from pathlib import Path
r=Path(__file__).resolve().parent
def verify_hashes():
 for a in json.loads((r/'manifest.json').read_text()):
  p=(r/a['path']).resolve();assert p.is_relative_to(r)
  assert hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'],str(p)
def properties(file):
 rows=[line.split() for line in file.read_text().splitlines()]
 assert len(rows)==10 and all(len(x)==5 for x in rows)
 return {x[0]:x[1:] for x in rows}
def main(mode):
 verify_hashes()
 roots=r/'evidence/roots'
 if mode=='roots':
  hello=properties(roots/'helloworld.txt');wiki=properties(roots/'wikipedia-before-repeat.txt')
  assert hello.keys()==wiki.keys()
  for path in hello:
   hm,hu,hg,hl=hello[path];wm,wu,wg,wl=wiki[path]
   assert hu=='20010055' and wu=='20010057'
   assert (hm,hl)==(wm,wl),(path,hello[path],wiki[path])
   assert (hg,wg)==(('1007','1007') if path.endswith('/log') else ('20010055','20010057'))
 elif mode=='idempotent':
  result=json.loads((roots/'result.json').read_text())
  assert result['repeat_receipt']['return_code']==0 and result['unchanged']
  assert properties(roots/'wikipedia-before-repeat.txt')==properties(roots/'wikipedia-after-repeat.txt')
 elif mode=='wikipedia':
  result=json.loads((r/'results.json').read_text())
  assert result['sample_span_seconds']>=15
  assert (r/'evidence/wikipedia/t3.jpeg').is_file() and (r/'evidence/wikipedia/final.jpeg').is_file()
  assert result['pids_after'], 'Wikipedia does not survive: DefaultIcon ClassNotFoundException, child exits 1; visual gate NOT met'
  assert result['outer_visual_verdict']=='LIT', 'outer visual acceptance pending'
 else:raise ValueError(mode)
 print(mode+': passed')
if __name__=='__main__':main(sys.argv[1])
