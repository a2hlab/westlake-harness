import copy
import unittest
from verify import validate_removal

class RetirementGate(unittest.TestCase):
    def setUp(self):
        self.good = dict(name="westlake-harness-label", master_ancestor=True, tracked_clean=True,
                         untracked_clean=True, live_content_matches_archive=True, restore_verified=True,
                         no_open_files=True, archive_members_verified=True,
                         local_archive_sha256="a" * 64, remote_archive_sha256="a" * 64)
    def test_verified_candidate(self):
        self.assertTrue(validate_removal(self.good))
    def test_refuses_each_missing_prerequisite(self):
        for field in ("master_ancestor", "tracked_clean", "untracked_clean", "live_content_matches_archive", "restore_verified", "no_open_files", "archive_members_verified"):
            with self.subTest(field=field):
                bad=copy.deepcopy(self.good); bad[field]=False
                with self.assertRaises(ValueError): validate_removal(bad)
    def test_refuses_archive_mismatch(self):
        bad=dict(self.good,remote_archive_sha256="b"*64)
        with self.assertRaises(ValueError): validate_removal(bad)
    def test_refuses_missing_archive(self):
        bad=dict(self.good,local_archive_sha256="",remote_archive_sha256="")
        with self.assertRaises(ValueError): validate_removal(bad)
    def test_refuses_other_worktree(self):
        for name in ("westlake-harness", "westlake-harness-bms", "../westlake-harness-label"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError): validate_removal(dict(self.good,name=name))

if __name__ == "__main__": unittest.main()
