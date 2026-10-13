#!/usr/bin/env python3
"""Preview by default; explicit --execute performs only native-HDC batch reads on5ea."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time
import uuid

WS = Path(os.environ['WORKSPACES']).resolve()
MAIN = WS / 'westlake-harness'
SERIAL = '5ea34a4500000000000000001123012c'
MANIFEST = MAIN / 'benchmark/2026-10-09-demo-baseline/demo-manifest.json'
MANIFEST_SHA = '7a2627326cb536bc8b0ee35587827999f448f827a91e22bdc663809767d82933'
HDC = Path('/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc')


def need(ok, text):
    if not ok: raise ValueError(text)


def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def portable(p):
    p = Path(p).resolve()
    return '$WORKSPACES/' + str(p.relative_to(WS)) if p.is_relative_to(WS) else str(p)
def pin(p): return {'path': portable(p), 'sha256': sha(p)}
def save(p, obj): Path(p).write_text(json.dumps(obj, indent=2) + '\n')


def plan(boot_id):
    need(str(uuid.UUID(boot_id)) == boot_id, 'boot UUID required')
    need(sha(MANIFEST) == MANIFEST_SHA, 'canonical manifest drift')
    apps = [a for a in read(MANIFEST)['apps'] if a.get('install') is not False]
    need(len(apps) == len({a['key'] for a in apps}) == 128, 'full128 required')
    commands = [('boot-before', 'cat /proc/sys/kernel/random/boot_id'), ('bundles', 'bm dump -a')]
    for offset in range(0, 128, 16):
        targets = ['/data/app/el1/bundle/public/' + a['package'] + '/android/base.apk' for a in apps[offset:offset+16]]
        commands.append(('apk-%03d' % offset, 'sha256sum ' + ' '.join(shlex.quote(p) for p in targets)))
    commands.append(('boot-after', 'cat /proc/sys/kernel/random/boot_id'))
    return apps, commands


def collect(out, boot_id, runner=subprocess.run):
    apps, commands = plan(boot_id)
    out = Path(out).resolve(); need(not out.exists(), 'fresh output required')
    out.mkdir(parents=True)
    readings, bodies, issues = {}, {}, []
    for name, cmd in commands:
        marker = '__EXACT_READ_RC_' + uuid.uuid4().hex + '__'
        shell = '/system/bin/sh -c ' + shlex.quote(cmd) + '; read_rc=$?; printf "\\n' + marker + '%s\\n" "$read_rc"'
        argv = [str(HDC), '-t', SERIAL, 'shell', shell]
        started = time.time()
        try:
            result = runner(argv, capture_output=True, timeout=180)
            stdout, stderr, rc = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as exc:
            stdout, stderr, rc = exc.stdout or b'', exc.stderr or b'', 124
        finished = time.time()
        (out / (name+'.stdout.txt')).write_bytes(stdout)
        (out / (name+'.stderr.txt')).write_bytes(stderr)
        match = re.search(rb'\n' + marker.encode() + rb'([0-9]+)\s*$', stdout)
        remote_rc = int(match[1]) if match else None
        save(out / (name+'.json'), {'argv':argv, 'rc':rc, 'remote_rc':remote_rc,
                                   'started':started, 'time':finished})
        readings[name] = {k:pin(out / (name+suffix)) for k,suffix in
                         [('receipt','.json'),('stdout','.stdout.txt'),('stderr','.stderr.txt')]}
        bodies[name] = stdout[:match.start()].decode('utf-8', errors='strict').strip() if match else ''
        if rc != 0 or remote_rc != 0 or stderr.strip(): issues.append(name+': transport/remote failure')
        if name == 'boot-before' and bodies[name] != boot_id:
            issues.append('initial boot mismatch'); break
    actual = {}
    for name, text in bodies.items():
        if not name.startswith('apk-'): continue
        for line in text.splitlines():
            m = re.fullmatch(r'([a-f0-9]{64})\s+(/data/app/el1/bundle/public/[A-Za-z0-9_.]+/android/base\.apk)', line)
            if not m: issues.append(name+': malformed raw SHA'); continue
            if m[2] in actual: issues.append(name+': duplicate target')
            actual[m[2]] = m[1]
    rows = []
    for a in apps:
        h = actual.get('/data/app/el1/bundle/public/'+a['package']+'/android/base.apk')
        rows.append({'key':a['key'],'package':a['package'],'expected':a['apk_sha256'],
                     'actual':h,'status':'UNKNOWN' if h is None else ('MATCH' if h==a['apk_sha256'] else 'DRIFT')})
    stable = bodies.get('boot-before') == bodies.get('boot-after') == boot_id
    if not stable: issues.append('bookend boot mismatch/incomplete')
    save(out/'apk-identity.json',{'serial':SERIAL,'boot_id':bodies.get('boot-before'), 'rows':rows,
         'summary':{s:sum(r['status']==s for r in rows) for s in ['MATCH','DRIFT','UNKNOWN']},'board_writes':0})
    if all(k in readings for k in ['boot-before','boot-after','bundles']):
        save(out/'final.json',{'identity':pin(out/'apk-identity.json'),'boot_before':readings['boot-before'],
             'boot_after':readings['boot-after'],'bundles':readings['bundles'],
             'apk_reads':[readings[name] for name,_ in commands if name.startswith('apk-') and name in readings]})
    result={'status':'READONLY_CAPTURE_COMPLETE' if not issues else 'READONLY_CAPTURE_INCOMPLETE',
            'serial':SERIAL,'stable_boot':stable,'issues':issues,'rows':len(rows),'matching':sum(r['status']=='MATCH' for r in rows),
            'collector':pin(Path(__file__)),'manifest':pin(MANIFEST),'device_write_operations':0,
            'admission':False,'raw_readings':readings}
    save(out/'collection.json',result)
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--boot-id',required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--execute',action='store_true');a=ap.parse_args()
    try:
        apps, commands = plan(a.boot_id)
        if not a.execute:
            print(json.dumps({'status':'PREVIEW_NO_DEVICE_CALLS','serial':SERIAL,'expected_boot':a.boot_id,
                'manifest':pin(MANIFEST),'members':len(apps),'out':portable(a.out),'commands':[
                    {'name':n,'argv':[str(HDC),'-t',SERIAL,'shell',cmd]} for n,cmd in commands],
                'note':'Execute adds unique remote-rc wrapper and persists exact actual argv/stdout/stderr/time.'},indent=2))
            return 0
        result=collect(a.out,a.boot_id)
        print(json.dumps({k:result[k] for k in ['status','matching','stable_boot','admission']}))
        return 0 if not result['issues'] and result['matching']==128 else 2
    except (ValueError,OSError,KeyError) as exc:
        print(json.dumps({'status':'REFUSED','error':str(exc)}));return 2


if __name__=='__main__': raise SystemExit(main())
