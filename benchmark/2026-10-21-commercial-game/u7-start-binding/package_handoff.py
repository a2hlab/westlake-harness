#!/usr/bin/env python3
"""Publish sanitized offline receipts and fixed path-only delivery, without Git writes."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];WS=ROOT.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,data):p.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
def portable(s):return s.replace(str(ROOT),'$REPO').replace(str(WS),'$WORKSPACES').replace(str(Path.home()),'$HOME')
def main():
    index=[]
    for src in sorted((HERE/'.private').rglob('*')):
        if not src.is_file() or src.suffix in ['.py','.pyc'] or '__pycache__' in src.parts:continue
        dst=HERE/'evidence'/src.relative_to(HERE/'.private');dst=dst.with_name(dst.name+'.txt') if dst.suffix in ['.stdout','.stderr'] else dst;dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_text(portable(src.read_text()));index.append({'original':'$G22/.private/'+str(src.relative_to(HERE/'.private')),'original_sha256':sha(src),'original_size':src.stat().st_size,'sanitized':str(dst.relative_to(HERE)),'sanitized_sha256':sha(dst),'transformation':'literal workspace/home path substitutions only'})
    save(HERE/'evidence-index.json',index)
    before=json.loads((HERE/'source-before.json').read_text())
    for name in ['deploy_generation.py','deployment_native_gate.py','selinux_label_audit.py']:assert sha(ROOT/'scripts/lab'/name)==before[name]['lane_sha256']
    source=ROOT/'scripts/lab/u7_executor.py';original=HERE/'.private/u7-before.py';assert sha(original)==before['u7_executor.py']['main_sha256']
    (HERE/'source.diff').write_text(''.join(difflib.unified_diff(original.read_text().splitlines(True),source.read_text().splitlines(True),fromfile='a/scripts/lab/u7_executor.py',tofile='b/scripts/lab/u7_executor.py')))
    records=json.loads((HERE/'.private/checks-01/records.json').read_text());assert all(r['rc']==0 for r in records)
    save(HERE/'results.json',{'status':'OFFLINE_VERIFIED','production_source_sha256':sha(source),'main_preimage_sha256':sha(original),'source_copy_required':False,'initial_reproduction_rc':1,'initial_reproduction_error':"AttributeError: 'DeviceIO' object has no attribute 'a'",'new_python_tests':10,'original_u7_python_tests':30,'original_label_python_tests':19,'rust_targets':{'u7_executor':7,'selinux_label_recipe':1,'u7_start_manifest_binding':1},'check_rc':[r['rc'] for r in records],'device_io':False,'runtime_build':False,'label_recipe_modified':False,'deployment_start_modified':False,'label_bypass_enabled':False,'execution_enabled':False})
    ref=HERE/'contract';ref.mkdir(exist_ok=True)
    for name in ['t22-u7-start-binding','t21-gles-bounded-window']:
        p=WS/'westlake-harness/specs/commercial-game-round1'/(name+'.spec.md');(ref/(name+'.reference.txt')).write_bytes(p.read_bytes())
    save(HERE/'documentation.json',{'.octos/KNOWLEDGE-DIGEST.md':['- G22: U7 DeviceIO inherited Deployment.start without self.a/self.m; bind candidate on verified check_ticket and baseline on verified check_restore, never select by shared host SHA. Recheck gate ticket/manifest before real label recipe and service start; readonly IO remains unbound. Offline 10-case real-start regression covers apply and all three restores.'],'.octos/OPS-RUNBOOK.md':['- U7 start/recovery requires the manifest context established by original check_ticket/check_restore; direct unbound DeviceIO.start refuses before commands. Landed U7 code changes alter policy binding: re-run the original preflight before a new window; do not bypass label recipe or reuse a stale candidate ticket.']})
    files={p for p in HERE.rglob('*') if p.is_file() and '.private' not in p.parts and '__pycache__' not in p.parts and p.name!='manifest.json'}
    files|={source,ROOT/'tools/spec-checks/tests/u7_start_manifest_binding.rs',HERE/'landing-paths.txt'}
    paths=sorted(str(p.relative_to(ROOT)) for p in files|{HERE/'manifest.json'});(HERE/'landing-paths.txt').write_text('\n'.join(paths)+'\n')
    save(HERE/'manifest.json',{'files':{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)},'execution_enabled':False})
    print(json.dumps({'paths':len(paths),'source_sha256':sha(source),'manifest_sha256':sha(HERE/'manifest.json')}))
if __name__=='__main__':main()
