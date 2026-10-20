#!/usr/bin/env python3
"""Offline tests for T16. `complete()` is a fully-valid admission exercised with files=False (no real .so
needed) for the structural gates; a separate files=True case proves local-byte refusal. `base()` is the
MINIMAL admission base5's probe consumes (it must be REFUSED). An optional reuse-structure check and a
Guard-argv whitelist check run when the pinned diagnostic-r13 dir is reachable (set T16_R13_DIR)."""
import copy, os, sys, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t16_core as C
from t16_core import t16_validate, Refuse

FORBID_61B = '61b0657200000000000000000324012c'


def base():
    """MINIMAL admission used by base5's probe. Deliberately omits android/bridge/hwui modules, tool paths,
    exe pins, etc. — my tightened validate REFUSES it; the probe's no-op case asserts that refusal."""
    now = time.time()
    return {
        'schema': 't16-admission-v1', 'execution_enabled': True, 'approved_by': 'outer(codex)',
        'serial': C.SERIAL, 'created_at': now, 'expires_at': now + 600,
        'host': {'sha256': C.HOST_SHA}, 'server': {'sha256': C.SERVER_SHA, 'pid': 50000, 'birth': 9000},
        'require_hardware_breakpoint': True, 'hardware_explicit': True,
        'no_software_fallback': True, 'no_stepout': True, 'no_expr': True,
        'holder': '5cd1e3dd... 7001 2026-10-20T08:30:00+0800',
        'identity': {'boot': 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', 'parent': 22000, 'parent_birth': 1,
                     'parent_uid': 0, 'child': 22100, 'child_birth': 2, 'uid': C.HOST_UID,
                     'fresh_profile': True, 'mnt': 'mnt:[4026541000]'},
        'modules': {'player': {'sha256': C.PLAYER_5CD}, 'shim': {'sha256': C.SHIM}},
        'addresses': [{'role': 'android', 'slot': 0x472688, 'expected_elf': 0x3b9c, 'pc': 0x3bd4},
                      {'role': 'shim', 'slot': 0x472490, 'expected_elf': 0x5e48, 'pc': 0x5e48}],
        'addresses_player_sha': C.PLAYER_5CD, 'player_got_rederived': True,
        'observed_fields': ['magic', 'tag', 'handle', 'winner_module'],
    }


def _mod(pin, inode):
    return {'sha256': pin, 'device': 64, 'inode': inode, 'remote_path': '/data/app/t16/x.so',
            'local_path': '/dev/null'}


def complete():
    """A FULLY valid admission: complete R13 module set, exe/UID pins, tool sha fields, exact triples,
    player = the REA-pinned 0b4d95c5. Exercised with files=False (no real pinned .so exists in tests)."""
    a = base()
    a['hdc'] = {'sha256': '1' * 64, 'path': '/dev/null'}
    a['lock_script'] = {'sha256': '2' * 64, 'path': '/dev/null'}
    a['server']['uid'] = 0   # independent lldb-server runs as root (matches real diagnostic-r13 admissions)
    a['identity']['parent_exe_sha256'] = C.EXE_SHA
    a['identity']['child_exe_sha256'] = C.EXE_SHA
    a['modules'] = {'player': _mod(C.PLAYER_R13, 11), 'android': _mod(C.ANDROID, 12),
                    'shim': _mod(C.SHIM, 13), 'bridge': _mod(C.BRIDGE, 14), 'hwui': _mod(C.HWUI, 15)}
    a.pop('addresses_player_sha', None)
    a.pop('player_got_rederived', None)
    return a


