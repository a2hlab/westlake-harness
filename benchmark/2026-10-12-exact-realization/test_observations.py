"""Temporary synthetic raw evidence only; no real process or device invocation."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import observations as o


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-exact-observation-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.expected = {'serial': '5cd1e3dd00000000000000000923012c',
                         'boot_id': '43bc3915-04bd-42ca-895e-26e8292911fa',
                         'host_uid': 20011300, 'host_gid': 20011300,
                         'control_root': '/data/westlake-demo/toutiao/recovery-attempts/synthetic-only',
                         'window_id': None}

    def fixture(self, phase='placement'):
        expected = copy.deepcopy(self.expected)
        pid, birth = 4344, 918273
        if phase == 'running':
            expected['window_id'] = 33
        data = {'schema': o.SCHEMA, 'serial': expected['serial'],
                'boot_before': expected['boot_id'], 'boot_after': expected['boot_id'],
                'host_uid': expected['host_uid'], 'host_gid': expected['host_gid'],
                'synthetic': True, 'readings': {}}
        raw = {'boot_before': expected['boot_id'] + '\n', 'boot_after': expected['boot_id'] + '\n',
               'host_owner': '20011300:20011300\n', 'host_hap': o.HAP_SHA + '  ' + o.HAP_PATH + '\n'}
        if phase == 'running':
            data.update(host_pid=pid, host_birth=birth, window_id=33)
            raw.update(host_status='Name:\timehost\nPid:\t4344\nTgid:\t4344\nUid:\t20011300\t20011300\t20011300\t20011300\nGid:\t20011300\t20011300\t20011300\t20011300\n',
                       host_stat='4344 (ime host) S ' + ' '.join(['0'] * 18 + [str(birth)] + ['0'] * 5) + '\n',
                       host_cmdline='org.westlake.imehost\0',
                       window_dump='WindowName DisplayId Pid WinId Type Mode Flag ZOrd Orientation\nimehost0 0 4344 33 1 1 0 101 0 [ 0 0 1200 1920 ]\n')
        for kind, command in o.commands(phase, pid if phase == 'running' else None).items():
            file = self.root / (kind + '.raw')
            file.write_bytes(raw[kind].encode())
            data['readings'][kind] = {'command': command, 'transport_rc': 0, 'remote_rc': 0,
                                      'stdout': {'path': file.name, 'sha256': o.digest(file)}}
        return expected, data

    def commit(self, data):
        path = self.root / 'observation.json'
        path.write_text(json.dumps(data))
        return {'path': path.name, 'sha256': o.digest(path)}

    def replace_raw(self, data, kind, text):
        file = self.root / data['readings'][kind]['stdout']['path']
        file.write_bytes(text if isinstance(text, bytes) else text.encode())
        data['readings'][kind]['stdout']['sha256'] = o.digest(file)

    def validate(self, expected, data, phase='placement'):
        return o.validate(self.commit(data), self.root, expected, phase)

    def test_placement_no_host_or_window(self):
        expected, data = self.fixture()
        result = self.validate(expected, data)
        self.assertIsNone(result['window_id'])
        self.assertIsNone(result['host_pid'])
        self.assertTrue(result['synthetic'])
        self.assertEqual(result['device_calls'], 0)
        self.assertEqual(set(result['readings']), {'boot_before', 'boot_after', 'host_owner', 'host_hap'})

    def test_running_raw_identity_matches(self):
        expected, data = self.fixture('running')
        result = self.validate(expected, data, 'running')
        self.assertEqual((result['host_pid'], result['host_birth'], result['window_id']), (4344, 918273, 33))
        expected.update(host_pid=4344, host_birth=918273)
        self.validate(expected, data, 'running')

    def test_pin_and_raw_drift_reject(self):
        expected, data = self.fixture()
        ref = self.commit(data)
        (self.root / 'observation.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'SHA drift'):
            o.validate(ref, self.root, expected, 'placement')
        expected, data = self.fixture()
        (self.root / 'host_owner.raw').write_text('0:0')
        with self.assertRaisesRegex(ValueError, 'SHA drift'):
            self.validate(expected, data)

    def test_stale_boot_foreign_serial_and_wrong_hap_reject(self):
        for variant in ('serial', 'claimed_boot', 'raw_boot', 'hap', 'owner'):
            with self.subTest(variant=variant):
                expected, data = self.fixture()
                if variant == 'serial':
                    data['serial'] = '61b0657200000000000000000324012c'
                elif variant == 'claimed_boot':
                    data['boot_after'] = '11111111-1111-1111-1111-111111111111'
                elif variant == 'raw_boot':
                    self.replace_raw(data, 'boot_after', '11111111-1111-1111-1111-111111111111\n')
                elif variant == 'hap':
                    self.replace_raw(data, 'host_hap', '0' * 64 + '  ' + o.HAP_PATH)
                else:
                    self.replace_raw(data, 'host_owner', '20011300:20011206\n')
                with self.assertRaises(ValueError):
                    self.validate(expected, data)

    def test_command_and_transport_status_fail_closed(self):
        for variant in ('command', 'transport_rc', 'remote_rc', 'boolean_rc', 'extra', 'missing'):
            with self.subTest(variant=variant):
                expected, data = self.fixture()
                if variant == 'command':
                    data['readings']['host_owner']['command'] += '; echo unrelated'
                elif variant == 'boolean_rc':
                    data['readings']['host_owner']['transport_rc'] = False
                elif variant in ('transport_rc', 'remote_rc'):
                    data['readings']['host_owner'][variant] = 7
                elif variant == 'extra':
                    data['readings']['run_sh'] = data['readings']['host_owner']
                else:
                    del data['readings']['host_hap']
                with self.assertRaises(ValueError):
                    self.validate(expected, data)

    def test_running_rejects_ambiguous_hidden_foreign_and_self_reported_window(self):
        for variant in ('duplicate', 'hidden', 'foreign_pid', 'wrong_wid', 'run_sh_command', 'missing_header'):
            with self.subTest(variant=variant):
                expected, data = self.fixture('running')
                text = (self.root / 'window_dump.raw').read_text()
                if variant == 'duplicate':
                    text += 'imehost0 0 4344 34 1 1 0 101 0\n'
                elif variant == 'hidden':
                    text = text.replace('0 101 0', '0 -1 0')
                elif variant == 'foreign_pid':
                    text = text.replace('4344 33', '4345 33')
                elif variant == 'wrong_wid':
                    text = text.replace('4344 33', '4344 34')
                elif variant == 'run_sh_command':
                    data['readings']['window_dump']['command'] = 'cat /tmp/run.sh'
                else:
                    text = text.split('\n', 1)[1]
                self.replace_raw(data, 'window_dump', text)
                with self.assertRaises(ValueError):
                    self.validate(expected, data, 'running')

    def test_running_proc_birth_uid_gid_and_cmdline_are_independent(self):
        for kind, replacement in [('host_status', 'Name: fake\nPid: 4344\nTgid: 4344\nUid: 0 0 0 0\nGid: 20011300 20011300 20011300 20011300\n'),
                                  ('host_stat', '4344 (imehost) S ' + ' '.join(['0'] * 18 + ['918274'])),
                                  ('host_cmdline', 'org.westlake.imehost:child\0')]:
            with self.subTest(kind=kind):
                expected, data = self.fixture('running')
                self.replace_raw(data, kind, replacement)
                with self.assertRaises(ValueError):
                    self.validate(expected, data, 'running')
        expected, data = self.fixture('running')
        expected['host_birth'] = 1
        with self.assertRaisesRegex(ValueError, 'expected host_birth'):
            self.validate(expected, data, 'running')

    def test_duplicate_json_and_placement_live_claim_reject(self):
        expected, data = self.fixture()
        data['window_id'] = 33
        with self.assertRaisesRegex(ValueError, 'placement'):
            self.validate(expected, data)
        expected, data = self.fixture()
        ref = self.commit(data)
        file = self.root / ref['path']
        file.write_text(file.read_text().replace('"schema":', '"serial": "fake", "schema":', 1))
        ref['sha256'] = o.digest(file)
        with self.assertRaisesRegex(ValueError, 'duplicate JSON field'):
            o.validate(ref, self.root, expected, 'placement')


if __name__ == '__main__':
    unittest.main(verbosity=2)
