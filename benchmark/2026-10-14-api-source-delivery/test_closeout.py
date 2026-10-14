import copy
import unittest

import generate as g
import map_closeout as m


class CloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = g.read(g.HERE / 'release-v2/source-build-mapping.json')
        cls.recipes = g.read(g.HERE / 'release-v2/recipes/recipes.json')
        cls.revision, cls.tree = g.master_tree()

    def apply(self, changes):
        return m.amend(self.base, self.recipes, changes, self.revision, self.tree)

    def test_existing_frozen_patch_is_delivery_only(self):
        path = 'sources/api-implementations/FZ-005/frozen/patches/22-dex2oat__implicit-suspend-checks-off.patch'
        sha = g.sha(g.MAIN / path)
        out, _ = self.apply([{'id': 'REG-005', 'source_entry': [
            {'path': path, 'sha256': sha, 'expected_sha256': sha, 'role': 'implementation_patch'}]}])
        before = next(r for r in self.base['rows'] if r['id'] == 'REG-005')
        after = next(r for r in out['rows'] if r['id'] == 'REG-005')
        self.assertEqual(before['implementation_status'], after['implementation_status'])
        self.assertFalse(after['complete_delivery_claim'])
        self.assertTrue(after['source_entry'][0]['master_tracked'])
        self.assertEqual(len(out['rows']), 315)

    def test_capability_grade_change_rejected(self):
        with self.assertRaises(ValueError):
            self.apply([{'id': 'REG-005', 'implementation_status': 'implemented'}])

    def test_duplicate_and_unknown_row_rejected(self):
        for changes in ([{'id': 'not-an-api'}], [{'id': 'REG-005'}, {'id': 'REG-005'}]):
            with self.assertRaises(ValueError):
                self.apply(changes)

    def test_wrong_source_hash_rejected(self):
        entry = copy.deepcopy(self.base['rows'][0]['source_entry'][0])
        entry['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.apply([{'id': 'REG-005', 'source_entry': [entry]}])

    def test_uncommitted_source_rejected(self):
        entry = copy.deepcopy(self.base['rows'][0]['source_entry'][0])
        with self.assertRaises(ValueError):
            m.amend(self.base, self.recipes, [{'id': 'REG-005', 'source_entry': [entry]}], self.revision, {})

    def test_shared_recipe_replacement_rejected(self):
        recipe = copy.deepcopy(self.recipes['recipes'][0])
        with self.assertRaises(ValueError):
            self.apply([{'id': 'REG-005', 'recipe': recipe}])


if __name__ == '__main__':
    unittest.main()
