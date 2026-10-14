import hashlib
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent


class ShellPredicateTests(unittest.TestCase):
    def function(self, name):
        source = (HERE / 'execute-three.sh').read_text()
        start = source.index(name + '() {')
        end = source.index('\n}\n', start) + 3
        return source[start:end]

    def invoke(self, name, arguments, setup=''):
        script = setup + '\n' + self.function(name) + '\nif ' + name + ' ' + ' '.join(shlex.quote(str(value)) for value in arguments) + '; then exit 0; else exit 2; fi\n'
        return subprocess.run(['/bin/sh', '-c', script], capture_output=True).returncode

    def test_actual_pin_rejects_missing_in_conditional_context(self):
        self.assertEqual(self.invoke('pin', ['/no-such-icon', 'a' * 64]), 2)

    def test_actual_pin_matches_bytes_and_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            icon = Path(directory) / 'icon'
            link = Path(directory) / 'link'
            icon.write_bytes(b'original')
            link.symlink_to(icon)
            pin = hashlib.sha256(b'original').hexdigest()
            setup = 'sha256sum() { shasum -a 256 "$1"; }'
            self.assertEqual(self.invoke('pin', [icon, pin], setup), 0)
            self.assertEqual(self.invoke('pin', [link, pin], setup), 2)

    def test_metadata_rejects_symlink_even_if_mocked_stat_and_label_match(self):
        with tempfile.TemporaryDirectory() as directory:
            icon = Path(directory) / 'icon'
            link = Path(directory) / 'link'
            icon.write_bytes(b'original')
            link.symlink_to(icon)
            setup = "stat() { printf '3060:3060:644'; }; ls() { printf 'u:object_r:data_app_el1_file:s0 icon'; }"
            self.assertEqual(self.invoke('metadata', [link], setup), 2)

    def test_five_diff_only_targets_and_counts(self):
        original = (HERE / 'execute-three.sh').read_text()
        five = (HERE / 'execute-five.sh').read_text()
        original_start = original.index('candidate_pin() {')
        original_end = original.index('\nmetadata()', original_start)
        five_start = five.index('candidate_pin() {')
        five_end = five.index('\nmetadata()', five_start)
        original = original[:original_start] + 'PIN_BRANCH' + original[original_end:]
        five = five[:five_start] + 'PIN_BRANCH' + five[five_end:]
        five = five.replace('com.kaajjo.libresudoku com.lcdcode.moodcairns com.paperknifeplus.app com.groce.app org.fossify.calendar', 'app.varlorg.unote com.alxgnon.postwriter org.tasks')
        five = five.replace('5_FILES_49_ROWS', '3_FILES_80_ROWS')
        self.assertEqual(original, five)


if __name__ == '__main__':
    unittest.main()
