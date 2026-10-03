#!/usr/bin/env python3
"""Unit tests for pair_sheet.py's pre-screen: aHash similarity, auto verdict, and flaky k/n.
Image I/O (ff_gray) is monkeypatched with crafted grey arrays so the logic is tested without ffmpeg or screenshots.
The window3 known-answer test runs only when its inputs are present (skipped otherwise)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pair_sheet as ps  # noqa: E402

N = ps.HASH_SIZE * ps.HASH_SIZE
FLAT_WHITE = bytes([250]) * N                                   # std 0, near white  -> blank-white render
FLAT_GREY = bytes([120]) * N                                    # std 0, mid grey    -> flat-but-lit screen
RICH = bytes([(i * 7) % 256 for i in range(N)])                # high std, structured content
RICH2 = bytes([(255 - (i * 7) % 256) for i in range(N)])       # structured, inverted vs RICH


class Ahash(unittest.TestCase):
    def test_identical_is_one(self):
        self.assertEqual(ps.ahash_similarity(RICH, RICH), 1.0)

    def test_inverted_is_zero(self):
        self.assertEqual(ps.ahash_similarity(RICH, RICH2), 0.0)

    def test_none_is_none(self):
        self.assertIsNone(ps.ahash_similarity(RICH, None))


class Prescreen(unittest.TestCase):
    def _patch(self, mapping):
        self.addCleanup(setattr, ps, 'ff_gray', ps.ff_gray)
        ps.ff_gray = lambda p, *a, **k: mapping.get(str(p))

    def test_same_structured(self):
        self._patch({'w': RICH, 'u': RICH})
        self.assertEqual(ps.prescreen('w', 'u')['auto'], 'same')

    def test_different_structured(self):
        self._patch({'w': RICH, 'u': RICH2})
        self.assertEqual(ps.prescreen('w', 'u')['auto'], 'different')

    def test_missing_window_is_no_window(self):
        self._patch({'u': RICH})           # 'w' absent -> ff_gray returns None
        self.assertEqual(ps.prescreen('w', 'u')['auto'], 'no-window')

    def test_blank_white_vs_rich_is_no_window(self):
        # window went near-uniform white while the U9 drew content -> lost content
        self._patch({'w': FLAT_WHITE, 'u': RICH})
        self.assertEqual(ps.prescreen('w', 'u')['auto'], 'no-window')

    def test_flat_lit_matching_flat_u9_is_not_no_window(self):
        # both sides equally flat (a plain page) -> must NOT be no-window; identical -> same
        self._patch({'w': FLAT_GREY, 'u': FLAT_GREY})
        self.assertEqual(ps.prescreen('w', 'u')['auto'], 'same')

    def test_no_ref(self):
        self._patch({'w': RICH})           # 'u' absent
        self.assertEqual(ps.prescreen('w', 'u')['auto'], 'no-ref')


class FlakyKn(unittest.TestCase):
    def test_regression_zero_lit_three_obs(self):
        r = ps.flaky_kn('x', 'different', ['white', 'white'], u9_verdict='lit')   # +this(not-lit) -> 0/3, regression
        self.assertEqual((r['k'], r['n'], r['regression']), (0, 3, True))

    def test_not_regression_when_some_lit(self):
        r = ps.flaky_kn('x', 'same', ['white', 'white'], u9_verdict='lit')        # +this(lit) -> 1/3
        self.assertEqual((r['k'], r['n']), (1, 3))
        self.assertFalse(r['regression'])

    def test_two_obs_not_regression(self):
        r = ps.flaky_kn('x', 'different', ['white'], u9_verdict='lit')            # 0/2 -> rule needs >=3
        self.assertFalse(r['regression'])

    def test_u9_not_lit_same_is_not_lit(self):
        # U9 verdict not lit: same screen = still not lit (n+1, k unchanged); regression never fires
        r = ps.flaky_kn('x', 'same', ['white', 'white'], u9_verdict='alive-white-window')
        self.assertEqual((r['k'], r['n']), (0, 3))
        self.assertEqual(r['kn_this'], 'not-lit')
        self.assertFalse(r['regression'])

    def test_u9_not_lit_different_is_undecided(self):
        # U9 verdict not lit: different = could be lit now; not counted, kn_this=undecided
        r = ps.flaky_kn('x', 'different', ['white'], u9_verdict='alive-white-window')
        self.assertEqual((r['k'], r['n']), (0, 1))
        self.assertEqual(r['kn_this'], 'undecided')
        self.assertFalse(r['regression'])


class IsSuspect(unittest.TestCase):
    def test_clean_same_not_suspect(self):
        self.assertFalse(ps.is_suspect({'auto': 'same', 'flaky': False, 'flaky_kn': None}))

    def test_different_is_suspect(self):
        self.assertTrue(ps.is_suspect({'auto': 'different', 'flaky': False, 'flaky_kn': None}))

    def test_flaky_same_still_suspect_until_regression_known(self):
        self.assertTrue(ps.is_suspect({'auto': 'same', 'flaky': True, 'flaky_kn': {'regression': False}}))


class ReferenceListing(unittest.TestCase):
    """A reference dir is u9-ref-<board>.txt or exactly one <label>-ref-<board>.txt (the U10.1T8 reference set)."""
    LINE = 'row 1 col 1  k1  verdict=lit  corpus=cv2  MISSING\n'

    def _dir(self, *names):
        import tempfile
        d = Path(tempfile.mkdtemp())
        self.addCleanup(__import__('shutil').rmtree, d)
        for n in names:
            (d / n).write_text('# header\n' + self.LINE)
        return d

    def test_legacy_u9_name(self):
        d = self._dir('u9-ref-5ea.txt')
        self.assertEqual(ps.load_ref_board(str(d), '5ea'), {'k1': ('lit', None)})

    def test_labelled_name(self):
        d = self._dir('u10-1-t8-ref-5cd.txt')
        self.assertEqual(ps.load_ref_board(str(d), '5cd'), {'k1': ('lit', None)})
        self.assertEqual(ps.load_ref_board(str(d), '5ea'), {})

    def test_two_listings_for_one_board_refused(self):
        d = self._dir('a-ref-61b.txt', 'b-ref-61b.txt')
        with self.assertRaises(SystemExit):
            ps.load_ref_board(str(d), '61b')


class U1018ReferenceKnownAnswer(unittest.TestCase):
    """Window 3 vs the U10.1T8 reference: 76 same + trickytripper (signed lit from its w5 retest) different, 0 no-ref;
    window 5 yahtzeedicer (U10.1T8 lit) is same. Skipped when the real window runs are absent."""
    REF = ps.REPO / 'benchmark/2026-10-02-u10-1-t8-sweep/u10-1-t8-reference'
    SIGNOFF = ps.REPO / 'benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json'
    RERUN = ps.WORKSPACES / 'westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun'

    def _rows(self, window):
        run = self.RERUN / window
        if not run.is_dir() or not self.REF.is_dir():
            self.skipTest(f'{run} or {self.REF} not present')
        return ps.build_rows(run.resolve(), str(self.REF), str(self.SIGNOFF), ps.SAME_THRESHOLD)

    def test_window3(self):
        rows = self._rows('window3')
        self.assertEqual(len(rows), 77)
        self.assertEqual([r['key'] for r in rows if r['auto'] != 'same'], ['cv2-de-koelle-christian-trickytripper'])
        self.assertEqual(sum(r['auto'] == 'no-ref' for r in rows), 0)

    def test_window5_yahtzeedicer_same(self):
        rows = {r['key']: r for r in self._rows('window5') if r['shard'] == 'unlit-cv2'}
        r = rows['cv2-org-secuso-privacyfriendlyyahtzeedicer']
        self.assertEqual((r['auto'], r['u9_verdict']), ('same', 'lit'))


class Window3KnownAnswer(unittest.TestCase):
    def test_selftest_reproduces_signoff(self):
        run = ps.WORKSPACES / 'westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun/window3'
        if not run.is_dir():
            self.skipTest('window3 inputs not present')
        self.assertEqual(ps.selftest(), 0)


if __name__ == '__main__':
    unittest.main()


class RefListing(unittest.TestCase):
    """A reference listing may annotate a row after its t20 path (u14-ref: '<t20> *gain', 2026-10-03)."""

    def test_annotation_after_path_is_not_part_of_the_path(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'x-ref-5ea.txt'
            f.write_text('row 1 col 1  fd-noice  verdict=lit  corpus=original  /a/b/fd-noice/t20.jpeg *gain\n'
                         'row 1 col 2  fd-gone  verdict=dead  corpus=original  MISSING\n')
            table = ps.load_ref_board(f, '5ea')
            self.assertEqual(table['fd-noice'], ('lit', '/a/b/fd-noice/t20.jpeg'))
            self.assertEqual(table['fd-gone'], ('dead', None))

    def test_rehomed_key_resolves_from_its_reference_board(self):
        """U14 window 3: 61b's keys ran on 5ea/5cd; their reference rows are only in the 61b listing."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'u14-ref-5ea.txt').write_text('row 1 col 1  fd-a  verdict=lit  corpus=original  /r/5ea/fd-a.jpeg\n')
            (Path(tmp) / 'u14-ref-61b.txt').write_text('row 1 col 1  bmicalc  verdict=lit  corpus=cv2  /r/61b/bmi.jpeg\n')
            (Path(tmp) / 'u14-ref-5cd.txt').write_text('row 1 col 1  twice  verdict=lit  corpus=cv2  /r/5cd/t.jpeg\n')
            (Path(tmp) / 'u14-ref-x9.txt').write_text('row 1 col 1  twice  verdict=lit  corpus=cv2  /r/x9/t.jpeg\n')
            cache = {}
            self.assertEqual(ps.cross_board_ref(tmp, '5ea', 'bmicalc', cache), ('61b', ('lit', '/r/61b/bmi.jpeg')))
            self.assertIsNone(ps.cross_board_ref(tmp, '5ea', 'absent', cache))
            self.assertIsNone(ps.cross_board_ref(tmp, '5ea', 'twice', cache))  # two other boards: ambiguous
            self.assertIsNone(ps.cross_board_ref(Path(tmp) / 'u14-ref-5ea.txt', '5ea', 'bmicalc', cache))  # a file, not a dir
