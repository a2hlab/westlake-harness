"""Fresh baseline, manual screenshot-confirmed consent, no article input, 90s.

VM driver. Only run after outer explicitly releases board. A private framework
stage containing #44 liblog must be prepared first. Does not install the recorder.
"""
import argparse
from board42 import *

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('name')
    ap.add_argument('--framework-report', type=pathlib.Path, required=True)
    ap.add_argument('--reference', type=pathlib.Path, required=True)
    ap.add_argument('--board-released', action='store_true', required=True)
    args = ap.parse_args()
    if not re.fullmatch(r'idle-[0-9]+', args.name): raise ValueError('Use idle-N')
    framework = json.loads(args.framework_report.read_text())
    if not framework['stage'].startswith('/data/local/tmp/a2hlab-framework-crash42-'):
        raise ValueError('Private crash42 framework stage required')
    liblog = A/'out-log44/lib/liblog.so'
    expected = sha(liblog)
    if framework['files']['liblog.so']['sha256'] != expected:
        raise ValueError('Framework report does not contain #44 liblog')
    r = R/args.name
    if r.exists(): raise ValueError('Never overwrite evidence')
    before = exclusive()
    actual = hashes([framework['stage']+'/liblog.so'])
    if next(iter(actual.values())) != expected: raise ValueError('Device liblog differs')
    r.mkdir()
    (r/'preflight.txt').write_text(before)
    config = json.loads(args.reference.read_text())
    cmd = config['argv'].copy()
    for flag, value in [('--serial', S), ('--out', str(r)),
                        ('--framework-report', str(args.framework_report))]:
        cmd[cmd.index(flag)+1] = value
    cmd += ['--runtime-env', 'WESTLAKE_SOURCE_LOG_STDERR=1']
    diagnostic = framework.get('crash42', {}).get('diagnostic', False)
    if diagnostic:
        # Namespace-private tmp already exists and is writable by the child UID.
        cmd += ['--runtime-env', 'WESTLAKE_CRASH42_DIR=/data/local/tmp']
    (r/'launch-config.json').write_text(json.dumps(dict(argv=cmd, liblog_sha256=expected), indent=2))
    result = dict(protocol='fresh baseline; no article input; last consent +90s', diagnostic=diagnostic,
                  consent=[], outcome='not_started', signal_events='pending analysis')
    tracked = {}
    def action(command):
        value = dev(command)
        with (r/'actions.jsonl').open('a') as f:
            f.write(json.dumps(dict(epoch=time.time(), command=command, output=value))+'\n')
        return value
    def state(pid):
        raw = action(f'cat /proc/{pid}/stat 2>/dev/null')
        return raw.rsplit(') ', 1)[1].split()[19] if ') ' in raw else None
    def shot(label):
        path = d['stage']+'/crash42-'+args.name+'-'+label+'.jpeg'
        action('cat /proc/uptime; snapshot_display -f '+shlex.quote(path)+' >/dev/null; cat /proc/uptime')
        recv(path, r/(label+'.jpeg'))
    d = None
    hilog_file = (r/'hilog.txt').open('wb')
    hilog = subprocess.Popen([H, '-t', S, 'shell', 'hilog'], stdout=hilog_file, stderr=subprocess.STDOUT)
    try:
        # Full diagnostics: no grep at collection time, no daemon restart/settings change.
        for label, command in {
            'system-before': 'date; cat /proc/uptime; df -h /data; pidof faultloggerd; cat /system/etc/faultloggerd_config.json',
            'faults-before': 'find /data/log/faultlog -type f',
            'network': 'ifconfig wlan0; ping -c 2 -W 2 1.1.1.1',
        }.items(): (r/(label+'.txt')).write_text(action(command))
        action('aa force-stop org.westlake.imehost')
        exclusive()
        with (r/'probe.log').open('w') as log:
            subprocess.run(cmd, cwd=pathlib.Path.home()/'a2hlab/manifest', stdout=log,
                           stderr=subprocess.STDOUT, check=True)
        d = json.loads((r/'device-report.json').read_text())
        for pid in [d['child'], d['parent']]: tracked[pid] = state(pid)
        pid = d['child']; logpath = d['runtime']+f'/private-tmp/adapter_child_{pid}.stderr'
        (r/'initial-status.txt').write_text(action(f'cat /proc/{pid}/status'))
        (r/'initial-maps.txt').write_text(action(f'cat /proc/{pid}/maps'))
        # Forwarder cleanup uses exact executable ownership, never name-wide kill.
        for value in d.get('touch', {}).get('forwarder_pid', '').split():
            forwarder = int(value)
            if action(f'readlink /proc/{forwarder}/exe').strip() == d['stage']+'/touchfwd':
                action(f'kill {forwarder}')
        action('power-shell wakeup')
        begin = time.monotonic(); last_consent = None; last_maps = 0; last_tree = 0
        result['outcome'] = 'running'
        while True:
            now = time.monotonic()
            live = state(pid)
            stamp = action('cat /proc/uptime').split()[0]
            with (r/'liveness.jsonl').open('a') as f:
                f.write(json.dumps(dict(uptime=float(stamp), starttime=live))+'\n')
            if live != tracked[pid]:
                result.update(outcome='exited', exit_observed_uptime=float(stamp)); break
            if last_consent is not None and now-last_consent >= 90:
                result['outcome'] = 'alive_90s_after_last_consent'; break
            if last_consent is None and now-begin > 240:
                result['outcome'] = 'no_confirmed_consent'; break
            if now-last_maps >= 5:
                (r/f'maps-{int(now-begin):03}.txt').write_text(action(f'cat /proc/{pid}/maps'))
                last_maps = now
            # Stop view-tree probes after consent settles; idle remains idle.
            if (last_consent is None or now-last_consent < 25) and now-last_tree >= 3:
                n = int(action('wc -l < '+logpath).strip())
                action('echo v > /data/local/tmp/noice_tap'); time.sleep(.5)
                tree = action(f'tail -n +{n+1} {logpath}')
                (r/f'view-{int(now-begin):03}.txt').write_text(tree)
                last_tree = now
                if re.search(r'^VT.*"同意[^"]*"', tree, re.M) and (last_consent is None or now-last_consent > 15):
                    index = len(result['consent']); label = 'consent-'+str(index)
                    shot(label); print('CHECK_CONSENT_SCREENSHOT', r/(label+'.jpeg'), flush=True)
                    control = r/(label+'-xy'); deadline = time.monotonic()+120
                    while not control.exists():
                        if time.monotonic() > deadline: raise RuntimeError('Consent confirmation timeout')
                        if state(pid) != tracked[pid]: raise RuntimeError('Exited before confirmed consent')
                        time.sleep(.5)
                    xy = control.read_text().strip()
                    if not re.fullmatch(r'[0-9]+ [0-9]+', xy): raise ValueError('Bad coordinates')
                    event = action('cat /proc/uptime; uinput -T -d '+xy+' -u '+xy+'; cat /proc/uptime')
                    result['consent'].append(event); last_consent = time.monotonic()
                    print('CONSENT', args.name, event, flush=True)
            time.sleep(1)
        shot('final')
    except Exception as error:
        result['error'] = str(error)
        result['outcome'] = 'fixture_error'
        raise
    finally:
        if d is None and (r/'device-report.json').exists():
            d = json.loads((r/'device-report.json').read_text())
            # No PID/starttime recorded: do not guess and kill a reused PID.
        if d:
            for label, path in [('child.stderr', d['runtime']+f'/private-tmp/adapter_child_{d["child"]}.stderr'),
                                ('parent.log', d['stage']+'/parent.log'), ('run.sh', d['runtime']+'/run.sh')]:
                try: recv(path, r/label)
                except Exception as error: (r/(label+'.error')).write_text(str(error))
            if diagnostic:
                paths = action('find '+d['runtime']+'/private-tmp -maxdepth 1 -type f -name "event-*"')
                for path in paths.splitlines():
                    if path.startswith(d['runtime']+'/private-tmp/event-'):
                        try: recv(path, r/'snapshots'/pathlib.Path(path).name)
                        except Exception as error: (r/'snapshot-copy-error.txt').write_text(str(error))
            # Delay for asynchronously generated reports, without keeping test app alive.
            for pid, start in tracked.items():
                if start is not None and state(pid) == start: action(f'kill -9 {pid}')
            for delay in (0, 3, 10):
                time.sleep(delay)
                paths = action(f'find /data/log/faultlog -type f -name "*-{d["child"]}-*"')
                (r/f'fault-paths-{delay}.txt').write_text(paths)
                for path in paths.splitlines():
                    if path.startswith('/'):
                        try: recv(path, r/pathlib.Path(path).name)
                        except Exception as error: (r/'fault-copy-error.txt').write_text(str(error))
            # Refresh after termination/reap so the last signal line is not lost.
            for label, path in [('child.stderr', d['runtime']+f'/private-tmp/adapter_child_{d["child"]}.stderr'),
                                ('parent.log', d['stage']+'/parent.log')]:
                try: recv(path, r/label)
                except Exception as error: (r/(label+'.refresh-error')).write_text(str(error))
            if diagnostic:
                paths = action('find '+d['runtime']+'/private-tmp -maxdepth 1 -type f -name "event-*"')
                for path in paths.splitlines():
                    if path.startswith(d['runtime']+'/private-tmp/event-'):
                        try: recv(path, r/'snapshots'/pathlib.Path(path).name)
                        except Exception as error: (r/'snapshot-refresh-error.txt').write_text(str(error))
        hilog.terminate()
        try: hilog.wait(timeout=5)
        except subprocess.TimeoutExpired: hilog.kill(); hilog.wait()
        hilog_file.close()
        (r/'after-processes.txt').write_text(dev('ps -A -o PID,PPID,NAME'))
        (r/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print('COLLECTED', args.name, result['outcome'], flush=True)

if __name__ == '__main__': main()
