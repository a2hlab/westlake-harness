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


class Window3KnownAnswer(unittest.TestCase):
    def test_selftest_reproduces_signoff(self):
        run = ps.WORKSPACES / 'westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun/window3'
        if not run.is_dir():
            self.skipTest('window3 inputs not present')
        self.assertEqual(ps.selftest(), 0)


if __name__ == '__main__':
    unittest.main()
