import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r4_recipe_test', HERE / 'restore_recipe.py')
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)


class RecipeTests(unittest.TestCase):
    def exercise(self, history_rc=0, directory_rc=0, execute=True, missing_receipt=False, core_rc=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def file(name, value):
                p = root / name; p.write_text(json.dumps(value)); return {'path': str(p), 'sha256': r.digest(p)}
            origin = file('origin.json', {})
            manifest = file('manifest.json', {'origin_realization': origin, 'executor_sha256': r.digest(HERE/'directory_transaction.py'), 'serial': 'test-serial', 'boot_id': 'test-boot'})
            core = {'realization': origin, 'prepared_manifest': file('prepared.json', {}),
                    'admission': file('admission.json', {}), 'restore_adapter': file('adapter', {}),
                    'execution_cwd': str(root), 'transaction_dir': str(root/'core'), 'execution_receipt': str(root/'core.json')}
            if core_rc is not None:
                core['execution_command'] = file('core-command.json', ['python3', str(HERE.parent/'r2-timeout/exact_realization.py'), '--realization', origin['path'], '--execute', '--out', core['transaction_dir']])
            recipe = file('recipe.json', {'schema': 'exact-directory-completed-restore/v1', 'signed_by': None,
                    'mode': 'complete-existing-success' if core_rc is None else 'restore-then-complete', 'core': core,
                    'supplement': {'manifest': manifest, 'authorization': file('authorization.json', {}), 'hdc': str(root/'never-run-hdc')}})
            out = root / 'out'; calls = []
            def fake(argv, **kwargs):
                calls.append(argv)
                if argv[1].endswith('/r2-timeout/exact_realization.py'):
                    return SimpleNamespace(returncode=core_rc, stdout='core', stderr='')
                if argv[1].endswith('build_binding.py'):
                    if history_rc == 0: (out/'activation-binding.json').write_text('{}')
                    return SimpleNamespace(returncode=history_rc, stdout='history', stderr='')
                self.assertTrue(argv[1].endswith('directory_transaction.py'))
                if directory_rc == 0 and not missing_receipt:
                    p=out/'directory-transaction';p.mkdir()
                    (p/'applied.json').write_text(json.dumps({'executor_rc':0,'state':'CREATED_VERIFIED','manifest_sha256':manifest['sha256']}))
                return SimpleNamespace(returncode=directory_rc, stdout='directory', stderr='')
            args=SimpleNamespace(directory_recipe=Path(recipe['path']), recipe_sha256=recipe['sha256'], out=out, execute=execute)
            with patch.object(r.subprocess, 'run', side_effect=fake): rc=r.run(args)
            receipt=json.loads((out/'recipe-receipt.json').read_text()) if out.exists() else None
            return rc,calls,receipt

    def test_preview_has_zero_execution(self):
        rc,calls,receipt=self.exercise(execute=False)
        self.assertEqual((rc,calls,receipt),(0,[],None))

    def test_history_failure_never_calls_directory(self):
        rc,calls,receipt=self.exercise(history_rc=2)
        self.assertEqual(rc,1); self.assertEqual(len(calls),1); self.assertFalse(receipt['complete'])

    def test_directory_failure_or_missing_receipt_not_complete(self):
        for kwargs in ({'directory_rc':1},{'missing_receipt':True}):
            with self.subTest(kwargs=kwargs):
                rc,calls,receipt=self.exercise(**kwargs)
                self.assertEqual(rc,1); self.assertEqual(len(calls),2); self.assertFalse(receipt['complete'])

    def test_existing_success_then_directory_receipt(self):
        rc,calls,receipt=self.exercise()
        self.assertEqual(rc,0);self.assertEqual(len(calls),2);self.assertTrue(receipt['complete']);self.assertEqual(receipt['reboots'],0)

    def test_core_failure_stops_before_history_and_directory(self):
        rc,calls,receipt=self.exercise(core_rc=124)
        self.assertEqual(rc,1); self.assertEqual(len(calls),1); self.assertFalse(receipt['complete'])

    def test_new_core_success_must_still_complete_directory(self):
        rc,calls,receipt=self.exercise(core_rc=0)
        self.assertEqual(rc,0); self.assertEqual(len(calls),3); self.assertTrue(receipt['complete'])


if __name__ == '__main__': unittest.main()
