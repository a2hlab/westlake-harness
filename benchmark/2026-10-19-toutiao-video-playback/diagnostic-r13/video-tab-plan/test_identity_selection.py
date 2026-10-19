import unittest
from pathlib import Path
from identity_selection import select_exact, check_stat
HERE=Path(__file__).resolve().parent
class IdentitySelectionTests(unittest.TestCase):
    def test_actual_ps_name_is_selected(self):
        raw=(HERE/'ps-original-line.txt').read_text()
        self.assertEqual(select_exact(raw,5602,7462),7462)
        self.assertNotEqual(raw.split()[3],'id.article.news')
    def test_wrong_identity_uid_name_and_duplicate_refused(self):
        raw=(HERE/'ps-original-line.txt').read_text()
        for text in [raw.replace('20011206','0'),raw.replace('com.ss.android.article.news','id.article.news'),raw+raw,raw.replace('7462','7463'),raw.replace('5602','5603')]:
            with self.subTest(text=text),self.assertRaises(ValueError):select_exact(text,5602,7462)
    def test_actual_stat_birth_and_parent(self):
        raw=(HERE/'child-original-stat.txt').read_text().strip()
        check_stat(raw,7462,14456,5602)
        for pid,birth,parent in [(7463,14456,5602),(7462,14457,5602),(7462,14456,5603)]:
            with self.subTest(identity=(pid,birth,parent)),self.assertRaises(ValueError):check_stat(raw,pid,birth,parent)
if __name__=='__main__':unittest.main()
