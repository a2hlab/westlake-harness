import copy
import unittest
from check_intake import compare


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.required = {'files': [{'stage_path': 'runtime/a.so', 'sha256': 'a'*64,
                                   'required': True, 'size': 42}]}
        self.manifest = {'files': [{'path': 'runtime/a.so', 'sha256': 'a'*64, 'size': 42}]}

    def test_complete(self):
        self.assertTrue(compare(self.required, self.manifest)['complete_declared_runtime'])

    def test_undeclared_dependency_detected(self):
        self.manifest['files'] = []
        result = compare(self.required, self.manifest)
        self.assertFalse(result['complete_declared_runtime'])
        self.assertEqual(result['missing'], ['runtime/a.so'])

    def test_wrong_same_name_binary_detected(self):
        self.manifest['files'][0]['sha256'] = 'b'*64
        self.assertFalse(compare(self.required, self.manifest)['complete_declared_runtime'])

    def test_wrong_size_detected(self):
        self.manifest['files'][0]['size'] = 43
        self.assertFalse(compare(self.required, self.manifest)['complete_declared_runtime'])


if __name__ == '__main__': unittest.main()
