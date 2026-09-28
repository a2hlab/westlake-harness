import json
import tempfile
import unittest
from pathlib import Path

import replay_evidence


def event(source, seq, time):
    return {
        "schemaVersion": 1, "source": source, "bootId": "boot",
        "generation": 1, "requestId": "request", "seq": seq,
        "monotonicNs": time, "kind": "OBS", "payload": {},
    }


class ReplayEvidenceTest(unittest.TestCase):
    def test_two_sources_valid(self):
        replay_evidence.validate([event("stimulus", 1, 1), event("observer", 1, 2)])

    def test_duplicate_identity_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            replay_evidence.validate([event("same", 1, 1), event("same", 1, 1)])

    def test_one_source_rejected(self):
        with self.assertRaisesRegex(ValueError, "two independent"):
            replay_evidence.validate([event("same", 1, 1)])

    def test_load_rejects_missing_field(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            value = event("a", 1, 1)
            del value["bootId"]
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing fields"):
                replay_evidence.load_events(path)


if __name__ == "__main__":
    unittest.main()
