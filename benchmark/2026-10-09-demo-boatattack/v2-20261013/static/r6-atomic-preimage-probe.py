#!/usr/bin/env python3
import argparse
import hashlib
import json
import shlex
from pathlib import Path
from types import SimpleNamespace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    text = source.read_text()
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != args.source_sha256:
        raise SystemExit('REFUSE: source SHA drift')
    namespace = {'__name__': 'independent_atomic_probe', '__file__': str(source)}
    exec(compile(text, str(source), 'exec'), namespace)
    metadata = {'mode': '755', 'uid': 0, 'gid': 0, 'label': 'u:object_r:system_lib_file:s0'}
    row = {
        'target': '/data/fixture/runtime.so',
        'source': '/private/tmp/fixture-candidate',
        'sha256': 'c' * 64,
        'before': {'exists': True, 'sha256': 'a' * 64, **metadata},
        'after': metadata,
    }

    class FakeDevice:
        def __init__(self):
            self.target = {'exists': True, 'sha256': 'f' * 64, **metadata}
            self.calls = []

        def probe(self, path):
            if '.successor-' in path:
                return {'exists': True, 'sha256': row['sha256'], **metadata}
            return dict(self.target)

        def send(self, *arguments):
            self.calls.append(('send', arguments))

        def shell(self, name, script):
            self.calls.append((name, script))
            if name == 'atomic-replace':
                self.target = {'exists': True, 'sha256': row['sha256'], **metadata}
            return ''

    def equal(actual_value, expected):
        return all(actual_value.get(key) == value for key, value in expected.items())

    core = SimpleNamespace(q=shlex.quote, resolve=lambda value: Path(value), equal=equal)
    device = FakeDevice()
    error = None
    try:
        namespace['atomic_place'](core, device, row)
    except (ValueError, KeyError, TypeError, OSError) as rejected:
        error = str(rejected)
    print(json.dumps({
        'source_sha256': actual,
        'case': 'post-fresh-foreign-preimage-before-atomic-place',
        'declared_before_sha256': 'a' * 64,
        'observed_foreign_sha256': 'f' * 64,
        'error': error,
        'atomic_replace_executed': any(call[0] == 'atomic-replace' for call in device.calls),
        'target_after_sha256': device.target['sha256'],
        'device_calls': 0,
    }, indent=2))


if __name__ == '__main__':
    main()
