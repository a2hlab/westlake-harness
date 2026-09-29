import json
from pathlib import Path
import tempfile
import unittest

import analyze


class EvidenceTests(unittest.TestCase):
    def test_baseline_known_sequence(self):
        got = analyze.inspect(analyze.BASELINE, 25183, 'com.example.helloworld')
        expected = {'attach': 3966, 'bind_main': 3985, 'bind_ok': 4307,
                    'launch_ability': 3988, 'launch_transaction': 4022,
                    'main_sentinel': 4443, 'vsync_request': 4616,
                    'vsync_callback': 4631, 'window_session': 4644,
                    'egl_surface': 5215, 'first_frame_notification': 5422}
        self.assertEqual({k: got['stages'][k]['first']['line'] for k in expected}, expected)
        self.assertIsNone(got['first_unobserved_launch_marker'])
        self.assertEqual(got['stages']['bind_failed']['count'], 0)

    def test_wrong_pid_registration_and_stack_are_not_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'hilog.txt'
            path.write_text('\n'.join([
                '01-02 07:26:24.000 10 10 I C00f00/AppSpawnXInit: initChild: proc=example.app target=android.app.ActivityThread',
                '01-02 07:26:24.001 11 11 I C00f00/OH_DER_VSync: onOhVsync ENTRY',
                '01-02 07:26:24.002 10 10 I C00f00/OH_RegHook: [BRIDGED] ScheduleLaunchAbility(recordId=1)',
                '01-02 07:26:24.003 10 10 I C00f00/AppSpawnXJava: [stderr] \tat activityResumed (first-frame): OH AbilityTransitionDone',
            ]) + '\n')
            got = analyze.inspect(path, 10, 'example.app')
            self.assertEqual(got['stages']['launch_ability']['count'], 0)
            self.assertEqual(got['stages']['vsync_callback']['count'], 0)
            self.assertEqual(got['stages']['first_frame_notification']['count'], 0)
            self.assertEqual(analyze.inspect(path, 11, 'example.app')['status'], 'identity_rejected')

    def test_missing_inputs_remain_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            result = analyze.build(Path(temp))
            self.assertEqual(len(result['apps']), 9)
            for row in result['apps']:
                self.assertEqual(row['status'], 'input_unavailable')
                self.assertIsNone(row['first_unobserved_launch_marker'])

    def test_captured_findings_have_distinct_bind_and_dispatch_outcomes(self):
        result = json.loads((analyze.HERE / 'results.json').read_text())
        apps = result['apps']
        self.assertEqual(len(apps), 9)
        self.assertEqual(sum(a['stages']['bind_failed']['count'] for a in apps), 7)
        self.assertEqual([a['key'] for a in apps if a['stages']['bind_ok']['count']], ['fd-stk', 'mindustry'])
        for app in apps:
            self.assertEqual(app['first_unobserved_launch_marker'], 'launch_ability')
            self.assertEqual(app['stages']['vsync_request']['count'], 0)
        events = result['delayed_ams_timeouts']
        self.assertEqual(len({r['key'] for r in events}), 8)
        self.assertNotIn('mindustry', {r['key'] for r in events})
        self.assertEqual(len([r for r in events if 'LIFECYCLE_HALF_TIMEOUT,Add Ability Stage TimeOut!' in r['text']]), 8)

    def test_capture_reproduction_and_source_hashes(self):
        result = json.loads((analyze.HERE / 'results.json').read_text())
        root = Path(result['apps'][0]['source']['path']).parents[1]
        if not root.exists():
            self.skipTest('Read-only #48 VM copy is not available on this host')
        regenerated = analyze.build(root)
        self.assertEqual(regenerated, result)
        for source in result['cross_capture_inputs']:
            self.assertEqual(analyze.digest(Path(source['path'])), source)


if __name__ == '__main__':
    unittest.main()
