#!/usr/bin/env python3
"""Read existing snapshot receipts only; never build, execute argv or access a device."""
import difflib
import hashlib
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
HOME = Path.home()
import sys
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths
# Workspace location is resolved by the existing repository helper.
WORKSPACES = lab_paths.workspaces()
MAIN = WORKSPACES / 'westlake-harness'
BASE = HOME / '.local/share/westlake/native-host-recovery-build-20261024'
OLD, NEW = BASE / 'snapshot-01', BASE / 'snapshot-02'
BUILD01 = MAIN / 'benchmark/2026-10-24-native-host-window-recovery/candidate-build-01'
STAGE = WORKSPACES / 'westlake-harness-t4/benchmark/2026-10-24-wmc-build-preparation/staging-01/.private/staged-03'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return json.loads(p.read_text())

def clean(s):
    for before, after in [(str(OLD),'$SNAPSHOT01'),(str(NEW),'$SNAPSHOT02'),(str(STAGE),'$STAGE'),(str(WORKSPACES),'$WORKSPACES'),(str(HOME),'$HOME')]:
        s = s.replace(before, after)
    return re.sub(r'/home/[^/\s"\']+', '$VM_HOME', s)

def pin(p):
    return {'path':clean(str(p)), 'bytes':p.stat().st_size, 'sha256':sha(p)}

def write(name, obj):
    (OUT/name).write_text(json.dumps(obj,indent=2)+'\n')

units = {'wmc':'wmc.o','input':'input.o','stage':'stage.o','core':'core.o','reader-build':'reader.o','link-01':'liboh_adapter_bridge.so'}
manifest = read(NEW/'review02-manifest.json')
assert sha(NEW/'review02-manifest.json') == 'f156d990caff276ce456027098d23fa0e9558530adaaf26319c2e0af5a4b220c'
pins = read(NEW/'source-pins.json')
for path, expected in pins.items():
    assert sha(NEW/path) == expected, path
for item in manifest['files']:
    assert pins[item['path']] == item['sha256'], item['path']
oldpins = read(OLD/'source-pins.json')
source_delta = [{'path':p,'before_sha256':oldpins.get(p),'after_sha256':h} for p,h in pins.items() if oldpins.get(p)!=h]
commands, receipts, artifacts = {}, {}, {}
for unit, filename in units.items():
    a, b = read(OLD/unit/'argv.json'), read(NEW/unit/'argv.json')
    changes=[]
    for op,i,j,k,l in difflib.SequenceMatcher(a=a,b=b,autojunk=False).get_opcodes():
        if op!='equal': changes.append({'operation':op,'before_range':[i,j],'after_range':[k,l],'before':[clean(x) for x in a[i:j]],'after':[clean(x) for x in b[k:l]]})
    rebuilt=a.copy()
    for item in reversed(changes):
        i,j=item['before_range'];k,l=item['after_range'];rebuilt[i:j]=b[k:l]
    assert rebuilt==b
    receipt=read(NEW/unit/'receipt.json');assert receipt['rc']==0 and receipt['error'] is None
    artifact=NEW/unit/filename
    assert sha(artifact)==receipt.get('object_sha256',receipt.get('output_sha256'))
    if unit != 'link-01':
        assert sha(Path(b[b.index('-c')+1])) == receipt['source_sha256']
    else:
        for other, obj in units.items():
            if other != 'link-01': assert b.count(str(NEW/other/obj)) == 1
    receipts[unit]=receipt; artifacts[unit]=pin(artifact)
    commands[unit]={'before_raw_argv':pin(OLD/unit/'argv.json'),'after_raw_argv':pin(NEW/unit/'argv.json'),'before_argc':len(a),'after_argc':len(b),'delta':changes,'exact_delta_reconstruction_pass':True,'cwd':clean(str(NEW/unit))}
    if unit=='link-01':
        commands[unit]['environment']=json.loads(clean((NEW/unit/'environment.json').read_text()))
        assert (NEW/unit/'cwd.txt').read_text().strip()==str(NEW/unit)
    else:
        first=(NEW/unit/'stderr').read_text().splitlines()[0]
        env=json.loads(first);assert env['cwd']==str(NEW/unit)
        commands[unit]['observed_execution_environment']=json.loads(clean(first))
        commands[unit]['transport_argv']=json.loads(clean((NEW/unit/'transport.json').read_text()))
        commands[unit]['diagnostic_lines_after_environment']=len((NEW/unit/'stderr').read_text().splitlines())-1
assert artifacts['link-01']['sha256']=='3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819'
write('recipe-delta.json',{'aliases':{'$SNAPSHOT01':'$HOME/.local/share/westlake/native-host-recovery-build-20261024/snapshot-01','$SNAPSHOT02':'$HOME/.local/share/westlake/native-host-recovery-build-20261024/snapshot-02','$STAGE':'$WORKSPACES/westlake-harness-t4/benchmark/2026-10-24-wmc-build-preparation/staging-01/.private/staged-03','$VM_HOME':'recorded Linux home; personal path redacted'},'common_recipe':pin(BUILD01/'recipe.sanitized.json'),'source_delta':source_delta,'commands':commands,'notes':['Arrays preserve actual argument order; raw bytes are independently hashed.','Apply indexed edits to snapshot01 argv in reverse index order; aliases are literal path substitutions.','This is a receipt recipe, not an executor. Retain shared baseline SDK/toolchain/input pins from build01.']})
write('raw-index.json',{'root':clean(str(NEW)),'files':[pin(p) for p in sorted(NEW.rglob('*')) if p.is_file()]})
write('results.json',{'status':'OFFLINE_SNAPSHOT02_RECEIPTS_VERIFIED_RUNTIME_UNVERIFIED','build_executor':'outer/root: Linux five-object compilation and Mac complete link','review_executor':'analysis lane: local reads/hash/argv comparison only','candidate_commit':'62a84c76d','review02_manifest':pin(NEW/'review02-manifest.json'),'source_pin_count':len(pins),'source_pins':pins,'source_delta':source_delta,'terminal_runs':receipts,'artifacts':artifacts,'all_six_rc_zero':True,'source_manifest_matches':True,'argv_delta_reconstruction_pass':True,'old_snapshot01_artifact':'158c174067853fd357c1ab2d7dd6a4374684f08d22712bde62018aac8e6a7822','target_snapshot02_artifact':artifacts['link-01']['sha256'],'old_artifact_not_deployment_target':True,'compilations_by_this_review':0,'device_operations':0,'limits':['Build evidence does not establish runtime recovery, feed, API freeze or seal.','CC C1 review and independent main Rust acceptance are separate; not inferred from build rc0.']})
print(json.dumps({'six_rc0':True,'source_pins':len(pins),'changed_sources':len(source_delta),'output_sha256':artifacts['link-01']['sha256']}))
