"""Offline-only successor candidate; never installed into the running round.

Retains the pinned original transport, decoder, parser, batch size and guards.
Only the dirname operation within each ancestor walk becomes shell builtins.
"""
import hashlib
import importlib.util
from pathlib import Path
import re
import shlex
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / 'benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-identity-f28-61b/presence_reader.py'
ORIGINAL_SHA256 = '7059cc45215f3f260402763fb6e8ac24994a3913614d6c6d635335f61df898f6'
if hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() != ORIGINAL_SHA256:
    raise ValueError('original presence helper pin drift')
spec = importlib.util.spec_from_file_location('pinned_original_presence_lowfork_base', ORIGINAL)
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)

# Operates on the existing loop variable, without command substitution/fork.
# Slash-only paths and trailing/repeated separators match dirname semantics.
PARENT_STEP = '''case "$walk" in
  *[!/]*)
    while [ "${walk%/}" != "$walk" ]; do walk="${walk%/}"; done
    walk="${walk%/*}"
    while [ "${walk%/}" != "$walk" ]; do walk="${walk%/}"; done
    [ -n "$walk" ] || walk=/
    ;;
  *) walk=/ ;;
esac'''


def with_presence(base):
    class Reader(original.with_presence(base)):
        def verify_metadata(self, files, directories):
            for kind, inventory in [('f', files), ('d', directories)]:
                paths = list(inventory)
                for offset in range(0, len(paths), 24):
                    group = paths[offset:offset + 24]
                    for path in group:
                        if not re.fullmatch(r'/(system|data)/[A-Za-z0-9_./+-]+', path) or '..' in path.split('/'):
                            raise ValueError('unsafe presence path')
                    command = 'set -eu; for p in ' + ' '.join(shlex.quote(p) for p in group) + '; do '
                    command += 'walk="$p"; while [ "$walk" != / ]; do test ! -L "$walk"; ' + PARENT_STEP + '; done; '
                    command += 'test -' + kind + ' "$p"; stat -c \'%n|%a|%u|%g|%C\' "$p"; done'
                    text = self._presence_read('metadata', command)
                    original.parse_metadata(text, {path: inventory[path] for path in group})
    return Reader
