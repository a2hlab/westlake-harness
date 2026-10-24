#!/usr/bin/env python3
"""Compile/run only local C++ fixtures. Raw receipts are persistent and exclusive."""
import argparse, hashlib, json, os, shutil, subprocess, sys, time, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO/'scripts/lab'))
import lab_paths

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reader',type=Path)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    reader=(args.reader or lab_paths.harness()/'benchmark/2026-10-24-native-host-window-recovery/record-reader').resolve()
    out=(args.out or ROOT/'.private'/('test-'+uuid.uuid4().hex)).resolve()
    out.mkdir(parents=True,exist_ok=False);(out/'fixtures').mkdir()
    dependency=json.loads((ROOT/'t1-dependency.json').read_text())
    assert sha(reader/'host_window_record_reader.cpp')==dependency['cpp_sha256']
    assert sha(reader/'host_window_record_reader.h')==dependency['header_sha256']
    wmc=(ROOT/'candidate/oh_window_manager_client.cpp').read_text()
    inp=(ROOT/'candidate/oh_input_bridge.cpp').read_text()
    stage=(ROOT/'candidate/session_stage_adapter.cpp').read_text()
    assert 'if (recoveryStates().count(persistentId)) startRecordObserver();' in wmc
    assert 'data.WriteInt32(actualId);' in wmc
    assert 'data.WriteInt32(static_cast<int32_t>(windowId)) && data.WriteBool(true)' in wmc
    assert inp.count('Routes::instance().logical(event->GetAgentWindowId())')==2
    assert 'recoveryGate_->submit(name, [this, name, sig, values]' in stage
    assert 'return recoveryGate_->activate();' in stage
    assert '#include "wmc_recovery_impl.inc"' in wmc
    assert 'ParentCache::instance().committed()' in wmc
    assert 'ParentCache::instance().publish(next.parent)' in (ROOT/'candidate/wmc_recovery_impl.inc').read_text()
    sources=[ROOT/'candidate/session_recovery.cpp',reader/'host_window_record_reader.cpp',ROOT/'tests/session_recovery_test.cpp']
    headers=[ROOT/'candidate/session_recovery.h',reader/'host_window_record_reader.h',reader/'vendor/nlohmann/json.hpp']
    inputs={str(p):sha(p) for p in sources+headers+list((ROOT/'candidate').glob('*')) if p.is_file()}
    compiler=shutil.which(os.environ.get('CXX','clang++'))
    if not compiler:raise RuntimeError('CXX unavailable')
    receipts=[]
    for label,cmd in [('compiler',[compiler,'--version']),('compile',[compiler,'-std=c++17','-Wall','-Wextra','-Werror','-pedantic','-pthread','-I',str(ROOT/'candidate'),'-I',str(reader),*map(str,sources),'-o',str(out/'fixtures-test')]),('test',[str(out/'fixtures-test'),str(out/'fixtures')])]:
        part=out/label;part.mkdir();start=time.time()
        with (part/'stdout').open('wb') as stdout,(part/'stderr').open('wb') as stderr:
            try: rc=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=120).returncode
            except subprocess.TimeoutExpired:rc=124
        receipt={'argv':cmd,'rc':rc,'start_epoch':start,'end_epoch':time.time(),'stdout_sha256':sha(part/'stdout'),'stderr_sha256':sha(part/'stderr')}
        (part/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');receipts.append(receipt)
        if rc:print('FAILED',label,rc,part);print((part/'stderr').read_text());return rc
    assert inputs=={str(p):sha(p) for p in sources+headers+list((ROOT/'candidate').glob('*')) if p.is_file()}
    result={'status':'compiled_fixture_pass','counts':json.loads((out/'test/stdout').read_text()),'inputs':inputs,'commands':receipts,'limits':['Native fixture links production coordinator/routes/t1 reader; not an OH device test or full bridge link.']}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(out);print(result['counts']);return 0
if __name__=='__main__':sys.exit(main())
