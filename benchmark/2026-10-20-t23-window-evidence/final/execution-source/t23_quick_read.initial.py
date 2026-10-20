"""Bounded serial read after the existing normal-icon launch; no UI mutations."""
import json, re, shlex, time

EXE = 'a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'

def collect(board, out, boot, context):
    out.mkdir(exist_ok=False)
    result = {'status': 'NOT_REACHED', 'boot': boot, 'device_writes': 0}
    q = shlex.quote
    children = []
    start = time.monotonic()
    deadline = min(start + 45, start + max(0, 1200-(time.time()-context['start'])))
    def read(command, required=True, timeout=5):
        left = deadline-time.monotonic(); assert left > 0, 'quick reader deadline'
        rc, held = board.command(board.lock+['held',board.serial], min(2,left))
        assert rc == 0 and held.strip() == context['holder'], 'exact holder drift'
        left = deadline-time.monotonic(); assert left > 0, 'quick reader deadline'
        command = '(test "$(cat /proc/sys/kernel/random/boot_id)" = '+q(boot)+' || exit 91; '+command+')'
        rc, text = board.raw_shell(command, timeout=min(timeout,left))
        if required: assert rc == 0, ('quick remote rc',rc)
        return rc,text
    try:
        for attempt in range(20):
            if time.monotonic() - start > 30 or time.time() - context['start'] > 1150:
                break
            _, ps = read('ps -A -o PID,PPID,UID,NAME', timeout=5)
            (out / ('ps-%02d.txt' % attempt)).write_text(ps)
            rows = [l.split() for l in ps.splitlines() if len(l.split()) == 4 and l.split()[0].isdigit()]
            parents = {int(r[0]) for r in rows if r[1] == '1' and r[2] == '0' and r[3] == 'appspawn-x'}
            children = [r for r in rows if int(r[1]) in parents and r[2] == '20011300' and r[3] == 'appspawn-x']
            if len(children) == 1:
                break
            time.sleep(1)
        else:
            children = []
        if len(children) != 1:
            result['selection'] = 'no unique child'; return
        pid, parent = map(int, children[0][:2])
        _, stat = read('cat /proc/%d/stat' % pid, timeout=5)
        tail = stat.rsplit(') ', 1)[1].split()
        birth = int(tail[19]); assert int(tail[1]) == parent and tail[0] not in ('Z', 'X')
        result.update(pid=pid, parent=parent, birth=birth)
        guard = (
            'test "$(cat /proc/sys/kernel/random/boot_id)" = '+q(boot)+'; '
            's=$(cat /proc/%d/stat); s=${s##*) }; set -- $s; '%pid+
            'test "$1" != Z; test "$1" != X; test "$2" = %d; test "${20}" = %d; '%(parent,birth)+
            'u=$(sed -n "s/^Uid:[[:space:]]*//p" /proc/%d/status); set -- $u; '%pid+
            'test "$#" = 4; test "$1:$2:$3:$4" = 20011300:20011300:20011300:20011300; '
            'test "$(sed -n "s/^TracerPid:[[:space:]]*//p" /proc/%d/status)" = 0; '%pid+
            'test "$(sha256sum /proc/%d/exe | cut -d\' \' -f1)" = '%pid+EXE)
        script = ('(set -eu; '+guard+'; printf "T23_IDENTITY_BEFORE\n"; '
                  'cat /proc/{p}/stat; readlink /proc/{p}/ns/mnt; '
                  'printf "T23_MAPS\n"; cat /proc/{p}/maps; '
                  'printf "T23_FD2\n"; log=$(readlink /proc/{p}/fd/2); '
                  'printf "%s\n" "$log"; test -f "$log"; test ! -L "$log"; '
                  'printf "T23_LOG_BEFORE\n"; stat -c %d:%i:%s "$log"; '
                  'printf "T23_LOG_TAIL\n"; tail -c 65536 "$log"; '
                  'printf "\nT23_LOG_AFTER\n"; stat -c %d:%i:%s "$log"; '
                  'printf "T23_IDENTITY_AFTER\n"; '.format(p=pid)+guard+
                  '; cat /proc/%d/stat; printf "T23_QUICK_COMPLETE\n")'%pid)
        _, raw = read(script, required=False, timeout=8)
        (out/'quick.raw.txt').write_text(raw)
        result['quick_complete'] = 'T23_QUICK_COMPLETE' in raw.splitlines()
        # A dead child still has useful PID-filtered historical logs. Preserve boot
        # and before/after proc existence; absence is not proof against PID reuse.
        hilog = ('(test "$(cat /proc/sys/kernel/random/boot_id)" = '+q(boot)+' || exit 91; '
                 'printf "T23_HILOG_PROC_BEFORE\n"; cat /proc/{p}/stat; '
                 'printf "T23_HILOG_START\n"; hilog -x -P {p} -z 2000 -L D,I,W,E,F -v epoch; '
                 'rc=$?; printf "T23_HILOG_RC=%s\n" "$rc"; '
                 'printf "T23_HILOG_PROC_AFTER\n"; cat /proc/{p}/stat; '
                 'test "$(cat /proc/sys/kernel/random/boot_id)" = '.format(p=pid)+q(boot)+
                 ' || exit 92; printf "T23_HILOG_COMPLETE\n"; exit "$rc")')
        _, raw = read(hilog, required=False, timeout=8)
        (out/'hilog.raw.txt').write_text(raw)
        result['hilog_complete'] = 'T23_HILOG_COMPLETE' in raw.splitlines()
        result['hilog_remote_rc'] = re.findall(r'^T23_HILOG_RC=(\d+)$', raw, re.M)
        result['status'] = 'CAPTURED_REQUIRES_IDENTITY_AND_TIME_REVIEW'
    except Exception as e:
        result['status'] = 'PARTIAL'; result['error'] = str(e)
        cause = getattr(e, '__cause__', None)
        if cause is not None:
            (out/'timeout.partial.stdout').write_bytes(getattr(cause,'stdout',b'') or b'')
            (out/'timeout.partial.stderr').write_bytes(getattr(cause,'stderr',b'') or b'')
    finally:
        result['elapsed_seconds'] = time.monotonic()-start
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
