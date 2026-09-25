"""AFTER board release: clone #42 baseline privately and overlay only #44 liblog.

Recorder libart is a separate optional diagnostic stage, never silently baseline.
"""
import argparse
from board42 import *

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board-released', action='store_true', required=True)
    ap.add_argument('--diagnostic', action='store_true')
    args = ap.parse_args()
    before = exclusive()
    origin = R.parent/'aot42/framework-baseline/device-report.json'
    report = json.loads(origin.read_text())
    old = report['stage']
    name = 'diag' if args.diagnostic else 'log44'
    stage = '/data/local/tmp/a2hlab-framework-crash42-'+name
    folder = R/('framework-'+name)
    if folder.exists(): raise ValueError('Never overwrite existing stage evidence')
    folder.mkdir()
    (folder/'before-processes.txt').write_text(before)
    # mkdir intentionally fails if someone already prepared this stage.
    dev('mkdir '+stage+' && cp -a '+old+'/. '+stage+'/', 240)
    replacements = {'liblog.so': A/'out-log44/lib/liblog.so'}
    if args.diagnostic: replacements['libart.so'] = A/'out-crash42/recorder/art/libart.so'
    for filename, path in replacements.items():
        send(path, stage+'/'+filename)
        report['files'][filename] = dict(bytes=path.stat().st_size, sha256=sha(path))
    # Verify every frozen baseline file, not only the changed library.
    measured = hashes([stage+'/'+name for name in report['files']])
    for name, entry in report['files'].items():
        if measured[stage+'/'+name] != entry['sha256']: raise RuntimeError('Mismatch '+name)
    command = report['device_command'].replace(old, stage)
    log = dev(command, 80)
    (folder/'preload.log').write_text(log)
    if 'PRELOAD_PASS' not in log: raise RuntimeError('Derived stage preload did not pass')
    report.update(stage=stage, device_command=command,
                  crash42=dict(origin=str(origin), replacements={k:sha(v) for k,v in replacements.items()},
                               all_file_hashes_verified=True, diagnostic=args.diagnostic))
    (folder/'device-report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(folder/'device-report.json')

if __name__ == '__main__': main()
