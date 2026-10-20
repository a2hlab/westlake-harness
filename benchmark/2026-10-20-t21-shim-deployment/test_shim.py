"""Actual executor gate/transaction tests. No HDC; only host metadata adapters."""
import ast, hashlib, json, os, shlex, subprocess, sys, tempfile, unittest
from pathlib import Path
from test_executor import B, SOURCE, TREE, helpers
from derive import derive

class ShimTests(unittest.TestCase):
 def test_donor_rejected(self):
  with self.assertRaises(AssertionError):derive(b'foreign')

 def test_candidate_refusal_before_board(self):
  for case in ('null','unbuilt','ref_drift'):
   with self.subTest(case=case),tempfile.TemporaryDirectory(dir=B) as td:
    root=Path(td).resolve();(root/'executor.py').write_text(SOURCE)
    # Pin a local fixture receipt solely to get past the unchanged bridge gate.
    evidence=root/'evidence.json';evidence.write_text('{}\n')
    ref={'path':evidence.name,'sha256':hashlib.sha256(evidence.read_bytes()).hexdigest()}
    bridge=json.loads((B/'bridge-candidate.json').read_text());bridge['production_refs']=[ref]
    (root/'bridge-candidate.json').write_text(json.dumps(bridge))
    c=json.loads((B/'shim-candidate.json').read_text())
    if case!='null':c['after_sha256']='a'*64
    if case=='ref_drift':c.update(build_status='PRODUCTION_BUILD_VERIFIED',production_refs=[dict(ref,sha256='b'*64)])
    (root/'shim-candidate.json').write_text(json.dumps(c))
    args=[sys.executable,str(root/'executor.py'),'apply','--execute','--boot','x','--parent','1','--birth','2','--hdc','NEVER_RUN','--holder','x','--out',str(root/'out'),'--repo',str(root),'--inputs',str(root),'--admission',str(root/'missing.json'),'--start','1']
    got=subprocess.run(args,capture_output=True)
    expected={'null':b'shim candidate pin required','unbuilt':b'shim production closure required','ref_drift':b'shim production receipt drift'}[case]
    self.assertNotEqual(got.returncode,0);self.assertIn(expected,got.stderr);self.assertFalse((root/'out').exists())

 def transaction(self,e):
  start=SOURCE.index('script=pre\n');end=SOURCE.index('completion=',start)
  exec(compile(SOURCE[start:end],'actual-t21-transaction','exec'),e)
  return e['script']

 def test_partial_all_six_swaps_restore(self):
  for cut in range(1,7):
   with self.subTest(cut=cut),tempfile.TemporaryDirectory() as td:
    root=Path(td).resolve();stage=root/'stage';stage.mkdir();e=helpers(root)
    names={'SHIM':'webview-t-lib/libwebview_bionic_shim.so','BRIDGE':'liboh_adapter_bridge.so','MEDIA':'media.so','PLAYER':'player.so','DSO':'compat.so'}
    (root/'webview-t-lib').mkdir();before=b'original-run';after=b'candidate-run'
    old={v:('before-'+k).encode() for k,v in names.items() if k!='DSO'};new={v:('after-'+k).encode() for k,v in names.items()}
    (root/'run.sh').write_bytes(before);(stage/'run.sh').write_bytes(after)
    for name,data in old.items():(root/name).write_bytes(data)
    inputs={'SHIM':'libwebview_bionic_shim.so','BRIDGE':names['BRIDGE'],'MEDIA':'libmffmpeg.so','PLAYER':'libttmplayer.so','DSO':names['DSO']}
    for k,name in inputs.items():(stage/name).write_bytes(new[names[k]])
    meta=f'644:{os.getuid()}:{os.getgid()}';label='u:object_r:appdat:s0'
    marker=str(root/names['DSO'])+'.t21-5cd-before-12345678.absent'
    e.update(names,SHIM_INPUT=inputs['SHIM'],stage=str(stage),pre='',meta=meta,label=label,dlabel=label,expected=e['sha'](before),actual=e['sha'](before),before=before,after=after,new=after,parent_guard='',dso_present=False,plan={'compat_absence_marker':marker,'compat_absence_marker_sha256':e['sha'](b'ABSENT\n')})
    for k in 'bmps':e[k+'meta']=meta;e[k+'label']=label
    for k,name in [('B',names['BRIDGE']),('M',names['MEDIA']),('P',names['PLAYER']),('S',names['SHIM'])]:e[k+'BEFORE']=e['sha'](old[name]);e[k+'AFTER']=e['sha'](new[name]);e[k.lower()+'actual']=e[k+'BEFORE']
    e['DSHA']=e['sha'](new[names['DSO']]);e['a'].mode='apply'
    shim='''stat() { /usr/bin/stat -f '%Lp:%u:%g' "$3"; }
ls() { printf 'u:object_r:appdat:s0 %s\\n' "$2"; }
chcon() { return 0; }
chown() { return 0; }
'''
    paths=['run.sh',names['BRIDGE'],names['MEDIA'],names['PLAYER'],names['SHIM']]
    guard='; '.join('test -f '+shlex.quote(str(root/n)+'.t21-5cd-before-12345678') for n in paths)
    guard+='; test "$(cat '+shlex.quote(marker)+')" = ABSENT'
    fail=f'moved=0; mv() {{ {guard}; command mv "$@"; moved=$((moved+1)); test "$moved" -lt {cut}; }}\n'
    got=subprocess.run(['sh','-c','set -eu\n'+shim+fail+self.transaction(e)],capture_output=True)
    self.assertNotEqual(got.returncode,0)
    self.assertEqual((root/names['SHIM']).read_bytes(),new[names['SHIM']])
    for name,data in {'run.sh':before,**old}.items():self.assertEqual(Path(str(root/name)+'.t21-5cd-before-12345678').read_bytes(),data)
    self.assertEqual(Path(marker).read_bytes(),b'ABSENT\n')
    e['a'].mode='rollback';e['new']=before;(stage/'run.sh').write_bytes(before)
    for k,name in [('b',names['BRIDGE']),('m',names['MEDIA']),('p',names['PLAYER']),('s',names['SHIM'])]:e[k+'actual']=e['sha']((root/name).read_bytes())
    e['actual']=e['expected']=e['sha']((root/'run.sh').read_bytes());e['dso_present']=(root/names['DSO']).exists()
    got=subprocess.run(['sh','-c','set -eu\n'+shim+self.transaction(e)],capture_output=True)
    self.assertEqual(got.returncode,0,got.stderr)
    for name,data in {'run.sh':before,**old}.items():self.assertEqual((root/name).read_bytes(),data)
    self.assertFalse((root/names['DSO']).exists())

 def test_actual_shim_plan_cas_guards(self):
  # Execute exact new rollback assertions, not a copied predicate.
  start=SOURCE.index(" assert apply_plan['shim_path']")
  end=SOURCE.index(" assert apply_plan['bridge_path']",start)
  body='\n'.join(l[1:] if l.startswith(' ') else l for l in SOURCE[start:end].splitlines())
  sha=lambda b:hashlib.sha256(b).hexdigest()
  good={'shim_path':'webview-t-lib/libwebview_bionic_shim.so','shim_before_sha':'a'*64,'shim_after_sha':'b'*64,'shim_candidate_sha256':'c'*64,'shim_metadata':'644:20011300:20011300','shim_label':'u:object_r:appdat:s0','compat_absence_marker_sha256':sha(b'ABSENT\n')}
  e=dict(apply_plan=good,SHIM=good['shim_path'],SBEFORE='a'*64,SAFTER='b'*64,sha=sha,sha_file=lambda p:'c'*64,here=B,smeta=good['shim_metadata'],slabel=good['shim_label'],sactual='a'*64)
  for actual in ('a'*64,'b'*64):e['sactual']=actual;exec(body,e)
  for field,value in [('sactual','d'*64),('smeta','644:0:0'),('slabel','foreign')]:
   bad=dict(e);bad[field]=value
   with self.assertRaises(AssertionError):exec(body,bad)
  bad=dict(e);bad['apply_plan']=dict(good,shim_candidate_sha256='d'*64)
  with self.assertRaises(AssertionError):exec(body,bad)

if __name__=='__main__':unittest.main()
