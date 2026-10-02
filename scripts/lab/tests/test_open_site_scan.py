#!/usr/bin/env python3
"""open_site_scan.py: lists open sites with their namespace / path / flags, and finds a library opened into two namespaces.

The synthetic cases always run. The known-answer cases run where the deployed binaries are present: the signed U9
appspawn-x has the six sites cx-t0 disassembled by hand for the N11h blueprint, U9 host + child open
liboh_android_runtime.so into two namespaces (the white-window double copy), the N11f child still tail-calls plain
dlopen at 0x35e8 and the N11g child does not.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab_paths  # noqa: E402
import open_site_scan as oss  # noqa: E402

WS = lab_paths.workspaces()
U9 = WS / oss.U9_GENERATION
HOST, CHILD = (U9 / b for b in oss.U9_BINARIES)
N11F = WS / 'westlake-inputs/generations/n11f-u9-owner-callback-v1/build/candidate/libwestlake_android_child.z.so'
N11G = WS / 'westlake-inputs/generations/n11g-u9-sealed-owner-v1/build/candidate/libwestlake_android_child.z.so'


class FakeElf:
    strings = {0x6004: '/system/android/lib64/liboh_android_runtime.so', 0x6100: '/a/libone.so', 0x6200: '/b/libtwo.so'}

    def cstring(self, va):
        return self.strings.get(va)

    def symbol(self, va):
        return 'closure_namespace' if va == 0x9000 else None

    def has_string(self, s):
        return 'liboh_android_runtime.so' in s


HOST_TEXT = """
0000000000001000 <Create>:
    1000: 00 00 00 00  \tmov\tx22, x1
    1004: 00 00 00 00  \tldp\tx22, x21, [sp, #16]
    1008: 00 00 00 00  \tadrp\tx1, 0x6000 <Create+0x10>
    100c: 00 00 00 00  \tadd\tx1, x1, #4
    1010: 00 00 00 00  \tmov\tx0, x22
    1014: 00 00 00 00  \tmov\tw2, #258
    1018: 00 00 00 00  \tbl\t0x2000 <dlopen_ns@plt>
    101c: 00 00 00 00  \tadrp\tx8, 0x6000 <Create+0x20>
    1020: 00 00 00 00  \tadd\tx8, x8, #256
    1024: 00 00 00 00  \tadrp\tx9, 0x6000 <Create+0x20>
    1028: 00 00 00 00  \tadd\tx9, x9, #512
    102c: 00 00 00 00  \tcsel\tx1, x9, x8, ne
    1030: 00 00 00 00  \tmov\tx0, x22
    1034: 00 00 00 00  \tmov\tw2, #6
    1038: 00 00 00 00  \tbl\t0x2000 <dlopen_ns@plt>
"""
CHILD_TEXT = """
0000000000003000 <Callback>:
    3000: 00 00 00 00  \tldp\tx29, x30, [sp], #16
    3004: 00 00 00 00  \tb\t0x2100 <dlopen@plt>
0000000000003100 <Local>:
    3100: 00 00 00 00  \tadrp\tx0, 0x9000 <Local+0x10>
    3104: 00 00 00 00  \tadd\tx0, x0, #0
    3108: 00 00 00 00  \tadrp\tx1, 0x6000 <Local+0x10>
    310c: 00 00 00 00  \tadd\tx1, x1, #4
    3110: 00 00 00 00  \tmov\tw2, #2
    3114: 00 00 00 00  \tbl\t0x2000 <dlopen_ns@plt>
"""


class Synthetic(unittest.TestCase):
    def setUp(self):
        self.host, _ = oss.scan('host', HOST_TEXT, FakeElf())
        self.child, _ = oss.scan('child', CHILD_TEXT, FakeElf())

    def test_literal_namespace_flags_and_epilogue_skip(self):
        s = self.host[0]
        self.assertEqual((s['function'], s['pc'], s['callee']), ('Create', '0x1018', 'dlopen_ns'))
        self.assertEqual(s['path'], ['/system/android/lib64/liboh_android_runtime.so'])
        self.assertEqual(s['namespace'], ['param:x1'])            # the epilogue ldp at 0x1004 is not the definition
        self.assertEqual(s['flags'], ['0x102=NOW|GLOBAL'])

    def test_csel_merges_both_literals(self):
        self.assertEqual(sorted(self.host[1]['path']), ['/a/libone.so', '/b/libtwo.so'])
        self.assertEqual(self.host[1]['flags'], ['0x6=NOW|NOLOAD'])

    def test_tail_call_and_global_namespace(self):
        tail, local = self.child
        self.assertTrue(tail['tail_call'])
        self.assertEqual(tail['namespace'], ['caller-default'])
        self.assertEqual(local['namespace'], ['global:closure_namespace'])

    def test_two_namespaces_for_one_library_is_confirmed_multi_ns(self):
        found = oss.findings([('host', self.host, FakeElf()), ('child', self.child, FakeElf())],
                             ['liboh_android_runtime.so'])
        multi = [f for f in found if f['kind'] == 'MULTI-NS' and f['library'] == 'liboh_android_runtime.so']
        self.assertEqual([f['confidence'] for f in multi], ['confirmed'])
        self.assertTrue(any(f['kind'] == 'DEFAULT-NS' and f['tail_call'] for f in found))
        # the NOLOAD csel site never creates a copy, so its libraries are not counted
        self.assertFalse(any(f['kind'] == 'MULTI-NS' and f['library'] in ('libone.so', 'libtwo.so') for f in found))


@unittest.skipUnless(HOST.exists() and CHILD.exists(), 'signed U9 generation not on this machine')
class SignedU9(unittest.TestCase):
    def test_host_has_the_six_hand_disassembled_sites(self):
        sites, _ = oss.scan(HOST)
        got = [(s['function'], s['pc'], s['callee']) for s in sites]
        self.assertEqual(got, [('main', '0xc51c', 'dlopen'),
                               ('StockCreateConfiguredNamespaces', '0xcb2c', 'dlopen_ns'),
                               ('StockCreateConfiguredNamespaces', '0xcc90', 'dlopen_ns'),
                               ('StockCreateConfiguredNamespaces', '0xcd70', 'dlopen_ns'),
                               ('StockCreateConfiguredNamespaces', '0xce10', 'dlopen_ns'),
                               ('StockOpenNamespace', '0xd098', 'dlopen_ns')])
        by_pc = {s['pc']: s for s in sites}
        self.assertEqual(by_pc['0xcd70']['path'], ['/system/android/lib64/liboh_android_runtime.so'])
        self.assertEqual(by_pc['0xce10']['path'], ['/system/lib64/libOpenSLES.so'])
        self.assertEqual(len(by_pc['0xcc90']['path']), 2)

    def test_runtime_reaches_host_and_child_namespaces(self):
        results = [(p, *oss.scan(p)) for p in (HOST, CHILD)]
        found = oss.findings(results, ['liboh_android_runtime.so'])
        multi = [f for f in found if f['kind'] == 'MULTI-NS' and f['library'] == 'liboh_android_runtime.so']
        self.assertEqual(multi[0]['confidence'], 'confirmed')
        resolved = {r['site'] for r in multi[0]['reaches'] if r['how'] == 'resolved'}
        self.assertIn('appspawn-x:StockCreateConfiguredNamespaces@0xcd70', resolved)
        self.assertIn('libwestlake_android_child.z.so:RealOpenLocalNow@0x41c8', resolved)


@unittest.skipUnless(N11F.exists() and N11G.exists(), 'N11f / N11g candidates not on this machine')
class ChildCallbackFix(unittest.TestCase):
    def test_n11f_tail_calls_plain_dlopen_and_n11g_does_not(self):
        f_sites, _ = oss.scan(N11F)
        g_sites, _ = oss.scan(N11G)
        f_cb = [s for s in f_sites if s['function'] == 'WLSCPL_OpenPreparedNamespace']
        g_cb = [s for s in g_sites if s['function'] == 'WLSCPL_OpenPreparedNamespace']
        self.assertEqual([(s['pc'], s['callee'], s['tail_call']) for s in f_cb], [('0x35e8', 'dlopen', True)])
        self.assertEqual([(s['callee'], s['namespace']) for s in g_cb], [('dlopen_ns', ['global:closure_namespace'])])


if __name__ == '__main__':
    unittest.main()
