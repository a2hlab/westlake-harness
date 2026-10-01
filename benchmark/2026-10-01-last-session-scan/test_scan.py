import copy
import json
import unittest

import scan


def event(number, message, pid=10, tid=11, time='10-01 01:00:00.000'):
    return dict(line=number, message=message, pid=pid, tid=tid, timestamp=time, tag='C00f00/OH_GfxShim', level='I')


def parsed(messages):
    return scan.extract([event(number, message) for number, message in enumerate(messages, 1)], {10}, '10-01 01:00:20.999')


class ParserTests(unittest.TestCase):
    def test_unknown_session_and_caught_gl_iae_are_distinct(self):
        events = [event(1, 'getOhNativeWindow: unknown sessionId=1'), event(2, 'createSession: success, sessionId=1'), event(3, 'java.lang.IllegalArgumentException: Make sure the SurfaceView or associated SurfaceHolder has a valid Surface')]
        events[-1]['tag'] = 'C00f00/GLSurfaceView'
        result = scan.correlate(scan.extract(events, {10}, None))
        self.assertEqual(result['unknown_session_count'], 1)
        self.assertEqual(result['unknown_sessions'][0]['relative_to_create_success'], 'before-success')
        self.assertEqual(result['gl_valid_surface_iae_count'], 1)
        self.assertEqual(result['null_count'], 0)

    def test_foreign_reflection_stderr_and_late_are_excluded(self):
        marker = '[IPC] ENTER oh_wm_set_last_session_local session=2'
        events = [event(1, marker), event(2, marker, pid=99), event(3, 'class_linker.cc:1 ' + marker), event(4, '[stderr] ' + marker), event(5, marker, time='10-01 01:00:21.000')]
        self.assertEqual([entry['line'] for entry in scan.extract(events, {10}, '10-01 01:00:20.999')], [1])
        unmatched = [event(6, '[stderr] ' + marker)]
        self.assertEqual([entry['line'] for entry in scan.extract(unmatched, {10}, None)], [6])

    def test_session_identity_not_latest_queue_controls_update(self):
        rows = parsed([
            'createSession: bundle=app ability=One name=app/app.One, androidType=1',
            'createSession: success, sessionId=1',
            '[IPC] ENTER oh_wm_set_last_session_local session=1',
            'BBQ.create name=VRI[One] ptr=AAA',
            'BBQ.update: sessionId=1 → OHNativeWindow=ABC',
            'createSession: bundle=app ability=Two name=app/app.Two, androidType=1',
            'createSession: success, sessionId=2',
            '[IPC] ENTER oh_wm_set_last_session_local session=2',
            'BBQ.create name=VRI[Two] ptr=BBB',
            'BBQ.update: sessionId=2 → OHNativeWindow=DEF',
            'BBQ.update: getOhNativeWindow(sessionId=1) returned null',
            'BBQ.getSurface: ohNativeWindow null (sessionId=1 not attached) returning empty Surface',
        ])
        result = scan.correlate(rows)
        self.assertEqual(result['distinct_session_count'], 2)
        self.assertEqual(result['null_count'], 1)
        self.assertEqual(result['empty_surface_count'], 1)
        failed = result['lookups'][-1]
        self.assertEqual((failed['activity'], failed['queue_ptr'], failed['last_session']), ('app.One', 'AAA', 2))
        self.assertTrue(failed['non_last'])

    def test_foreign_thread_does_not_supply_missing_creation_or_queue(self):
        events = [event(1, 'createSession: bundle=app ability=One name=app/app.One,'), event(2, 'BBQ.create name=VRI[One] ptr=AAA'), event(3, 'createSession: success, sessionId=1', tid=99), event(4, 'BBQ.update: getOhNativeWindow(sessionId=1) returned null', tid=99)]
        result = scan.correlate(scan.extract(events, {10}, None))
        self.assertIsNone(result['lookups'][0]['activity'])
        self.assertIsNone(result['lookups'][0]['queue_ptr'])
        self.assertIsNone(result['lookups'][0]['non_last'])


