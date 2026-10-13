#!/usr/bin/env python3
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    digest = lambda: hashlib.sha256(source.read_bytes()).hexdigest()
    if digest() != args.source_sha256:
        raise SystemExit('REFUSE source SHA drift')
    sys.dont_write_bytecode = True
    namespace = {'__name__': 'independent_hooks_probe', '__file__': str(source)}
    exec(compile(source.read_text(), str(source), 'exec'), namespace)
    window_type = namespace['Window']
    results = []
    original_run = subprocess.run
    holder = 'outer(codex) 123 2026-10-13T18:00:00+0800'
    subprocess.run = lambda *a, **k: SimpleNamespace(returncode=0, stdout=holder + '\n', stderr='')
    try:
        window = window_type.__new__(window_type)
        window.auth = {'holder': 'outer(codex)'}
        window.program = lambda name: Path('/fixture/lock')
        actual_holder = window.held()
        assert actual_holder == holder
        results.append({'case': 'window_token_to_successor_full_held_receipt', 'passed': True})
    finally:
        subprocess.run = original_run

    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent / '.artifacts') as temporary:
        root = Path(temporary)
        old_boot = '11111111-2222-3333-4444-555555555555'
        new_boot = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        for case in ('ready_trailing_spaces_bound7', 'bound6_refused', 'old_boot_refused', 'ready_wrong_boot_refused'):
            out = root / case
            out.mkdir()
            clock = {'now': 1000}
            namespace['time'] = SimpleNamespace(time=lambda: clock['now'], sleep=lambda seconds: clock.update(now=clock['now'] + seconds))
            window = window_type.__new__(window_type)
            window.out = out
            window.hdc = '/FORBIDDEN_DEVICE_TRANSPORT'
            window.deadline = 1500
            window.auth = {'allow_candidate_boot': True}
            window.inst = SimpleNamespace(ROOT='/fixture/owned')
            boot_calls = []

            def boot_id():
                boot_calls.append(True)
                return old_boot if len(boot_calls) == 1 or case == 'old_boot_refused' else new_boot

            window.boot_id = boot_id
            window.run = lambda *a, **k: ''

            def device(name, _):
                if name.endswith('-ready'):
                    boot = old_boot if case == 'ready_wrong_boot_refused' else new_boot
                    return 'state=READY \nlayers=56 \nboot_id=' + boot + ' \ntrue \nPermissive '
                return 'state=BOUND \nlayers=' + ('6' if case == 'bound6_refused' else '7') + ' \nboot_id=' + new_boot + ' '

            window.device = device
            error = None
            returned = None
            try:
                returned = window.reboot('candidate-boot', True)
            except ValueError as rejected:
                error = str(rejected)
            should_pass = case == 'ready_trailing_spaces_bound7'
            assert (returned == new_boot) == should_pass
            assert (out / 'candidate-boot-result.json').exists() == should_pass
            results.append({'case': case, 'passed': True, 'returned_new_boot': returned == new_boot, 'error': error})

        namespace['time'] = SimpleNamespace(time=lambda: 1000)
        for case in ('final_319_reject', 'restored_hwzz_reject'):
            out = root / case
            transaction = out / 'transaction'
            transaction.mkdir(parents=True)
            (transaction / 'intent-000.json').write_text('{}')
            (transaction / 'transaction.json').write_text('{}')
            (out / 'candidate-boot-intent.json').write_text('{}')
            window = window_type.__new__(window_type)
            window.out = out
            window.auth = {'holder': 'outer(codex)'}
            window.q = {'baseline_smoke': '/fixture/smoke'}
            window.inst = SimpleNamespace(OLD='947' * 21 + '0')
            events = []
            window.action = lambda action: events.append(('action', action))
            window.preboot = lambda tag: events.append(('preboot', tag))
            window.reboot = lambda *a: events.append(('reboot', a))
            window.program = lambda name: Path('/fixture/' + name)

            def verify(tag, runtime, sources):
                events.append(('verify', tag, runtime, sources))
                if case == 'final_319_reject':
                    raise ValueError('full319 mismatch')

            def run(*a, **k):
                events.append(('run', a[0]))
                raise ValueError('restored-hw-zz failed')

            window.verify = verify
            window.run = run
            previous_type = namespace['Window']
            previous_argv = sys.argv
            namespace['Window'] = lambda _: window
            sys.argv = [str(source), 'before-unlock', '--request', '/fixture/request', '--authorization', '/fixture/auth', '--authorization-sha256', 'a' * 64]
            try:
                rc = namespace['main']()
            finally:
                namespace['Window'] = previous_type
                sys.argv = previous_argv
            assert rc == 2 and not (out / 'closed.json').exists()
            assert any(event[0] == 'verify' and event[1:] == ('restored', window.inst.OLD, 'before') for event in events)
            results.append({'case': case, 'passed': True, 'actual_main_exit': rc, 'closed_receipt': False, 'events': events})
    if digest() != args.source_sha256:
        raise SystemExit('REFUSE source changed during review')
    print(json.dumps({'source_sha256': args.source_sha256, 'boundary': 'Actual inherited held/reboot/main/before_unlock functions; device transport, time and phase gates are local fixtures. No board lock operation.', 'device_calls': 0, 'results': results}, indent=2))


if __name__ == '__main__':
    main()
