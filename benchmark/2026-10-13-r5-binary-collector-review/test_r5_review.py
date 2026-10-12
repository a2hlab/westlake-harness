"""Independent local R5 seam checks: actual collector bytes, no HDC execution."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
SOURCE = WS / 'westlake-harness-bms/benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector'
PINS = {'binary_safe_collector.py': '64421012ff2bc905970a5d2d0dd72073755b81b6f42f8c182680fc91ef95ef34',
        'selfcheck_entry.py': 'a5eb301d77f92c1755c53c93e9d59ca60d5da5030b77f495d5859b2cf68012d8'}
for name, value in PINS.items():
    assert hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() == value, 'review subject changed'
sys.path.insert(0, str(SOURCE))
import binary_safe_collector as b
import selfcheck_entry as entry


def encoded(raw=b'org.westlake.imehost\0\0tail\0'):
    return raw.hex(' ').encode() + b.SHA_MARKER + hashlib.sha256(raw).hexdigest().encode() + b'  /proc/4344/cmdline\n'


class Review(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='t0-r5-review-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def read(self, payload, rc=0, remote=0, marker=True, collector_type=None, dest='raw'):
        c = (collector_type or b.BinarySafeCollector)(sys.executable, '61b0657200000000000000000324012c', self.base/dest)
        def remote_record(argv, **kwargs):
            token = re.search(r'__EXACT_READ_RC_[0-9a-f]+__', argv[-1])[0].encode()
            out = payload + (b'\n' + token + str(remote).encode() + b'\n' if marker else b'')
            return subprocess.CompletedProcess(argv, rc, out, b'')
        with patch('subprocess.run', side_effect=remote_record):
            result = c.read('host_cmdline', 'cat /proc/4344/cmdline')
        return c, result

    def test_raw_decoded_transport_and_audit_are_consistent(self):
        raw = b'org.westlake.imehost\0\0tail\0'
        c, (decoded, reading) = self.read(encoded(raw))
        self.assertEqual(decoded, raw)
        audit = json.loads((c.directory/'000-host_cmdline.binary.json').read_text())
        transport = json.loads((c.directory/'000-host_cmdline.json').read_text())
        self.assertEqual((c.directory/reading['stdout']['path']).read_bytes(), raw)
        self.assertEqual((c.directory/transport['stdout']['path']).read_bytes(), encoded(raw))
        self.assertEqual(audit['actual_argv'], transport['argv'])
        self.assertEqual(audit['logical_command'], reading['command'])
        self.assertEqual(audit['encoded_command'], transport['command'])
        self.assertEqual(reading['stdout']['sha256'], audit['board_sha256'])
        self.assertIn('set -o pipefail; cat /proc/4344/cmdline | od -An -v -tx1;', transport['command'])
        for ref in (reading['stdout'], reading['binary_transport'], transport['stdout'], transport['transport_stdout'], transport['stderr']):
            self.assertEqual(hashlib.sha256((c.directory/ref['path']).read_bytes()).hexdigest(),ref['sha256'])

    def test_decode_failures_preserve_raw_and_reject_without_decoded(self):
        p = encoded()
        faults = [p.replace(b'6f ',b'6 ',1), p.replace(b'6f ',b'gg ',1), p.replace(b'6f ',b'* ',1),
                  p.replace(b'/4344/',b'/4345/'),p.replace(b'R5_CMDLINE_SHA256=',b'OTHER='),p+b.SHA_MARKER,
                  p.replace(hashlib.sha256(b'org.westlake.imehost\0\0tail\0').hexdigest().encode(),b'0'*64),
                  b'garbage '+p,p+b'extra',b.SHA_MARKER+hashlib.sha256(b'').hexdigest().encode()+b'  /proc/4344/cmdline\n']
        for i,payload in enumerate(faults):
            with self.subTest(i=i), self.assertRaises(ValueError): self.read(payload,dest=str(i))
            d=self.base/str(i)
            audit=json.loads((d/'000-host_cmdline.binary.json').read_text())
            self.assertFalse(audit['accepted'])
            self.assertFalse(list(d.glob('*.decoded.stdout')))
            self.assertEqual((d/'000-host_cmdline.stdout').read_bytes(),payload)

    def test_transport_remote_and_missing_marker_refuse(self):
        for i,(rc,remote,marker) in enumerate([(7,0,True),(0,7,True),(0,0,False)]):
            with self.subTest(i=i),self.assertRaises(ValueError):self.read(encoded(),rc,remote,marker,dest=str(i))
            d=self.base/str(i);self.assertFalse(list(d.glob('*.decoded.stdout')))
            self.assertFalse(json.loads((d/'000-host_cmdline.binary.json').read_text())['accepted'])

    def test_noncanonical_logical_commands_do_not_call_transport(self):
        c=b.BinarySafeCollector(sys.executable,'61b0657200000000000000000324012c',self.base/'raw')
        with patch('subprocess.run',side_effect=AssertionError('forbidden local transport')):
            for text in ['cat /proc/1/cmdline','cat /proc/04344/cmdline','cat /proc/4344/cmdline; true','strings /proc/4344/cmdline','cat /proc/4344/cmdline\n']:
                with self.subTest(command=text),self.assertRaises(ValueError):c.read('host_cmdline',text)
        self.assertEqual(c.commands,[])

    def test_existing_decoded_evidence_not_overwritten(self):
        c=b.BinarySafeCollector(sys.executable,'61b0657200000000000000000324012c',self.base/'raw')
        dst=c.directory/'000-host_cmdline.decoded.stdout';dst.write_bytes(b'preexisting')
        def remote(argv,**kwargs):
            marker=re.search(r'__EXACT_READ_RC_[0-9a-f]+__',argv[-1])[0].encode()
            return subprocess.CompletedProcess(argv,0,encoded()+b'\n'+marker+b'0\n',b'')
        with patch('subprocess.run',side_effect=remote),self.assertRaises(FileExistsError):c.read('host_cmdline','cat /proc/4344/cmdline')
        self.assertEqual(dst.read_bytes(),b'preexisting')
        self.assertFalse(json.loads((c.directory/'000-host_cmdline.binary.json').read_text())['accepted'])

    def test_real_probe_original_bytes_hash_and_nul_preserved(self):
        p=WS/'westlake-harness/benchmark/2026-10-12-v1-seal-execution/61b-binary-read-probe/001-encoded-cmdline.stdout'
        original=p.read_bytes();m=re.search(rb'(?m)^([0-9a-f]{64})  /proc/4344/cmdline$',original)
        raw,sha=b.decode_hex(original[:m.start()]+b.SHA_MARKER+m[0]+b'\n','/proc/4344/cmdline')
        self.assertEqual(len(raw),275);self.assertIn(b'\0',raw)
        self.assertEqual(sha,'02d57f611f6aeb98c4c796a5925fff85f8907113ab924b42c66f5aa0d6ddbf5c')
        self.assertEqual(raw.split(b'\0')[0],b'org.westlake.imehost')

    def test_real_r3_reload_reinstalls_binary_collector(self):
        # Use real pinned R3 select_frozen/dependencies, not a substitute selector.
        p=self.base/'minimal-generator-selection.json'
        p.write_text(json.dumps({'generator':{'path':str(b.FROZEN/'realization.py'),'sha256':b.PINS['realization']}}))
        loader=b.load_pinned;seen=[]
        def load(path,name,expected):
            module=loader(path,name,expected)
            if name=='r5_activation_selfcheck':
                def seam_main(argv):
                    module.select_frozen(p)
                    self.assertIs(module.original_check.ReadOnlyCollector,b.BinarySafeCollector)
                    c,(raw,reading)=self.read(encoded(),collector_type=module.original_check.ReadOnlyCollector)
                    seen.append(raw);return 0
                module.main=seam_main
            return module
        with patch.object(b,'load_pinned',side_effect=load):
            self.assertEqual(entry.main(['--checker','activation']),0)
        self.assertEqual(seen,[b'org.westlake.imehost\0\0tail\0'])

    def test_install_wrong_selfcheck_sha_reject(self):
        p=self.base/'changed-selfcheck.py';p.write_text('# drift')
        class Fake:__file__=str(p)
        with self.assertRaisesRegex(ValueError,'exact frozen'):b.install(Fake)

if __name__=='__main__':unittest.main(verbosity=2)
