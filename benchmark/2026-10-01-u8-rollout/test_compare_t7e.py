import tempfile
import unittest
from pathlib import Path
from compare_t7e import compare, sha


class EvidenceBoundaryTests(unittest.TestCase):
    def test_only_backtrace_word_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            ref, replay = Path(tmp) / 'ref', Path(tmp) / 'replay'
            ref.mkdir(); replay.mkdir()
            names = ['boot.art', 'boot.oat'] + [f'other-{i}.vdex' for i in range(25)]
            expected = {}
            for name in names:
                data = b'original command' if name == 'boot.oat' else bytes(0x3e3c0)
                (ref / name).write_bytes(data); (replay / name).write_bytes(data)
                expected[name] = sha(data)
            changed = bytearray((replay / 'boot.art').read_bytes())
            changed[0x3e3b9] = 1
            (replay / 'boot.art').write_bytes(changed)
            run = lambda: compare(ref, replay, expected, 'original command')
            self.assertTrue(run()['boot_art_only_proposal_satisfied'])
            changed[0x1c] = 2; (replay / 'boot.art').write_bytes(changed)
            self.assertFalse(run()['boot_art_only_proposal_satisfied'])
            changed[0x1c] = 0
            changed[0x100] = 1; (replay / 'boot.art').write_bytes(changed)
            self.assertFalse(run()['boot_art_only_proposal_satisfied'])
            changed[0x100] = 0; (replay / 'boot.art').write_bytes(changed)
            (replay / 'boot.oat').write_bytes(b'original command changed path')
            self.assertFalse(run()['boot_art_only_proposal_satisfied'])
            (replay / 'boot.oat').write_bytes(b'original command')
            expected['boot.art'] = sha(b'wrong original')
            self.assertFalse(run()['boot_art_only_proposal_satisfied'])


if __name__ == '__main__':
    unittest.main()
