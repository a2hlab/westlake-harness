"""Known answers from the three actual r2 smoke runs; no device operation."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
import observe_effects

H = Path(__file__).resolve().parent
E = H / 'window1/smoke-correction-1155'
M = H.parents[2] / 'westlake-harness'
spec = importlib.util.spec_from_file_location('reviewed_activation_smoke', M / 'scripts/lab/activation_smoke.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class Correction(unittest.TestCase):
    def cases(self):
        for board, variant in [('5ea', 'common'), ('5cd', 'common'), ('61b', '61b')]:
            proposal = json.loads((H / 'window1' / variant / f'smoke-{board}-proposal.json').read_text())
            fixture = json.loads((E / f'replay-{board}.json').read_text())
            yield board, proposal, fixture

    def evaluate(self, proposal, fixture):
        return smoke.evaluate(proposal, fixture['runs'], fixture['hilogs'], fixture['probe'])

    def test_actual_three_board_replay_passes_without_fd_app_m6(self):
        for board, proposal, fixture in self.cases():
            with self.subTest(board=board):
                self.assertEqual(fixture['hilogs']['fd-app'], '')
                passed, checks = self.evaluate(proposal, fixture)
                self.assertTrue(passed, [c for c in checks if not c['ok']])
                self.assertFalse(any(c.get('fix') == 'U14-BRIDGE-M6' for c in checks))

    def test_exact_actual_localsend_line_and_optional_prefix(self):
        for board, proposal, _ in self.cases():
            fix = next(f for f in proposal['fixes'] if f['id'] == 'U14-FLUTTER-EGL')
            marker = fix['markers'][1]
            self.assertEqual(marker, r'EGLSurface=(0x)?0*[1-9a-fA-F][0-9a-fA-F]*')
            line = (E / f'localsend-{board}-nonzero.txt').read_text()
            self.assertGreater(smoke.marker_hits(line, [marker])[marker], 0)
            self.assertGreater(smoke.marker_hits('EGLSurface=0x000A1', [marker])[marker], 0)
            for null in ['EGLSurface=00000000', 'EGLSurface=0x00000000', 'EGLSurface=(nil)']:
                self.assertEqual(smoke.marker_hits(null, [marker])[marker], 0)

    def test_only_the_two_approved_semantic_changes(self):
        for board, proposal, _ in self.cases():
            original = json.loads((E / f'executed-smoke-{board}.json').read_text())
            expected = copy.deepcopy(original)
            expected['fixes'] = [f for f in expected['fixes'] if f['id'] != 'U14-BRIDGE-M6']
            next(f for f in expected['fixes'] if f['id'] == 'U14-FLUTTER-EGL')['markers'][1] = r'EGLSurface=(0x)?0*[1-9a-fA-F][0-9a-fA-F]*'
            expected['pending_outer_review'] = True
            self.assertEqual(proposal, expected)

    def test_zero_surface_still_rejects(self):
        for _, proposal, fixture in self.cases():
            fixture['hilogs']['localsend'] = 'eglCreateWindowSurface: detected ANW shim -> EGLSurface=00000000'
            self.assertFalse(self.evaluate(proposal, fixture)[0])

    def test_crypto_failure_still_rejects(self):
        for _, proposal, fixture in self.cases():
            fixture['probe']['control_crypto']['passed'] = False
            self.assertFalse(self.evaluate(proposal, fixture)[0])

    def test_third_bridge_or_second_art_still_rejects(self):
        for _, proposal, fixture in self.cases():
            for lib in ['liboh_adapter_bridge.so', 'libart.so']:
                changed = copy.deepcopy(fixture)
                changed['probe']['copies'][lib].append('/same-library@new-load-base')
                self.assertFalse(self.evaluate(proposal, changed)[0])

    def test_wrong_fingerprint_or_m5_absent_still_rejects(self):
        for _, proposal, fixture in self.cases():
            wrong = copy.deepcopy(fixture)
            next(iter(wrong['runs'].values()))['runtime_fp'] = 'wrong'
            self.assertFalse(self.evaluate(proposal, wrong)[0])
            m5 = next(f for f in proposal['fixes'] if f['id'] == 'U14-BRIDGE-M5')
            fixture['hilogs'][m5['key']] = ''
            self.assertFalse(self.evaluate(proposal, fixture)[0])

    def test_installed_specs_match_approved_proposal_without_pending_flag(self):
        for board, proposal, _ in self.cases():
            proposal.pop('pending_outer_review')
            variant = '61b' if board == '61b' else 'common'
            installed = json.loads((H / 'window1' / variant / f'smoke-{board}.json').read_text())
            self.assertEqual(installed, proposal)

    def test_m6_absence_is_unknown_and_real_marker_is_record_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / 'termux'
            p.mkdir()
            (p / 'record.json').write_text('{}')
            (p / 'hilog.txt').write_text('unrelated line\n')
            data = observe_effects.effect_report(root)
            self.assertFalse(data['activation_veto'])
            self.assertEqual(data['runs'][0]['status'], 'untriggered/unknown')
            (p / 'hilog.txt').write_text(observe_effects.MARKER + '123\nCompleteBackground\n')
            data = observe_effects.effect_report(root)
            self.assertEqual(data['runs'][0]['marker_count'], 1)
            self.assertEqual(data['runs'][0]['status'], 'observed')
            self.assertTrue(data['record_only'])


if __name__ == '__main__':
    unittest.main()