class Admission(unittest.TestCase):
    def test_accept_complete(self):
        self.assertEqual(t16_validate(complete(), files=False)['serial'], C.SERIAL)

    def test_base_minimal_is_refused(self):
        # base5's probe no-op case: the minimal fixture must NOT pass (missing complete module roles).
        with self.assertRaises(Refuse):
            t16_validate(base(), files=False)

    def _rej(self, mut, why):
        a = copy.deepcopy(complete()); mut(a)
        with self.assertRaises(Refuse, msg='ACCEPTED bad: ' + why):
            t16_validate(a, files=False)

    def test_rejects(self):
        self._rej(lambda a: a['server'].update(sha256=C.FORBIDDEN_SERVER), 'old incompatible server d6d9a233')
        self._rej(lambda a: a['host'].update(sha256='0' * 64), 'wrong host')
        self._rej(lambda a: a['server'].update(uid=-1), 'server uid negative (uid=0 root is allowed)')
        self._rej(lambda a: a['server'].update(pid=a['identity']['child']), 'server pid == business child pid')
        self._rej(lambda a: a['server'].update(pid=a['identity']['parent']), 'server pid == business parent pid')
        self._rej(lambda a: a['identity'].update(boot=C.HIST['boot']), 'historical boot 0525')
        self._rej(lambda a: a['identity'].update(parent=19163), 'historical parent 19163')
        self._rej(lambda a: a['identity'].update(child=1601), 'historical child 1601')
        self._rej(lambda a: a['identity'].update(uid=20011206), 'wrong host uid (61b)')
        self._rej(lambda a: a['identity'].update(parent_uid=1000), 'parent uid not 0')
        self._rej(lambda a: a['identity'].update(parent_exe_sha256='0' * 64), 'parent exe not EXE_SHA (hex only)')
        self._rej(lambda a: a['identity'].update(child_exe_sha256='0' * 64), 'child exe not EXE_SHA (hex only)')
        self._rej(lambda a: a['identity'].update(fresh_profile=False), 'not fresh profile')
        self._rej(lambda a: a['identity'].pop('mnt'), 'missing mnt ns')
        self._rej(lambda a: a.update(require_hardware_breakpoint=False), 'software bp allowed')
        self._rej(lambda a: a.update(no_stepout=False), 'stepout allowed')
        self._rej(lambda a: a['modules'].pop('android'), 'missing android module (incomplete roles)')
        self._rej(lambda a: a['modules'].pop('bridge'), 'missing bridge module (incomplete roles)')
        self._rej(lambda a: a['modules']['shim'].update(sha256='0' * 64), 'wrong shim pin')
        self._rej(lambda a: a['modules']['android'].pop('inode'), 'module missing inode')
        self._rej(lambda a: a['modules']['player'].update(sha256=C.PLAYER_5CD), 'player b427614d has no pinned triples')
        self._rej(lambda a: a['addresses'][0].update(pc=4), 'android pc=4 (not the proven 0x3bd4)')
        self._rej(lambda a: a['addresses'][0].update(slot=8), 'android GOT slot=8 (not 0x472688)')
        self._rej(lambda a: a['addresses'][1].update(pc=0x9999), 'shim lock pc != 0x5e48')
        self._rej(lambda a: a['addresses'].append({'role': 'android', 'slot': 0x472688, 'expected_elf': 0x3b9c, 'pc': 0x3bd4}),
                  '3 address rows (duplicate android must not set-mask)')
        self._rej(lambda a: a['addresses'].__setitem__(1, {'role': 'android', 'slot': 0x472688, 'expected_elf': 0x3b9c, 'pc': 0x3bd4}),
                  'duplicate android role, shim role missing')
        self._rej(lambda a: a.update(observed_fields=['magic', 'usage', 'virAddr']), 'out-of-scope fields')
        self._rej(lambda a: a.update(installs_r15=True), 'R15 masquerade')
        self._rej(lambda a: a.update(schema='r13-admission-v1'), 'wrong schema (not 61b/R13)')
        self._rej(lambda a: a.update(serial=FORBID_61B), '61b serial refused')
        self._rej(lambda a: a.update(created_at=time.time() - 400), 'stale')
        self._rej(lambda a: a.update(max_seconds=600), 'budget override')

    def test_local_bytes_verified(self):
        # files=True: a declared-correct sha256 with a nonexistent path must be REFUSED (base5 pt.3).
        a = complete(); a['host']['path'] = '/nonexistent/t16-fixture-host'
        with self.assertRaises(Refuse):
            t16_validate(a, files=True)
        # wrong actual content under an existing path must also be REFUSED.
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b'not the pinned bytes'); tf.flush()
            b = complete(); b['host']['path'] = tf.name
            with self.assertRaises(Refuse):
                t16_validate(b, files=True)

    def test_preview_zero_device(self):
        p = C.plan_preview()
        self.assertEqual(p['device_calls'], 0)
        self.assertEqual(p['execute'], False)
        self.assertEqual(p['playback'], 'UNKNOWN_NOT_TESTED')
        self.assertEqual(p['shim_lock_pc'], '0x5e48')