class ImpactTests(unittest.TestCase):
    def test_foreground_background_and_unknown_are_distinct(self):
        row = dict(pids=[10], cutoff='x', log_complete=True, distinct_session_count=2, lookups=[dict(outcome='update-null',activity='app.One')])
        self.assertEqual(scan.impact(row, foreground='app.One'), 'foreground-null-white-candidate')
        self.assertEqual(scan.impact(row, background=['app.One']), 'background-only-not-on-screen-blocker')
        self.assertEqual(scan.impact(row), 'null-foreground-unknown')
        row['lookups'][0]['activity'] = None
        self.assertEqual(scan.impact(row, background=['app.One']), 'null-foreground-unknown')

    def test_single_null_and_no_session_not_silently_passed(self):
        row = dict(pids=[10], cutoff='x', log_complete=True, distinct_session_count=1, lookups=[])
        self.assertEqual(scan.impact(row), 'single-session-not-exposed')
        row['lookups'] = [dict(outcome='update-null',activity='app.One')]
        self.assertEqual(scan.impact(row), 'single-session-null-counterexample')
        row['distinct_session_count'] = 0
        self.assertEqual(scan.impact(row), 'no-session-observed-not-a-negative')
        row['pids'] = []
        self.assertEqual(scan.impact(row), 'unknown-incomplete-evidence')


class CohortTests(unittest.TestCase):
    def test_full_report_and_controls_reproduce(self):
        result = scan.load()
        self.assertEqual(result, json.loads((scan.HERE / 'results.json').read_text()))
        self.assertEqual(scan.markdown(result), (scan.HERE / 'README.md').read_text())
        self.assertEqual(result['summary']['keys'], 66)
        self.assertEqual(result['summary']['signed_visuals']['own-ui'], 34)
        rows = {row['key']:row for row in result['rows']}
        for key in result['negative_controls']:
            self.assertEqual(rows[key]['visual'], 'own-ui')
            self.assertEqual(rows[key]['distinct_session_count'], 1)
            self.assertEqual(rows[key]['null_count'], 0)
            self.assertTrue(rows[key]['log_complete'])
        self.assertEqual(result['summary']['null_events'], 9)
        self.assertEqual(result['summary']['null_non_last_events'], 9)
        self.assertEqual(result['summary']['unknown_session_events'], 108)
        self.assertEqual(result['summary']['gl_valid_surface_iae_keys'], ['fd-app', 'fd-shatteredpixeldungeon'])
        self.assertEqual(result['summary']['gl_valid_surface_iae_events'], 2)
        for key in result['negative_controls']:
            self.assertEqual(rows[key]['unknown_session_count'], 2)
        for key, count in [('mindustry', 0), ('ppsspp', 2), ('fd-mobile', 4), ('x', 0)]:
            self.assertEqual(rows[key]['unknown_session_count'], count)
            self.assertEqual(rows[key]['gl_valid_surface_iae_count'], 0)
        self.assertEqual(rows['wikipedia']['impact'], 'foreground-null-white-candidate')
        self.assertEqual(rows['fd-AppManager']['null_count'], 0)
        self.assertEqual([session['android_type'] for session in rows['anki']['sessions']], [2, 1])
        signed = json.loads(scan.SCORES.read_text())
        expected = {row['key']:row['visual'] for shard in signed['shards'].values() for row in shard['rows']}
        self.assertEqual({key:row['visual'] for key,row in rows.items()}, expected)

    def test_pin_and_cohort_drift_refused(self):
        import base64
        import gzip
        intake = json.loads(gzip.decompress(base64.b64decode((scan.HERE / 'evidence.json.gz.b64').read_bytes())))
        authority = json.loads((scan.HERE / 'authority.json').read_text())
        broken = copy.deepcopy(intake)
        broken['signed_scores_sha256'] = 'changed'
        with self.assertRaises(ValueError):
            scan.build(broken, authority)
        broken = copy.deepcopy(intake)
        broken['rows'].pop()
        with self.assertRaises(ValueError):
            scan.build(broken, authority)


if __name__ == '__main__':
    unittest.main()
