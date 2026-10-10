import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location('cantopen_impact', Path(__file__).with_name('collect_impact.py'))
impact = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(impact)


class ImpactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fatal = impact.load_fatal()

    def events(self, messages):
        return [self.fatal.classify.parse('10-10 12:00:0%d.000 %d 12 E C00f00/AppSpawnXJava: %s' %
                (number, pid, message), number + 1) for number, (pid, message) in enumerate(messages)]

    def analyze(self, messages):
        events = self.events(messages)
        return impact.termination(events, {11}, self.fatal.analyze(events, {11}), self.fatal)

    def test_cantopen_main_thread_requires_kill_confirmation(self):
        first = self.analyze([(11, '[W-ROOM-SURVIVE] UNCAUGHT in thread Thread-1 (main=true): android.database.sqlite.SQLiteCantOpenDatabaseException: db'),
                             (11, '[W-ROOM-SURVIVE] main-thread fatal -> preserving kill semantics')])
        self.assertTrue(first['cantopen'])

    def test_cantopen_without_kill_confirmation_is_not_a_confirmed_fatal(self):
        first = self.analyze([(11, '[W-ROOM-SURVIVE] UNCAUGHT in thread Thread-1 (main=true): android.database.sqlite.SQLiteCantOpenDatabaseException: db')])
        self.assertFalse(first['cantopen'])

    def test_background_cantopen_is_not_fatal(self):
        self.assertFalse(self.analyze([(11, '[B8-UEH] background thread uncaught, process kept alive: android.database.sqlite.SQLiteCantOpenDatabaseException: db')])['cantopen'])

    def test_earlier_other_terminal_wins_over_later_cantopen(self):
        self.assertFalse(self.analyze([(11, '[CHILD_CK] J_invokeStaticMain_main_threw: java.lang.NullPointerException: first'),
            (11, '[W-ROOM-SURVIVE] UNCAUGHT in thread Thread-1 (main=true): android.database.sqlite.SQLiteCantOpenDatabaseException: db'),
            (11, '[W-ROOM-SURVIVE] main-thread fatal -> preserving kill semantics')])['cantopen'])

    def test_other_pid_cantopen_does_not_contaminate(self):
        self.assertFalse(self.analyze([(22, '[CHILD_CK] J_invokeStaticMain_main_threw: android.database.sqlite.SQLiteCantOpenDatabaseException: db')])['cantopen'])

    def test_standard_main_threw_cantopen_is_fatal(self):
        self.assertTrue(self.analyze([(11, '[CHILD_CK] J_invokeStaticMain_main_threw: android.database.sqlite.SQLiteCantOpenDatabaseException: db')])['cantopen'])

    def test_presence_is_not_first_fatal_and_prediction_is_separate(self):
        apps = [dict(key=key, package='fixture.' + key) for key in ['fatal', 'caught', 'pending', 'no-reference']]
        scans = {key: dict(calls=dict(Room=[{}] if key != 'no-reference' else [])) for key in ['fatal', 'caught', 'pending', 'no-reference']}
        measured = dict(fatal=dict(count=7, suspect=True, first_fatal=dict(cantopen=True, kind='CANTOPEN')),
                        caught=dict(count=3, suspect=False, first_fatal=dict(cantopen=False, kind='no-observed-termination')))
        rows, summary = impact.build(dict(apps=apps), {}, scans, measured)
        keyed = {row['key']: row for row in rows}
        self.assertEqual(summary['measured_cantopen_presence_keys'], 2)
        self.assertEqual(summary['measured_first_fatal_cantopen_count'], 1)
        self.assertEqual(summary['predicted_unmeasured_conditional_upper_bound_count'], 1)
        self.assertEqual(summary['unmeasured_startup_first_fatal_proven'], 0)
        self.assertEqual(keyed['caught']['predicted_blocked'], 'n')
        self.assertEqual(keyed['pending']['predicted_blocked'], 'possible-static')
        self.assertEqual(keyed['pending']['cantopen_count_5cd'], '')
        self.assertEqual(keyed['no-reference']['predicted_blocked'], 'unknown-no-dex-reference')

    def test_static_family_match_is_not_just_any_open_method(self):
        self.assertEqual(impact.family('Landroid/database/sqlite/SQLiteOpenHelper;', 'getWritableDatabase'), 'SQLiteOpenHelper')
        self.assertEqual(impact.family('Landroid/content/Context;', 'openOrCreateDatabase'), 'openOrCreateDatabase')
        self.assertEqual(impact.family('Landroidx/room/RoomDatabase;', 'query'), 'Room')
        self.assertIsNone(impact.family('Lfixture/Other;', 'open'))


if __name__ == '__main__':
    unittest.main()
