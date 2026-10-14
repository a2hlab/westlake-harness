#!/usr/bin/env python3
"""Compare real JAR/DEX bytes and full locked-tool disassembly; never replace SHA acceptance."""
import argparse,hashlib,json,struct,subprocess,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
def sha(data):return hashlib.sha256(data).hexdigest()
def read_dex(path):
 data=path.read_bytes()
 if path.suffix=='.jar':
  with zipfile.ZipFile(path) as z:data=z.read('classes.dex')
 assert data[:4]==b'dex\n' and len(data)>=112,'invalid DEX'
 assert struct.unpack_from('<I',data,32)[0]==len(data),'DEX length'
 return data
def sections(data):
 off=struct.unpack_from('<I',data,52)[0];n=struct.unpack_from('<I',data,off)[0]
 rows=[struct.unpack_from('<HHII',data,off+4+12*i) for i in range(n)]
 assert len({r[0] for r in rows})==n and rows==sorted(rows,key=lambda r:r[3])
 return [(kind,count,start,rows[i+1][3] if i+1<n else len(data)) for i,(kind,unused,count,start) in enumerate(rows)]
def byte_report(a,b):
 sa,sb=sections(a),sections(b);assert [(r[:3]) for r in sa]==[(r[:3]) for r in sb],'layout/count changed'
 return [{'map_type':hex(k),'count':c,'offset':s,'bytes':e-s,'equal':a[s:e]==b[s:e],
          'differing_bytes':sum(x!=y for x,y in zip(a[s:e],b[s:e])),'historical_sha256':sha(a[s:e]),'rebuilt_sha256':sha(b[s:e])} for k,c,s,e in sa]
def logical(p):
 try:return str(p.resolve().relative_to(REPO))
 except ValueError:return '${EXTERNAL}/'+p.name
def compare(hist,new,inputs,out):
 assert not out.exists(),'existing output';out.mkdir(parents=True)
 lock=json.loads((HERE/'j1/dependencies.lock.json').read_text())
 for r in lock['files']:
  p=inputs/r['name'];assert p.stat().st_size==r['bytes'] and sha(p.read_bytes())==r['sha256'],r['name']
 cp=':'.join(str(p) for p in sorted(inputs.glob('*.jar')) if p.name not in ('android.jar','d8.jar') and not p.name.startswith('baseline'))
 a,b=read_dex(hist),read_dex(new);raw=byte_report(a,b);executions=[];trees=[]
 for label,data in [('historical',a),('rebuilt',b)]:
  dex=out/(label+'.dex');dex.write_bytes(data);tree=out/(label+'-smali');trees.append(tree)
  args=['java','-cp',cp,'org.jf.baksmali.Main','disassemble',str(dex),'-o',str(tree)]
  stdout=out/(label+'.stdout.txt');stderr=out/(label+'.stderr.txt')
  with stdout.open('wb') as o,stderr.open('wb') as e:q=subprocess.run(args,stdout=o,stderr=e)
  executions.append({'tool':'org.jf.baksmali.Main','argv':['java','-cp','${PINNED_INPUTS_CLASSPATH}','org.jf.baksmali.Main','disassemble',logical(dex),'-o',logical(tree)],'rc':q.returncode,'stdout':stdout.name,'stdout_sha256':sha(stdout.read_bytes()),'stderr':stderr.name,'stderr_sha256':sha(stderr.read_bytes())})
  assert q.returncode==0,'disassembly failed'
 manifests=[{str(p.relative_to(t)):sha(p.read_bytes()) for p in t.rglob('*.smali')} for t in trees]
 left,right=manifests
 classes={'historical_count':len(left),'rebuilt_count':len(right),'added':sorted(right.keys()-left.keys()),'removed':sorted(left.keys()-right.keys()),'changed':sorted(k for k in left.keys()&right.keys() if left[k]!=right[k]),'historical':left,'rebuilt':right}
 (out/'classes.json').write_text(json.dumps(classes,indent=2)+'\n')
 jar_changes=None
 if hist.suffix==new.suffix=='.jar':
  with zipfile.ZipFile(hist) as hz,zipfile.ZipFile(new) as nz:
   assert hz.namelist()==nz.namelist(),'JAR member drift'
   jar_changes=[n for n in hz.namelist() if hz.read(n)!=nz.read(n)]
 result={'historical':{'path':logical(hist),'artifact_sha256':sha(hist.read_bytes()),'dex_sha256':sha(a),'dex_bytes':len(a)},'rebuilt':{'path':logical(new),'artifact_sha256':sha(new.read_bytes()),'dex_sha256':sha(b),'dex_bytes':len(b)},'historical_exact_match':hist.read_bytes()==new.read_bytes(),'jar_changed_members':jar_changes,'full_disassembly_equal':left==right,'class_counts':[len(left),len(right)],'class_added':classes['added'],'class_removed':classes['removed'],'class_changed':classes['changed'],'sections':raw,'executions':executions,'device_calls':0,'semantic_identity_is_not_historical_sha_acceptance':True}
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');return result
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--historical',type=Path,required=True);ap.add_argument('--rebuilt',type=Path,required=True);ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();print(json.dumps(compare(a.historical,a.rebuilt,a.inputs,a.out),indent=2))
if __name__=='__main__':main()
