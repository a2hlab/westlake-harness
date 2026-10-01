#!/usr/bin/env python3
"""evo_family: explicit tags win, curated overrides next, keyword rules last; lane tag sets the actor."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import evo_family as e

TEXT = """### EVO-0001（2026-10-01T04:05:39Z，harvest）
trigger: r2_record
symptom: > 外环(claude)·R2 记档(#97): [家族:concurrent-board][车道:oc-t4] 同板两个进程
### EVO-0002（2026-10-01T04:06:00Z，harvest）
symptom: > 外环(claude)·R2 记档(#96): 外环写「原始构建配方不存在」,只搜了产物
### EVO-0003（2026-10-01T04:07:00Z，harvest）
symptom: > 外环(claude)·改判(作废 #1): 换车道
"""


class Family(unittest.TestCase):
    def test_classification(self):
        rows = {c['id']: e.classify(c['symptom'], f"{c['id']}@{c['ts'][:16]}", {}) for c in e.cards(TEXT)}
        self.assertEqual(rows['EVO-0001'], ('concurrent-board', 'tag', 'oc-t4'))
        self.assertEqual(rows['EVO-0002'][0], 'narrow-negative')
        self.assertEqual(rows['EVO-0003'][0], 'decision')

    def test_override_beats_rules_but_not_tags(self):
        over = {'EVO-0002@2026-10-01T04:06': {'family': 'runtime-unverified', 'actor': 'cc-wiki'}}
        c = list(e.cards(TEXT))
        self.assertEqual(e.classify(c[1]['symptom'], 'EVO-0002@2026-10-01T04:06', over), ('runtime-unverified', 'curated', 'cc-wiki'))
        self.assertEqual(e.classify(c[0]['symptom'], 'EVO-0001@2026-10-01T04:05', {'EVO-0001@2026-10-01T04:05': {'family': 'other'}})[0], 'concurrent-board')


if __name__ == '__main__':
    unittest.main()
