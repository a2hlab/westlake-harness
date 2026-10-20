import re
import unittest
from pathlib import Path
import hilog_tail as h

class Tests(unittest.TestCase):
    def test_real_rc0_error31(self):
        raw = (Path(__file__).parent/'fixtures/t23-hilog-error.txt').read_bytes()
        body = raw.split(b'T23_HILOG_START\n')[1].split(b'T23_HILOG_RC=')[0]
        rc = int(re.search(rb'T23_HILOG_RC=(-?\d+)', raw)[1])
        r = h.analyze(body,b'',0,rc,True,7655)
        self.assertEqual(rc,0); self.assertEqual(r['body_error_codes'],[-31])
        self.assertEqual(r['status'],'REJECTED_OR_PARTIAL')
        self.assertIsNone(r['first_timestamp_epoch'])
    def test_plan(self):
        a = h.plan(7655,2000)['argv']
        self.assertNotIn('-x',a); self.assertEqual(a[a.index('-z')+1],'2000')
        self.assertEqual(a[a.index('-P')+1],'7655')
    def test_time_coverage_and_gone_retained(self):
        raw = b'1792467138.123 7655 100 I C00f00: one\n1792467141.456 7655 100 E C00f00: two\n'
        r = h.analyze(raw,b'',0,0,True,7655,'gone')
        self.assertEqual(r['status'],'COLLECTED'); self.assertEqual(r['body_bytes'],len(raw))
        self.assertEqual(r['first_timestamp_epoch'],'1792467138.123')
        self.assertEqual(r['last_timestamp_epoch'],'1792467141.456')
        self.assertFalse(r['elapsed_used_as_coverage']); self.assertEqual(r['postguard'],'gone')
    def test_partial(self):
        self.assertEqual(h.analyze(b'partial',b'',124,None,False,7655)['status'],'REJECTED_OR_PARTIAL')
    def test_empty_unknown(self):
        r=h.analyze(b'',b'',0,0,True,7655); self.assertIsNone(r['last_timestamp_epoch'])
    def test_wrong_pid(self):
        self.assertEqual(h.analyze(b'1792467138.123 999 100 I x\n',b'',0,0,True,7655)['status'],'REJECTED_OR_PARTIAL')
    def test_stderr_error(self):
        self.assertEqual(h.analyze(b'',b'[CODE: -31]',0,0,True,7655)['status'],'REJECTED_OR_PARTIAL')

if __name__ == '__main__': unittest.main()
