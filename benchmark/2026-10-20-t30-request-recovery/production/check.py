#!/usr/bin/env python3
"""Preparation-only checks: no compiler, linker or device invocation."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('t30_production', HERE / 'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

class Preparation(unittest.TestCase):
    def test_default_preview_never_runs_commands(self):
        with patch.object(build.subprocess, 'run', side_effect=AssertionError('execution forbidden')), io.StringIO() as output, contextlib.redirect_stdout(output):
            build.main([])
            result = json.loads(output.getvalue())
        self.assertEqual(result['status'], 'PREVIEW_ONLY')
        self.assertEqual(result['compile_units'], ['window_module.c', 'provider_adapter.c'])
        self.assertEqual(result['compiler_calls'], 0)

    def test_execute_missing_freeze_refuses_before_command(self):
        with patch.object(build.subprocess, 'run', side_effect=AssertionError('execution forbidden')):
            with self.assertRaisesRegex(ValueError, 'frozen manifest required'):
                build.main(['--execute'])

    def test_freeze_hash_and_path_guards(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src, review = root / 'window_module.c', root / 'review.json'
            src.write_text('/* offline manifest fixture, never compiled */\n')
            provider = root / 'provider_adapter.c'
            provider.write_text('/* provider fixture only */')
            review.write_text('{"review":"fixture only"}\n')
            manifest = {'status':'T30_SOURCE_FINAL_REVIEWED',
                'source_r14':{'path':src.name,'sha256':build.digest(src)},
                'source_r15':{'path':provider.name,'sha256':build.digest(provider)},
                'review':{'path':review.name,'sha256':build.digest(review)}}
            path = root / 'pins.json'
            path.write_text(json.dumps(manifest))
            self.assertEqual(build.frozen(root, path)[1]['source_r14'], src.resolve())
            src.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'source_r14 SHA mismatch'):
                build.frozen(root, path)
            manifest['source_r14']['path'] = '../window_module.c'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'escapes snapshot'):
                build.frozen(root, path)
            manifest['status'] = 'UNFROZEN_DO_NOT_EXECUTE'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'not frozen'):
                build.frozen(root, path)

    def test_r15_freeze_required_even_if_r14_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src = root / 'window_module.c'
            src.write_text('fixture')
            path = root / 'pins.json'
            path.write_text(json.dumps({'status':'T30_SOURCE_FINAL_REVIEWED',
                'source_r14':{'path':src.name,'sha256':build.digest(src)}}))
            with self.assertRaisesRegex(ValueError, 'missing source_r15 path'):
                build.frozen(root, path)

    def test_baseline_input_drift_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'baseline.o'
            path.write_bytes(b'fixture bytes only; not an ELF')
            recipe = {'inputs':{'$BASE/object':{'bytes':path.stat().st_size,'sha256':build.digest(path)}}}
            build.verify_inputs(recipe, lambda token: str(path))
            path.write_bytes(b'different bytes')
            with self.assertRaisesRegex(ValueError, 'baseline input drift'):
                build.verify_inputs(recipe, lambda token: str(path))

    def test_actual_recipe_has_two_replaceable_objects(self):
        recipe = json.loads((HERE / 'recipe.json').read_text())
        self.assertEqual(recipe['candidate_source_sha256'], {'r14': None, 'r15': None})
        self.assertEqual(set(recipe['compiles']), {'r14','r15'})
        for unit, name in [('r14','window_module.c'), ('r15','provider_adapter.c')]:
            self.assertEqual(recipe['compiles'][unit].count('-c'), 1)
            self.assertTrue(recipe['baseline_sources'][unit].endswith('/' + name))
            self.assertEqual(recipe['link'].count(recipe['replace_objects'][unit]), 1)
        self.assertEqual(sum(x.endswith('.o') for x in recipe['link']), 16)
        self.assertEqual(recipe['inputs']['$BASE/bridge.so']['sha256'], recipe['bridge_sha256'])
        for suffix in ['llvm/bin/clang', 'llvm/bin/ld.lld', 'llvm/bin/llvm-readelf', 'libdl.a', 'libc.so']:
            self.assertTrue(any(k.endswith(suffix) and v['bytes'] > 0 and len(v['sha256']) == 64 for k,v in recipe['inputs'].items()))
        self.assertTrue(all('/Users/' not in k and '/home/' not in k for k in recipe['inputs']))

if __name__ == '__main__':
    unittest.main()
