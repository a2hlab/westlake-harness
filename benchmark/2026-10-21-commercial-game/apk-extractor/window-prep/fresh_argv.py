#!/usr/bin/env python3
"""Render read-only 5ea argv as JSON. Never execute commands or contact a device."""
import argparse
import json

SERIAL = '5ea34a4500000000000000001123012c'
TARGETS = ['/system/lib64/libinstalls.z.so', '/system/lib64/platformsdk/libinstalls.z.so']


def render(pid=None):
    reads = [
        ('boot-before', 'cat /proc/sys/kernel/random/boot_id'),
        ('processes', 'ps -A -o PID,PPID,UID,NAME'),
        ('mounts', 'cat /proc/mounts'),
        ('aliases', 'set -e; for p in ' + ' '.join(TARGETS) + '; do '
         'echo "FILE $p"; ls -ldZ "$p"; readlink -f "$p"; '
         'stat -c "%d:%i %u:%g %a %h %F" "$p"; sha256sum "$p"; done'),
        ('packages', 'bm dump -a'),
        ('genshin-bundle', 'bm dump -n com.miHoYo.Yuanshen'),
        ('power', 'power-shell dump -s'),
        ('focus', "hidumper -s WindowManagerService -a '-a'"),
        ('hilog-buffers', 'hilog -g'),
        ('hilog-privacy', 'param get hilog.private.on'),
        ('network-kernel', 'cat /proc/net/wireless; cat /proc/net/route'),
        ('boot-after', 'cat /proc/sys/kernel/random/boot_id'),
    ]
    if pid is not None:
        if type(pid) is not int or pid <= 1:
            raise ValueError('fresh positive PID > 1 required')
        reads = [('loader-boot-before', reads[0][1]),
                 ('loader-identity-before', f'cat /proc/{pid}/stat; cat /proc/{pid}/status; '
                  f'readlink /proc/{pid}/exe; readlink /proc/{pid}/ns/mnt; '
                  f'od -An -v -tx1 /proc/{pid}/cmdline'),
                 ('loader-maps', f'cat /proc/{pid}/maps')]
        for index, path in enumerate(TARGETS):
            view = f'/proc/{pid}/root{path}'
            reads.append((f'loader-root-{index}', f'sha256sum {view}; stat -L -c "%d:%i" {view}'))
        reads += [('loader-identity-after', f'cat /proc/{pid}/stat; cat /proc/{pid}/status; '
                   f'readlink /proc/{pid}/exe; readlink /proc/{pid}/ns/mnt'),
                  ('loader-boot-after', 'cat /proc/sys/kernel/random/boot_id')]
    return {'schema': 'g12-readonly-argv/v1', 'executed': False, 'serial': SERIAL,
            'notes': ['HDC is an executable placeholder, resolve explicitly; no shell eval.',
                      'Record each argv/start/end/transport rc/remote rc/stdout/stderr; timeout 15s, no retries.',
                      'Missing PID or identity mismatch is unknown/refuse, never use G06 PID13171.',
                      'Kernel network files do not prove SSID; separately bind outer verified readonly SSID reader.',
                      'No locking or device operation is performed by this renderer.'],
            'commands': [{'id': tag, 'argv': ['$HDC', '-t', SERIAL, 'shell', cmd],
                          'timeout_seconds': 15} for tag, cmd in reads]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, help='fresh observed loader PID; renders phase 2 only')
    args = parser.parse_args()
    print(json.dumps(render(args.pid), indent=2))
