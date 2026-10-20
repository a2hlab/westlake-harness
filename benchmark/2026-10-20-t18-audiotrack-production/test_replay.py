#!/usr/bin/env python3
import contextlib,io,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from build import command,compare_owner,sections
class ReplayTests(unittest.TestCase):
    def test_non_elf_rejected(self):
        with self.assertRaises(ValueError):sections(b'not an ELF')
    def test_missing_receipts_rejected(self):
        from verify import verify
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):verify(Path(td))
    def test_timeout_retains_raw_and_failure(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            def timeout(argv,**kw):
                kw['stdout'].write(b'partial binary\x00\xff');kw['stderr'].write(b'compiler warning\n')
                raise subprocess.TimeoutExpired(argv,90)
            with patch('build.subprocess.run',side_effect=timeout):
                with self.assertRaises(RuntimeError):command(['compiler'],d,'compile')
            self.assertEqual((d/'compile.rc').read_text(),'124\n')
            self.assertEqual((d/'compile.stdout').read_bytes(),b'partial binary\x00\xff')
            self.assertEqual((d/'compile.stderr').read_bytes(),b'compiler warning\n')
    def test_real_owner_text_mutation_is_rejected(self):
        raw=Path.home()/'.local/share/westlake/t18-production/audio-baseline-mac-01/audio.o'
        data=bytearray(raw.read_bytes());text=next(s for s in sections(data) if s[0]=='.text');data[text[1][4]]^=1
        with tempfile.TemporaryDirectory() as td:
            mutant=Path(td)/'bad.o';mutant.write_bytes(data)
            with self.assertRaises(ValueError):compare_owner(raw,mutant)
if __name__=='__main__':unittest.main()
