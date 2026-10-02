#!/usr/bin/env python3
"""open_site_scan.py: lists open sites with their namespace / path / flags, and finds a library opened into two namespaces.

The synthetic cases always run. The known-answer cases run where the deployed binaries are present: the signed U9
appspawn-x has the six sites cx-t0 disassembled by hand for the N11h blueprint, U9 host + child open
liboh_android_runtime.so into two namespaces (the white-window double copy), the N11f child still tail-calls plain
dlopen at 0x35e8 and the N11g child does not.
"""
import sys
import unittest
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab_paths  # noqa: E402
import open_site_scan as oss  # noqa: E402

WS = lab_paths.workspaces()
U9 = WS / oss.U9_GENERATION
HOST, CHILD = (U9 / b for b in oss.U9_BINARIES)
N11F = WS / 'westlake-inputs/generations/n11f-u9-owner-callback-v1/build/candidate/libwestlake_android_child.z.so'
N11G = WS / 'westlake-inputs/generations/n11g-u9-sealed-owner-v1/build/candidate/libwestlake_android_child.z.so'
R2 = WS / 'westlake-inputs/generations/u10-j37465d6d-c015aa3a6-p621caec4-v3/bundle/native/payload/runtime/appspawn-x'
R3 = WS / 'westlake-inputs/generations/u10.1-j5ae3dd29-c015aa3a6-p0718f01e-r3-v1/bundle/native/payload/runtime/appspawn-x'
SPILL = WS / 'westlake-harness-bms/benchmark/2026-10-02-u11-native-batch/.artifacts/r1/host/appspawn-x-candidate'
PINS = {HOST: '1d3b08816969369a1941a3877a8a3d6addf604dd830bd3753bbd883ea74aa8b3',
        R2: '71901abc64e2474b582579b7093b84c6e2d7088950086e78f7a0551b04e46298',
        R3: '65cc3535ebf22bdf664b3c8ddf932ccd7f42d936be1c861e1221a80b12a00284',
        SPILL: '67753f7700887e4510e215abb2c4791534bb46b46c69e6f4775559c86653d55e'}


def known_scan(filename):
    if hashlib.sha256(filename.read_bytes()).hexdigest() != PINS[filename]:
        raise AssertionError('known-answer ELF identity mismatch: ' + str(filename))
    sites, elf = oss.scan(filename)
    return sites, elf.namespace_edges, oss.findings([(filename, sites, elf)], [])


def assembly(name, rows, base=0x1000):
    return f'{base:016x} <{name}>:\n' + ''.join(
        f'    {base + index * 4:x}: 00 00 00 00\t{mnem}\t{operands}\n'
        for index, (mnem, operands) in enumerate(rows))


class NamespaceElf:
    strings = {0x7000: 'application.demo', 0x7100: 'westlake.sealed.child',
               0x7200: 'libone.so:libtwo.so', 0x7300: 'libtwo.so'}

    def cstring(self, address):
        return self.strings.get(address)

    def symbol(self, address):
        return None

    def has_string(self, value):
        return False


def synthetic_scan(text):
    sites, elf = oss.scan('synthetic', text, NamespaceElf())
    return sites, elf.namespace_edges, oss.findings([('synthetic', sites, elf)], [])


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


