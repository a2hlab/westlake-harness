import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import noice_upgrade as upgrade


HERE = Path(__file__).resolve().parent
ROOTS = ['/data/app/' + prefix + '/' + upgrade.NOICE for prefix in
         ['el1/100/base', 'el2/100/base', 'el1/100/database', 'el2/100/log']]
CONTENT = b'private fixture only'
FILE = ROOTS[1] + '/prefs.txt'
META = {'exists': True, 'dev_inode_uid_gid_mode': '1:2:20010994:20010994:700', 'label': 'u:object_r:appdat:s0'}
METADATA = {root: dict(META) for root in ROOTS}
CONTENTS = {'files': {FILE: dict(sha256=hashlib.sha256(CONTENT).hexdigest(),
                                dev_inode_uid_gid_mode=META['dev_inode_uid_gid_mode'], label=META['label'])}, 'links': {}}


class FakeBatch:
    @staticmethod
    def parse_bundle(text, package):
        return {'queryable': True, 'uid': json.loads(text)['uid']}

    @staticmethod
    def cold_stop(*args):
        return True


class FakeBoard:
    def __init__(self, fault=None):
        self.after = False
        self.fault = fault
        self.calls = []

    def shell(self, command, **kwargs):
        self.calls.append(command)
        if command == 'bm dump -a':
            value = upgrade.NOICE if self.fault != 'missing' else 'org.other.app'
            return 0, 'ID: 100:\n\t' + value
        if command.startswith('bm dump -n '):
            uid = 20010995 if self.after and self.fault == 'uid' else 20010994
            token = 9 if self.after and self.fault == 'token' else 537490247
            return 0, json.dumps({'name': upgrade.NOICE, 'uid': uid, 'gid': 20010994,
                'applicationInfo': {'uid': uid, 'accessTokenId': token, 'accessTokenIdEx': token},
                'reqPermissions': [], 'reqPermissionStates': []})
        if command.startswith('sha256sum '):
            value = upgrade.NOICE_AFTER if self.after else upgrade.NOICE_BEFORE
            return 0, value + '  /data/app/el1/bundle/public/' + upgrade.NOICE + '/android/base.apk'
        if command.startswith('if test -L '):
            root = next(path for path in ROOTS if path in command)
            stat = META['dev_inode_uid_gid_mode']
            if self.after and self.fault == 'metadata':
                stat = '1:3:20010994:20010994:700'
            return 0, 'PRESENT\n' + stat + '\n' + META['label'] + ' ' + root
        if ' -type l ' in command:
            return 0, ''
        if ' -type f ' in command:
            if ROOTS[1] not in command:
                return 0, ''
            digest = '0' * 64 if self.after and self.fault == 'content' else CONTENTS['files'][FILE]['sha256']
            return 0, digest + '  ' + FILE + '\n' + META['dev_inode_uid_gid_mode'] + '\n' + META['label'] + ' ' + FILE
        raise AssertionError('unexpected command: ' + command)

    def receive(self, remote, local):
        original = upgrade.expand(upgrade.read(HERE / 'config.json')['original_apk']['path'])
        if self.fault == 'backup':
            Path(local).write_bytes(b'bad backup')
        else:
            shutil.copyfile(original, local)


class NoiceTests(unittest.TestCase):
    def perform(self, fault=None):
        board = FakeBoard(fault)
        config = copy.deepcopy(upgrade.read(HERE / 'config.json'))
        config['expected_data_metadata'] = METADATA
        config['expected_file_counts'] = {root: int(root == ROOTS[1]) for root in ROOTS}
        if fault == 'count':
            config['expected_file_counts'][ROOTS[1]] = 2
        installs = []
        def installer(config, app, folder):
            installs.append(app['key'])
            if fault == 'install':
                raise RuntimeError('original installer failed')
            board.after = True
            return {'success': True}
        with tempfile.TemporaryDirectory() as directory, patch.object(upgrade, 'private_archive') as archive:
            try:
                result = upgrade.perform(board, FakeBatch(), config, config['operation'], Path(directory),
                                         {upgrade.NOICE}, installer)
                self.assertEqual(0o600, (Path(directory) / 'original-base.apk').stat().st_mode & 0o777)
                return result, installs
            except Exception:
                self.assertTrue(all('uninstall' not in command and 'rm ' not in command for command in board.calls))
                if fault in ['missing', 'backup', 'count']:
                    self.assertEqual([], installs)
                raise

    def test_success_exact_backup_same_uid_token_metadata_contents(self):
        self.assertEqual(({'success': True}, ['fd-noice']), self.perform())

    def test_prewrite_missing_package_and_bad_backup_reject(self):
        for fault in ['missing', 'backup', 'count']:
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                self.perform(fault)

    def test_postwrite_uid_token_metadata_content_reject(self):
        for fault in ['uid', 'token', 'metadata', 'content']:
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                self.perform(fault)

    def test_install_failure_never_uninstalls_or_cleans_data(self):
        with self.assertRaisesRegex(RuntimeError, 'original installer failed'):
            self.perform('install')

    def test_complete_names_reject_unknown_partial_duplicate(self):
        for text in ['', 'ID: 100:', 'ID: 100:\nwrong', 'ID: 100:\n\torg.a\n\torg.a']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                upgrade.names(text)

    def archive(self, directory, fault=None):
        path = Path(directory) / 'data.tar'
        with tarfile.open(path, 'w', format=tarfile.PAX_FORMAT) as archive:
            for root in ROOTS:
                member = tarfile.TarInfo(root.removeprefix('/data/app/'))
                member.type = tarfile.DIRTYPE
                member.uid = member.gid = 20010994
                member.mode = 0o700
                member.pax_headers = {'RHT.security.selinux': META['label']}
                archive.addfile(member)
            member = tarfile.TarInfo(FILE.removeprefix('/data/app/'))
            member.uid = member.gid = 20010994
            member.mode = 0o700
            member.pax_headers = {} if fault == 'label' else {'RHT.security.selinux': META['label']}
            payload = b'wrong' if fault == 'bytes' else CONTENT
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
            if fault == 'foreign':
                archive.addfile(tarfile.TarInfo('../foreign'))
        return path

    def test_archive_readable_matches_bytes_owner_mode_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            upgrade.verify_archive(self.archive(directory), METADATA, CONTENTS)

    def test_archive_wrong_bytes_missing_labels_foreign_reject(self):
        for fault in ['bytes', 'label', 'foreign']:
            with tempfile.TemporaryDirectory() as directory, self.subTest(fault=fault), self.assertRaises(ValueError):
                upgrade.verify_archive(self.archive(directory, fault), METADATA, CONTENTS)

    def test_default_preview_no_device_or_output(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(upgrade.subprocess, 'run', side_effect=AssertionError('device call')):
            out = Path(directory) / 'unused'
            self.assertEqual(0, upgrade.main(['--config', str(HERE / 'config.json'), '--out', str(out)]))
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
