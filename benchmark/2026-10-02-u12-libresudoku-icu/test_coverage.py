import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


class Coverage(unittest.TestCase):
    def test_same_country_display_path_without_new_artifact(self):
        result = json.loads((HERE / "results.json").read_text())
        self.assertEqual(result["expected_first_fatal_moved"], 1)
        self.assertTrue(result["candidate_sha256"].startswith("1e206531"))
        self.assertFalse(result["new_native_artifact"])
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["t20"], "unknown")
        dex = (HERE / "dex.json").read_text()
        self.assertIn("Locale.getDisplayCountry", dex)
        self.assertIn("LocaleNative;.getDisplayCountry", dex)
        self.assertIn("String;.isEmpty", dex)
        candidate = (HERE / "evidence/constructor-candidate.txt").read_text()
        self.assertIn("forLanguageTag", candidate)
        self.assertRegex(candidate, r"str\s+wzr, \[x29, #0x1c\]")
        self.assertIn("ScopedIcuLocale", (HERE / "evidence/country-candidate.txt").read_text())


if __name__ == "__main__":
    unittest.main()
