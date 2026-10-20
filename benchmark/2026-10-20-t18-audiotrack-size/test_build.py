#!/usr/bin/env python3
"""Exercise real build CLI preview/timeout flow; compiler is a test seam."""
import contextlib, io, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import build_object
class BuildTests(unittest.TestCase):
    def invoke(self, argv):
        with patch.object(sys,'argv',['build_object.py',*argv]), contextlib.redirect_stdout(io.StringIO()):
            build_object.main()
    def test_preview_has_no_output_directory(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'out'
            with patch.object(build_object,'sha',return_value='pinned'),patch.object(build_object.json,'loads',return_value={'source_pins':{},'sdk_pins':{}}),patch.object(build_object,'derive',return_value=b'source'):
                self.invoke(['--sdk',td,'--out',str(out)])
            self.assertFalse(out.exists())
    def test_timeout_preserves_partial_bytes_and_status(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'out'
            def timeout(argv,**kw):
                kw['stdout'].write(b'partial stdout\n');kw['stderr'].write(b'partial stderr\n')
                raise subprocess.TimeoutExpired(argv,60)
            # Patch pins only; exercise actual file creation/recording and failure path.
            with patch.object(build_object.json,'loads',return_value={'source_pins':{},'sdk_pins':{}}),patch.object(build_object,'derive',return_value=b'source'),patch.object(build_object.subprocess,'run',side_effect=timeout):
                with self.assertRaises(SystemExit) as cm:self.invoke(['--sdk',td,'--out',str(out),'--execute'])
            self.assertEqual(cm.exception.code,124)
            self.assertEqual((out/'stdout').read_bytes(),b'partial stdout\n')
            self.assertEqual((out/'stderr').read_bytes(),b'partial stderr\n')
            self.assertEqual((out/'rc').read_text(),'124\n')
            self.assertEqual(json.loads((out/'result.json').read_text())['status'],'COMPILE_TIMEOUT')
if __name__=='__main__':unittest.main()