def _r13_dir():
    r13 = os.environ.get('T16_R13_DIR')
    return r13 if r13 and Path(r13).is_dir() else None


class ReuseStructure(unittest.TestCase):
    def test_subclass_only_overrides_prepare_and_schema(self):
        r13 = _r13_dir()
        if not r13:
            self.skipTest('diagnostic-r13 dir not provided (set T16_R13_DIR); reuse verified at execute time')
        import t16_observer
        r13core, r13observer = t16_observer.load_r13(r13)   # SHA-verifies the pinned reuse base
        T16 = t16_observer.make_session_class(r13observer)
        self.assertTrue(issubclass(T16, r13observer.Session))
        overridden = {n for n in vars(T16) if not n.startswith('__') or n == '__init__'}
        self.assertEqual(overridden, {'__init__', 'prepare_addresses'})
        for m in ('add_bp', 'on_hit', 'cleanup', 'run', 'wait_stop', 'resume', 'module', 'read'):
            self.assertIs(getattr(T16, m), getattr(r13observer.Session, m), m + ' must be the reused R13 method')


class GuardArgv(unittest.TestCase):
    def test_every_device_argv_carries_5cd_never_61b(self):
        """Blocker 1: the injected 5cd Guard (isolated private R13 identity module) must emit 5cd in every
        device command argv (whitelist) and never 61b, while the public `identity` stays 61b. Mirrors
        base5's probe but exercises the INJECTED guard_factory, not the untouched public identity.Guard."""
        r13 = _r13_dir()
        if not r13:
            self.skipTest('set T16_R13_DIR to run the Guard-argv whitelist check')
        import t16_identity, t16_observer
        Guard = t16_observer.make_guard(r13)                 # SHA-verifies R13 + binds 5cd on a private module
        priv = sys.modules[t16_identity._PRIVATE_NAME]
        self.assertEqual(priv.SERIAL, C.SERIAL)
        # the public identity module (loaded by R13 observer) must be untouched (still 61b)
        t16_observer.load_r13(r13)
        import identity as public_identity
        self.assertEqual(public_identity.SERIAL, FORBID_61B)
        self.assertIsNot(public_identity, priv)

        v = complete()
        v['lock_script'] = {'path': '/fixture/lock'}
        v['hdc'] = {'path': '/fixture/hdc'}
        for role, mod in v['modules'].items():
            mod['remote_path'] = '/data/fixture/' + role
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if len(calls) == 1:
                return type('Reply', (), {'returncode': 0, 'stdout': v['holder'].encode(), 'stderr': b''})()
            raise RuntimeError('FIXTURE_STOP_BEFORE_DEVICE')

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(priv.subprocess, 'run', fake_run):
                with self.assertRaises(Exception):
                    Guard(v, directory, time.monotonic() + 120).capture('pre-connect')
        self.assertTrue(calls, 'Guard.capture issued no device command')
        for argv in calls:
            self.assertIn(C.SERIAL, argv, 'device argv missing 5cd serial: ' + repr(argv))
            self.assertNotIn(FORBID_61B, argv, '61b serial leaked into device argv: ' + repr(argv))


if __name__ == '__main__':
    unittest.main(verbosity=2)
