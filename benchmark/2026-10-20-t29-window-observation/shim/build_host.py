#!/usr/bin/env python3
"""Offline only. Actual derived C routing, fixed input pins and persistent logs."""
import argparse
import errno
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

P = Path(__file__).resolve().parent
CASES = ['valid','wrong_caller','wrong_lock','wrong_unlock','wrong_geometry',
         'rgb','unknown','geometry_failure','unmap_failure','flush_failure',
         'alloc_failure','format_refuse','precheck_failure','abort_failure',
         'owner_release_failure','rgbx','rgbx_format0','rgbx_geometry_failure',
         'rgbx_bad_format','rgbx_precheck','rgbx_unmap','rgbx_flush',
         'cache_busy','cache_full','request_failure','map_failure','errno_route',
         'layout_failure','handle_failure','native_convert_failure','request_positive_error']
LOGGER = ['pipe','fd2_rebind','sink_drift','epipe','eintr','short',
          'hot_new','parallel','reserve','total','epochs','long']

def check_failure_fields(case, text):
    """Assertions against actual C dispatch logs; no modeled implementation."""
    table = {
        'request_failure': (3,37,-19,{'Q':'1/1/-19','M':'0/0/0','U':'0/0/0','F':'0/0/0'}),
        'map_failure': (3,46,-5,{'Q':'1/1/0','M':'1/1/-5','U':'0/0/0','F':'0/0/0'}),
        'alloc_failure': (3,48,-12,{'prepare':'1/1/-12','M':'1/1/0','U':'1/1/0','B':'1/1/0','F':'0/0/0'}),
        'format_refuse': (3,48,-22,{'prepare':'1/1/-22','U':'1/1/0','B':'1/1/0','F':'0/0/0'}),
        'rgbx_bad_format': (3,48,-22,{'prepare':'1/1/-22','U':'1/1/0','B':'1/1/0','F':'0/0/0'}),
        'precheck_failure': (4,49,-22,{'conversion':'1/1/-22','U':'1/1/0','B':'1/1/0','F':'0/0/0'}),
        'abort_failure': (4,49,-22,{'conversion':'1/1/-22','U':'1/1/0','B':'1/1/-11','F':'0/0/0'}),
        'rgbx_precheck': (4,49,-22,{'conversion':'1/1/-22','U':'1/1/0','B':'1/1/0','F':'0/0/0'}),
        'unmap_failure': (4,50,-5,{'conversion':'1/1/0','U':'1/1/-5','B':'0/0/0','F':'0/0/0'}),
        'rgbx_unmap': (4,50,-5,{'conversion':'1/1/0','U':'1/1/-5','B':'0/0/0','F':'0/0/0'}),
        'flush_failure': (4,51,-7,{'conversion':'1/1/0','U':'1/1/0','B':'0/0/0','F':'1/1/-7'}),
        'rgbx_flush': (4,51,-7,{'conversion':'1/1/0','U':'1/1/0','B':'0/0/0','F':'1/1/-7'}),
        'cache_busy': (3,32,-16,{'Q':'0/0/0','M':'0/0/0'}),
        'cache_full': (3,32,-28,{'Q':'0/0/0','M':'0/0/0'}),
        'layout_failure': (3,47,-22,{'M':'1/1/0','U':'1/1/0','B':'1/1/0','F':'0/0/0'}),
        'handle_failure': (3,44,-errno.EPROTO,{'H':f'1/1/{-errno.EPROTO}','N':'0/0/0','M':'0/0/0','B':'1/1/0'}),
        'native_convert_failure': (3,45,-6,{'H':'1/1/0','N':'1/1/-6','M':'0/0/0','B':'1/1/0'}),
        'request_positive_error': (3,37,-5,{'Q':'1/1/7','M':'0/0/0'}),
    }
    if case not in table:
        return
    phase,stage,rc,extra = table[case]
    rows = [dict(re.findall(r'(\w+)=([^\s]+)', line)) for line in text.splitlines()
            if line.startswith('[WL-R29]')]
    rows = [r for r in rows if r.get('p') == str(phase) and r.get('stage') == str(stage)]
    assert len(rows) == 1, (case,rows)
    expected = dict(extra, called='1',raw_valid='1',raw=str(rc),
                    rc=str(rc),failure_stage=str(stage))
    if case == 'layout_failure':
        expected.update(called='0',raw_valid='0',raw='0',provider='0')
    if case == 'request_positive_error':
        expected['raw'] = '7'
    for key,value in expected.items():
        assert rows[0].get(key) == value, (case,key,value,rows[0])

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--observer',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    steps = []
    def run(name,argv):
        argv = list(map(str,argv))
        (a.out/(name+'.argv.json')).write_text(json.dumps(argv)+'\n')
        with (a.out/(name+'.stdout')).open('wb') as o, (a.out/(name+'.stderr')).open('wb') as e:
            r = subprocess.run(argv,stdout=o,stderr=e)
        (a.out/(name+'.rc')).write_text(str(r.returncode)+'\n')
        steps.append(dict(name=name,rc=r.returncode))
        print(name,r.returncode,flush=True)
        if r.returncode:
            (a.out/'failure.json').write_text(json.dumps(steps,indent=2)+'\n')
            raise SystemExit(r.returncode)
    for item in json.loads((P/'base-pins.json').read_text()):
        assert sha(a.repo/item['path']) == item['sha256'], item['path']
    pins = {str(f):sha(f) for f in P.rglob('*') if f.suffix in ('.c','.h','.py') and f.is_file()}
    for n,h in [('observer.c','0a31347c0c8499d5109b9ef73c84b1dab42ea78fac58c7ece08a884dc0814521'),
                ('observer.h','d60cf01a30a600348451de6b9b25a86ab5a1a2ff651fa1bddfe04ef6d1cf516b')]:
        assert sha(a.observer/n)==h
        pins[str(a.observer/n)] = h
    run('00-frozen',['python3',a.repo/'scripts/lab/check_frozen.py','--git',a.repo,
                     '--registry',a.repo/'knowledge/frozen/frozen.json'])
    cc = shutil.which('clang')
    assert cc
    base = [cc,'-std=c11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
            '-pthread','-D_GNU_SOURCE=1','-I'+str(P),'-I'+str(P/'derived'),
            '-I'+str(a.observer)]
    run('01-compiler',[cc,'--version'])
    run('10-logger-build',base+[P/'test_observe29.c','-o',a.out/'test_observe29'])
    for case in LOGGER:
        run('11-'+case,[a.out/'test_observe29',case])
    run('20-route-build',base+['-DWL_T27_OBSERVER',P/'test_route.c',
        P/'derived/window_module.c',P/'derived/provider_adapter.c',P/'derived/entry.c',
        P/'rgbx.c',P/'observation.c',P/'observe29.c',a.observer/'observer.c',
        '-o',a.out/'test_route'])
    for case in CASES:
        run('21-'+case,[a.out/'test_route',case])
        text=(a.out/('21-'+case+'.stderr')).read_text()
        assert '[WL-R29]' in text, case
        if case in ('cache_busy','cache_full'):
            assert 'stage=3 ' in text and 'stage=32 ' in text, case
        if case.startswith('wrong_'):
            assert 'oh=0 ' in text and 'stage=2 ' in text, case
        check_failure_fields(case,text)
    run('30-core-build',base+[P/'test_rgbx.c',P/'rgbx.c',P/'observe29.c','-o',a.out/'test_rgbx'])
    run('31-core-test',[a.out/'test_rgbx'])
    run('32-yv12-build',base+[P/'test_yv12.c',P/'rgbx.c',P/'observe29.c','-o',a.out/'test_yv12'])
    run('33-yv12-test',[a.out/'test_yv12'])
    for f,h in pins.items():
        assert sha(Path(f))==h, f
    (a.out/'receipt.json').write_text(json.dumps({
        'status':'HOST_ONLY_PASS','source_inputs':pins,'commands':steps,
        'route_cases':CASES,'logger_cases':LOGGER,'compiler_sha256':sha(Path(cc).resolve()),
        'device_calls':0,'production_status':'PENDING_CC_FINAL_PINS_AND_BRIDGE_FIRST'
    },indent=2)+'\n')

if __name__ == '__main__':
    main()
