import unittest
from pathlib import Path

import audit


class AuditTests(unittest.TestCase):
    def test_matching_object(self):
        self.assertEqual(audit.ownership({'key': 'one', 'pkg': 'p.one'},
            {'key': 'one', 'package': 'p.one'}, 'one'), [])

    def test_wrong_object_fields(self):
        self.assertEqual(audit.ownership({'key': 'one', 'pkg': 'p.one'},
            {'key': 'two', 'package': 'p.two'}, 'two'), ['directory', 'record.key', 'record.package'])

    def test_missing_same_package_key(self):
        result = audit.coverage([{'key': 'fd-noice', 'pkg': 'same'}], ['fd-noice', 'noice'])
        self.assertEqual(result['missing'], ['noice'])
        self.assertEqual(result['unique_keys'], 1)

    def test_duplicate_and_extra_keys(self):
        result = audit.coverage([{'key': 'one'}, {'key': 'one'}, {'key': 'two'}], ['one'])
        self.assertEqual(result['duplicates'], {'one': 2})
        self.assertEqual(result['extra'], ['two'])

    def test_exact_metadata(self):
        original = dict(display_name_zh='名称', display_name_en='Name', purpose_zh='用途。',
            package='p.one', category='工具', version='1', source='F-Droid')
        row = dict(key='one', name='名称', en='Name', purpose='用途。', pkg='p.one',
            cat='工具', ver='1', source='F-Droid')
        self.assertEqual(audit.metadata_diffs(row, original), [])
        row['purpose'] = '用途'
        self.assertEqual(audit.metadata_diffs(row, original)[0]['field'], 'purpose')

    def test_card_pair_swap(self):
        result = audit.pair_mismatches([('A', 'purpose B'), ('B', 'purpose A')],
            [('A', 'purpose A'), ('B', 'purpose B')])
        self.assertEqual(len(result['missing']), 2)
        self.assertEqual(len(result['extra']), 2)

    def test_shortened_name_is_not_exact(self):
        self.assertTrue(audit.pair_mismatches([('Noice', 'purpose')],
            [('Noice：自然平静的噪音', 'purpose')])['missing'])

    def test_signed_path_not_just_same_key(self):
        original = dict(screenshot_reference='/private/tmp/reference.png', signoff_path='signed', signed_scope='lit')
        allowed = {('one', '/private/tmp/signed.png'): ['signed']}
        self.assertEqual(audit.signed_membership('one', Path('/private/tmp/other.png'), allowed, original), [])
        self.assertEqual(audit.signed_membership('one', Path('/private/tmp/signed.png'), allowed, original), ['signed'])
        self.assertTrue(audit.signed_membership('one', audit.path(original['screenshot_reference']), allowed, original))

    def test_portable_preserves_sibling_worktree(self):
        actual = audit.portable(str(audit.WORKSPACES / 'westlake-harness-u7-executor/run'))
        self.assertEqual(actual, '$WORKSPACES/westlake-harness-u7-executor/run')
        self.assertEqual(audit.portable({str(audit.WORKSPACES / 'file'): 'hash'}), {'$WORKSPACES/file': 'hash'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
