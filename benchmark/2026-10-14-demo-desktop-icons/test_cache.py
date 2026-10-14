import hashlib
import sqlite3
import unittest

import prepare_cache as cache


def execute(connection, sql):
    sql = '\n'.join(line for line in sql.splitlines() if not line.startswith('.'))
    try:
        connection.executescript(sql)
    except sqlite3.Error:
        connection.rollback()
        raise


class CacheTransactionTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(':memory:')
        self.connection.execute('CREATE TABLE bundleResource(NAME TEXT PRIMARY KEY,UPDATE_TIME INTEGER,LABEL TEXT,ICON TEXT,SYSTEM_STATE TEXT,FOREGROUND BLOB,BACKGROUND BLOB)')
        for package in cache.PACKAGES:
            for name in [package, package + '/entry/Activity']:
                self.connection.execute('INSERT INTO bundleResource VALUES(?,?,?,?,?,?,?)', (name, 1, 'Label', 'old-uri', 'state', b'old-png', None))
        self.connection.execute('INSERT INTO bundleResource VALUES(?,?,?,?,?,?,?)', ('other.pkg', 2, 'Other', 'unchanged', 'state', b'other', b'bg'))
        self.connection.commit()
        images = {package: b'\x89PNG\r\n\x1a\n' + package.encode() for package in cache.PACKAGES}
        self.columns, self.before, self.after = cache.build(self.connection, images)

    def tearDown(self):
        self.connection.close()

    def rows(self):
        return self.connection.execute('SELECT * FROM bundleResource ORDER BY NAME').fetchall()

    def test_apply_then_exact_rollback_and_foreign_unchanged(self):
        original = self.rows()
        foreign = next(row for row in original if row[0] == 'other.pkg')
        execute(self.connection, cache.make_sql(self.columns, self.before, self.after))
        self.assertEqual(next(row for row in self.rows() if row[0] == 'other.pkg'), foreign)
        for old, new in zip(self.before, self.after):
            self.assertEqual([value for column, value in zip(self.columns, old) if column not in ('ICON', 'FOREGROUND')],
                             [value for column, value in zip(self.columns, new) if column not in ('ICON', 'FOREGROUND')])
        execute(self.connection, cache.make_verify_sql(self.columns, self.after))
        execute(self.connection, cache.make_sql(self.columns, self.after, self.before))
        self.assertEqual(original, self.rows())

    def test_late_row_drift_rolls_back_earlier_updates(self):
        self.connection.execute('UPDATE bundleResource SET LABEL=? WHERE NAME=?', ('Foreign', self.before[-1][0]))
        self.connection.commit()
        original = self.rows()
        with self.assertRaises(sqlite3.IntegrityError):
            execute(self.connection, cache.make_sql(self.columns, self.before, self.after))
        self.assertEqual(self.rows(), original)

    def test_extra_ability_row_rejected(self):
        self.connection.execute('INSERT INTO bundleResource VALUES(?,?,?,?,?,?,?)', (cache.PACKAGES[0] + '/entry/Unexpected', 1, 'Extra', 'icon', 'state', b'png', None))
        self.connection.commit()
        original = self.rows()
        with self.assertRaises(sqlite3.IntegrityError):
            execute(self.connection, cache.make_sql(self.columns, self.before, self.after))
        self.assertEqual(self.rows(), original)

    def test_foreign_after_row_blocks_rollback(self):
        execute(self.connection, cache.make_sql(self.columns, self.before, self.after))
        self.connection.execute('UPDATE bundleResource SET FOREGROUND=? WHERE NAME=?', (b'foreign', self.after[-1][0]))
        self.connection.commit()
        original = self.rows()
        with self.assertRaises(sqlite3.IntegrityError):
            execute(self.connection, cache.make_sql(self.columns, self.after, self.before))
        self.assertEqual(self.rows(), original)

    def test_prefix_collision_not_selected(self):
        self.assertFalse(cache.belongs('org.tasks.extra/entry/Activity', 'org.tasks'))

    def test_quoted_label_remains_literal(self):
        self.assertEqual(cache.literal("a'b"), "'a''b'")


if __name__ == '__main__':
    unittest.main()
