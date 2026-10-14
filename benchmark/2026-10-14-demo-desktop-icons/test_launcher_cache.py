import base64
import hashlib
import sqlite3
import unittest
from unittest.mock import patch

import prepare_launcher_cache as cache
from test_cache import execute


class LauncherCacheTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(':memory:')
        self.connection.execute('CREATE TABLE icon_info(bundle_name TEXT,module_name TEXT,ability_name TEXT,icon_type INTEGER,fore_pic TEXT,back_pic TEXT,combine_pic TEXT,system_state TEXT,app_version TEXT,PRIMARY KEY(bundle_name,module_name,ability_name))')
        self.connection.execute('CREATE TABLE gridlayout_info(value TEXT)')
        self.connection.execute("INSERT INTO gridlayout_info VALUES('unchanged')")
        original = b'captured-placeholder-fixture'
        uri = 'data:image/png;base64,' + base64.b64encode(original).decode()
        images = {package: b'\x89PNG\r\n\x1a\n' + package.encode() for package in cache.PACKAGES}
        for package in cache.PACKAGES:
            keys = [('', ''), ('entry', 'Main')]
            if package == 'org.fossify.calendar':
                keys.append(('entry', 'Alias'))
            for module, ability in keys:
                self.connection.execute('INSERT INTO icon_info VALUES(?,?,?,?,?,?,?,?,?)', (package, module, ability, 'normal', None, None, uri, None, 'version'))
        self.connection.commit()
        self.pin_patch = patch.object(cache, 'PLACEHOLDER', hashlib.sha256(original).hexdigest())
        self.pin_patch.start()
        self.images = images
        self.before, self.after = cache.build(self.connection, images)

    def tearDown(self):
        self.pin_patch.stop()
        self.connection.close()

    def rows(self):
        return self.connection.execute('SELECT * FROM icon_info ORDER BY bundle_name,module_name,ability_name').fetchall()

    def test_17_combine_only_and_full_rollback(self):
        original = self.rows()
        execute(self.connection, cache.make_sql(self.before, self.after))
        self.assertEqual(sum(a != b for a, b in zip(original, self.rows())), 17)
        self.assertEqual(self.connection.execute('SELECT * FROM gridlayout_info').fetchall(), [('unchanged',)])
        for old, new in zip(self.before, self.after):
            self.assertEqual(old[:6] + old[7:], new[:6] + new[7:])
        execute(self.connection, cache.make_sql(self.after, self.before))
        self.assertEqual(original, self.rows())

    def test_late_version_drift_atomic_refusal(self):
        self.connection.execute('UPDATE icon_info SET app_version=? WHERE bundle_name=?', ('foreign', cache.PACKAGES[-1]))
        self.connection.commit()
        original = self.rows()
        with self.assertRaises(sqlite3.IntegrityError):
            execute(self.connection, cache.make_sql(self.before, self.after))
        self.assertEqual(original, self.rows())

    def test_foreign_after_image_preserved_on_rollback(self):
        execute(self.connection, cache.make_sql(self.before, self.after))
        self.connection.execute('UPDATE icon_info SET combine_pic=? WHERE bundle_name=?', ('foreign', cache.PACKAGES[-1]))
        self.connection.commit()
        original = self.rows()
        with self.assertRaises(sqlite3.IntegrityError):
            execute(self.connection, cache.make_sql(self.after, self.before))
        self.assertEqual(original, self.rows())

    def test_unverified_layered_kind_rejected(self):
        self.connection.execute('UPDATE icon_info SET icon_type=? WHERE bundle_name=?', ('layered', cache.PACKAGES[0]))
        with self.assertRaises(ValueError):
            cache.build(self.connection, self.images)


if __name__ == '__main__':
    unittest.main()
