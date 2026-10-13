"""Strict read-only presence extension; original frozen Reader is unchanged."""
import os
from pathlib import Path
import re
import shlex
import subprocess
import uuid

PACKAGE = 'com.Unity3d.BoatAttackDay'


def decode(returncode, stdout, stderr, marker):
    match = re.search(r'\n' + re.escape(marker) + r'([0-9]+)\s*$', stdout)
    if returncode or stderr or not match or match[1] != '0':
        raise ValueError('presence transport/remote/permission failure')
    return stdout[:match.start()].strip()


def parse_metadata(text, expected):
    rows = {}
    for line in text.splitlines():
        fields = line.split('|')
        if len(fields) != 5:
            raise ValueError('presence metadata malformed')
        target, mode, uid, gid, label = fields
        if target not in expected or target in rows or not re.fullmatch('[0-7]{3,4}', mode) or not uid.isdecimal() or not gid.isdecimal() or not re.fullmatch(r'u:object_r:[A-Za-z0-9_]+:s0', label):
            raise ValueError('presence metadata unknown/duplicate')
        rows[target] = dict(mode=mode, uid=int(uid), gid=int(gid), label=label)
    if rows != expected:
        raise ValueError('presence metadata missing/drift')
    return rows


def with_presence(base):
    class Reader(base):
        def _presence_read(self, name, command):
            marker = '__BOAT_PRESENCE_RC_' + uuid.uuid4().hex + '__'
            script = '/system/bin/sh -c ' + shlex.quote(command) + '; rc=$?; printf "\\n' + marker + '%s\\n" "$rc"'
            ws = Path(os.environ.get('WORKSPACES', str(Path(__file__).resolve().parents[5])))
            result = subprocess.run(['bash', str(ws / 'westlake-inputs/tools/hdc_mac.sh'),
                                     '-t', self.serial, 'shell', script],
                                    capture_output=True, text=True, timeout=90)
            self.n += 1
            prefix = self.out / ('presence-%03d-%s' % (self.n, name))
            prefix.with_suffix('.stdout.txt').write_text(result.stdout)
            prefix.with_suffix('.stderr.txt').write_text(result.stderr)
            return decode(result.returncode, result.stdout, result.stderr, marker)

        def bundle(self):
            return self._presence_read('bundle', 'bm dump -n ' + PACKAGE)

        def verify_metadata(self, files, directories):
            for kind, inventory in [('f', files), ('d', directories)]:
                paths = list(inventory)
                for offset in range(0, len(paths), 24):
                    group = paths[offset:offset + 24]
                    for path in group:
                        if not re.fullmatch(r'/(system|data)/[A-Za-z0-9_./+-]+', path) or '..' in path.split('/'):
                            raise ValueError('unsafe presence path')
                    command = 'set -eu; for p in ' + ' '.join(shlex.quote(p) for p in group) + '; do '
                    command += 'walk="$p"; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done; '
                    command += 'test -' + kind + ' "$p"; stat -c \'%n|%a|%u|%g|%C\' "$p"; done'
                    text = self._presence_read('metadata', command)
                    parse_metadata(text, {path: inventory[path] for path in group})
    return Reader