class NamespaceListing(unittest.TestCase):
    def test_cli_text_and_json_preserve_open_sites(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'scan.json'
            command = [sys.executable, str(Path(oss.__file__)), str(HOST), '--json', str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('== namespace edges', result.stdout)
            self.assertIn('DEFAULT-NS', result.stdout)
            data = json.loads(output.read_text())
            self.assertEqual(len(data['binaries'][0]['sites']), 6)
            self.assertEqual(len(data['binaries'][0]['namespace_edges']), 14)

    def test_u9_known_namespace_pcs_and_names(self):
        _, edges, _ = known_scan(HOST)
        by_pc = {edge['pc']: edge for edge in edges}
        for callee, pcs in {'dlns_init': ['0xcacc', '0xcb7c'], 'dlns_create2': ['0xcadc', '0xcb8c'],
                            'dlns_inherit': ['0xcc64', '0xccd8', '0xccf0'], 'dlns_get': ['0xccac', '0xccc0']}.items():
            for pc in pcs:
                self.assertEqual(by_pc[pc]['callee'], callee)
        self.assertEqual(by_pc['0xccac']['name'], ['default'])
        self.assertEqual(by_pc['0xccc0']['name'], ['westlake.sealed.child'])
        self.assertEqual(by_pc['0xccf0']['parent_identity'], ['name:westlake.sealed.child'])
        self.assertIn('libbionic_compat.so', by_pc['0xccf0']['shared'][0])
        self.assertEqual(len(edges), 14)

    def test_mixed_register_pair_reload_is_a_stack_slot(self):
        sites, _, _ = known_scan(SPILL)
        site = next(site for site in sites if site['pc'] == '0xcf0c')
        self.assertEqual(site['namespace'], ['stack:frame slot [sp, #24]'])
        instructions = oss.parse_disassembly(assembly('Reload', [('ldp', 'x21, x13, [sp, #24]'), ('nop', '')]))['Reload']
        self.assertEqual(oss.resolve(instructions, 1, 13, NamespaceElf()), [('stack', 'frame slot [sp, #24]+8')])

    def test_all_namespace_api_families_and_tail_calls(self):
        rows = [('mov', 'x0, x19'), ('adrp', 'x1, 0x7000'), ('add', 'x1, x1, #0'), ('bl', '0x9000 <dlns_init@plt>'),
                ('mov', 'x0, x19'), ('bl', '0x9000 <dlns_create@plt>'),
                ('mov', 'x0, x19'), ('bl', '0x9000 <dlns_create2@plt>'),
                ('mov', 'x0, x19'), ('bl', '0x9000 <dlns_set_namespace_custom_paths@plt>'),
                ('mov', 'x0, x19'), ('adrp', 'x2, 0x7200'), ('add', 'x2, x2, #0'), ('b', '0x9000 <dlns_inherit@plt>')]
        _, edges, _ = synthetic_scan(assembly('Edges', rows))
        self.assertEqual([edge['callee'] for edge in edges], ['dlns_init', 'dlns_create', 'dlns_create2', 'dlns_set_namespace_custom_paths', 'dlns_inherit'])
        self.assertTrue(edges[-1]['tail_call'])
        self.assertEqual(edges[-1]['shared'], ['libone.so:libtwo.so'])


class NamespaceRepeat(unittest.TestCase):
    def test_unreachable_helper_body_is_not_projected(self):
        text = assembly('Caller', [('mov', 'x19, x0'), ('mov', 'x0, x19'), ('bl', '0x2000 <Helper>'), ('ret', '')])
        text += assembly('Helper', [('ret', ''), ('mov', 'x19, x0'), ('mov', 'x0, x19'), ('bl', '0x9000 <dlns_inherit@plt>')], 0x2000)
        _, edges, found = synthetic_scan(text)
        self.assertFalse(any(edge.get('projected') for edge in edges))
        self.assertFalse(any(row['kind'] == 'INHERIT-REPEAT' for row in found))

    def test_deployed_r2_cross_function_repeat_and_r3_negative(self):
        _, edges, found = known_scan(R2)
        repeated = [row for row in found if row['kind'] == 'INHERIT-REPEAT']
        self.assertEqual(len(repeated), 1)
        self.assertEqual(repeated[0]['parent'], ['name:westlake.sealed.child'])
        self.assertEqual(repeated[0]['first']['pc'], '0xd008')
        self.assertEqual(repeated[0]['second']['via_call'], {'callee': 'U10ShareResidentCompat', 'inherit_pc': '0xd694', 'depth': 1})
        projected = [edge for edge in edges if edge.get('via_call', {}).get('callee') == 'U10ShareResidentCompat']
        self.assertEqual(len(projected), 1)
        self.assertEqual(projected[0]['pc'], '0xcf80')
        _, _, r3_found = known_scan(R3)
        self.assertFalse(any(row['kind'] == 'INHERIT-REPEAT' for row in r3_found))

    def test_name_normalization_and_direct_caller(self):
        caller = [('mov', 'x19, x0'), ('mov', 'x0, x19'), ('adrp', 'x1, 0x7000'), ('add', 'x1, x1, #0'),
                  ('bl', '0x9000 <dlns_init@plt>'), ('adrp', 'x0, 0x7100'), ('add', 'x0, x0, #0'),
                  ('add', 'x1, sp, #64'), ('bl', '0x9000 <dlns_get@plt>'), ('mov', 'x0, x19'),
                  ('add', 'x1, sp, #64'), ('adrp', 'x2, 0x7200'), ('add', 'x2, x2, #0'),
                  ('bl', '0x9000 <dlns_inherit@plt>'), ('mov', 'x0, x19'), ('bl', '0x2000 <Helper>'), ('ret', '')]
        helper = [('mov', 'x20, x0'), ('adrp', 'x0, 0x7100'), ('add', 'x0, x0, #0'),
                  ('add', 'x1, sp, #32'), ('bl', '0x9000 <dlns_get@plt>'), ('mov', 'x0, x20'),
                  ('add', 'x1, sp, #32'), ('adrp', 'x2, 0x7300'), ('add', 'x2, x2, #0'),
                  ('bl', '0x9000 <dlns_inherit@plt>'), ('ret', '')]
        _, _, found = synthetic_scan(assembly('Caller', caller) + assembly('Helper', helper, 0x2000))
        repeated = [row for row in found if row['kind'] == 'INHERIT-REPEAT']
        self.assertEqual(len(repeated), 1)
        self.assertEqual(repeated[0]['child'], ['name:application.demo'])
        self.assertEqual(repeated[0]['second']['shared'], ['libtwo.so'])
        self.assertEqual(repeated[0]['second']['via_call']['depth'], 1)

    def test_disjoint_branches_and_unknown_names_do_not_repeat(self):
        rows = [('mov', 'x19, x0'), ('mov', 'x20, x1'), ('cbz', 'x2, 0x1020'),
                ('mov', 'x0, x19'), ('mov', 'x1, x20'), ('bl', '0x9000 <dlns_inherit@plt>'),
                ('ret', ''), ('nop', ''), ('mov', 'x0, x19'), ('mov', 'x1, x20'),
                ('b', '0x9000 <dlns_inherit@plt>')]
        _, _, found = synthetic_scan(assembly('Disjoint', rows))
        self.assertFalse(any(row['kind'] == 'INHERIT-REPEAT' for row in found))
        _, _, unknown = synthetic_scan(assembly('Unknown', [('bl', '0x9000 <other@plt>'),
            ('bl', '0x9000 <dlns_inherit@plt>'), ('bl', '0x9000 <dlns_inherit@plt>')]))
        self.assertFalse(any(row['kind'] == 'INHERIT-REPEAT' for row in unknown))


class NamespaceFlow(unittest.TestCase):
    def test_bit_branch_uses_target_not_bit_immediate(self):
        for mnemonic in ['tbz', 'tbnz']:
            text = assembly('Bits', [(mnemonic, 'w0, #0x0, 0x100c <Bits+0xc>'), ('ret', ''), ('nop', ''), ('ret', '')])
            instructions = oss.parse_disassembly(text)['Bits']
            self.assertEqual(set(oss.successors(instructions)[0]), {1, 3})

    def test_u9_numeric_after_sites_are_not_reachable(self):
        _, edges, found = known_scan(HOST)
        for pc in ['0xccd8', '0xccf0']:
            edge = next(edge for edge in edges if edge['pc'] == pc)
            earlier = next(opened for opened in edge['opens'] if opened['pc'] == '0xcc90')
            self.assertTrue(earlier['pc_before_inherit'])
            self.assertFalse(earlier['reachable'])
            self.assertFalse(any(row['kind'] == 'INHERIT-AFTER-OPEN' and row['site'].endswith('@' + pc) for row in found))
        self.assertTrue(any(row['kind'] == 'INHERIT-AFTER-OPEN' and row['site'].endswith('@0xcc64') and row['open_pc'] == '0xcd70' for row in found))

    def test_reachable_and_unreachable_later_inherit(self):
        prefix = [('mov', 'x19, x0'), ('mov', 'x20, x1'), ('mov', 'x0, x19'),
                  ('mov', 'x1, x20'), ('mov', 'w2, #2'), ('bl', '0x9000 <dlopen_ns@plt>')]
        inherit = [('mov', 'x0, x19'), ('mov', 'x1, x20'), ('bl', '0x9000 <dlns_inherit@plt>'), ('ret', '')]
        for terminator, expected in [(('nop', ''), True), (('ret', ''), False), (('b', '0x102c <Flow+0x2c>'), False),
                                     (('cbz', 'x3, 0x102c <Flow+0x2c>'), True)]:
            with self.subTest(terminator=terminator):
                _, edges, found = synthetic_scan(assembly('Flow', prefix + [terminator] + inherit + [('ret', '')]))
                edge = next(edge for edge in edges if edge['callee'] == 'dlns_inherit')
                self.assertEqual(edge['opens'][0]['reachable'], expected)
                self.assertEqual(any(row['kind'] == 'INHERIT-AFTER-OPEN' for row in found), expected)

    def test_different_namespace_is_not_after_open(self):
        rows = [('mov', 'x19, x0'), ('mov', 'x20, x1'), ('mov', 'x0, x19'),
                ('bl', '0x9000 <dlopen_ns@plt>'), ('mov', 'x0, x20'), ('bl', '0x9000 <dlns_inherit@plt>')]
        _, edges, found = synthetic_scan(assembly('Different', rows))
        self.assertEqual(edges[-1]['opens'], [])
        self.assertFalse(any(row['kind'] == 'INHERIT-AFTER-OPEN' for row in found))


if __name__ == '__main__':
    unittest.main()
