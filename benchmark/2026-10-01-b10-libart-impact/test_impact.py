import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import scan_classes as classes
import scan_bitvector as bits
import report_bits


def method(name, descriptor='()V', flags=0, code=1):
    return dict(name=name, descriptor=descriptor, flags=flags, code=code)


def node(parent='Ljava/lang/Object;', methods=(), interfaces=()):
    return dict(super=parent, interfaces=list(interfaces), methods=list(methods), fields=[])


def event(message, line=1, pid=123):
    return bits.first_fatal.classify.parse(f'10-01 04:30:00.000 {pid} 456 I C00f00/AppSpawnXJava: {message}', line)


class IdentityTests(unittest.TestCase):
    def test_jar_hash_drift_refused_before_scan(self):
        with tempfile.TemporaryDirectory() as temporary:
            apk = Path(temporary)/'fake.apk'
            apk.write_bytes(b'not-the-pinned-input')
            with self.assertRaisesRegex(ValueError, 'APK SHA drift'):
                classes.inspect(dict(path=str(apk),apk_sha256='0'*64,key='test'), {}, {}, {})

    def test_cross_dex_class_is_not_absent(self):
        app = 'Ltest/App;'
        known = 'Ltest/Known;'
        first = dict(classes={app:node('Landroid/app/Application;', [method('onCreate')])}, types=[app,known,'Ljava/lang/Object;'])
        second = dict(classes={known:node(methods=[method('<init>')])}, types=[known,'Ljava/lang/Object;'])
        dump = ["  Class descriptor  : 'Ltest/App;'\n", '  Virtual methods -\n', '    #0 : (in Ltest/App;)\n',
                "      name : 'onCreate'\n", "      type : '()V'\n", '000000: |0000: invoke-direct {v0}, Ltest/Known;.<init>:()V // method@0000\n']
        class Process:
            def __init__(self):
                self.stdout = io.StringIO(''.join(dump))
            def wait(self):
                return 0
        with tempfile.TemporaryDirectory() as temporary:
            apk = Path(temporary)/'test.apk'
            with zipfile.ZipFile(apk,'w') as archive:
                archive.writestr('classes.dex',b'first')
                archive.writestr('classes2.dex',b'second')
            xml = 'E: manifest\n  A: package="test"\n  E: application\n    A: android:name="test.App"\n'
            runtime = {'Ljava/lang/Object;':dict(super='',interfaces=[],methods=[]), 'Landroid/app/Application;':dict(super='Ljava/lang/Object;',interfaces=[],methods=['onCreate()V'])}
            with patch.object(classes,'dex_metadata',side_effect=[first,second]), patch.object(classes.subprocess,'check_output',return_value=xml), patch.object(classes.subprocess,'Popen',side_effect=lambda *args,**kwargs:Process()):
                result = classes.inspect(dict(path=str(apk),apk_sha256=classes.sha(apk.read_bytes()),key='test',package='test',cohort='fixture'),dict(aapt2='fixture',dexdump='fixture'),runtime,{})
            self.assertNotIn(known,result['absent_boot_and_app'])
            self.assertEqual(result['defined_classes'],2)

    def test_duplicate_definitions_refused(self):
        metadata = dict(classes={'Ltest/App;':node()})
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            classes.prepare_graph([('classes.dex',metadata),('classes2.dex',metadata)])

    def test_non_dex_refused(self):
        with self.assertRaisesRegex(ValueError,'DEX'):
            classes.dex_metadata(b'not-a-dex')


class ClassTests(unittest.TestCase):
    def fixture(self):
        metadata = dict(classes={'Ltest/App;':node('Landroid/app/Application;', [method('onCreate')]),
                                 'Ltest/Unused;':node(methods=[method('later', '(Lmissing/Type;)V')])})
        graph, sites = classes.prepare_graph([('classes.dex',metadata)])
        lines = ["Class descriptor  : 'Ltest/App;'", '  Virtual methods -', '    #0 : (in Ltest/App;)',
                 "      name : 'onCreate'", "      type : '()V'", '000000: |0000: invoke-static {v0}, Ljava/util/Objects;.require:(Lmissing/Type;)V // method@0000']
        classes.parse_code(lines,'classes.dex',graph,sites,{'Lmissing/Type;'},[])
        runtime = {'Landroid/app/Application;':dict(super='Ljava/lang/Object;',interfaces=[],methods=['onCreate()V']),
                   'Ljava/lang/Object;':dict(super='',interfaces=[],methods=[])}
        facts = dict(application_class='test.App',app_component_factory=None,application_meta_data={},components=[],main_activities=[])
        reached = classes.stages(graph,facts,runtime)
        return classes.classify_sites(sites,graph,reached,{'Lmissing/Type;'})

    def test_signature_reference_on_application_startup(self):
        rows = self.fixture()
        called = next(row for row in rows if row['kind']=='instruction')
        self.assertEqual(called['tier'],'startup-chain-candidate')
        self.assertEqual(called['missing'],['Lmissing/Type;'])
        self.assertIn('Ltest/App;->onCreate()V',called['path'])

    def test_unreached_is_not_later_only(self):
        later = next(row for row in self.fixture() if row['owner']=='Ltest/Unused;')
        self.assertEqual(later['tier'],'unanchored-not-proved-later')

    def test_array_component_descriptor(self):
        self.assertEqual(classes.descriptors('([[Lmissing/Type;I)[Ljava/lang/Object;'), {'Lmissing/Type;','Ljava/lang/Object;'})

    def test_manifest_alias_and_application_roots(self):
        text = '\n'.join(['E: manifest','  A: package="test"','  E: application','    A: android:name=".App"',
                          '    E: activity-alias','      A: android:name=".Alias"','      A: android:targetActivity=".Main"',
                          '      E: intent-filter','        E: action','          A: android:name="android.intent.action.MAIN"',
                          '        E: category','          A: android:name="android.intent.category.LAUNCHER"'])
        facts = classes.manifest(text)
        self.assertEqual(facts['main_activities'], ['test.Main'])
        self.assertEqual(facts['application_class'], 'test.App')

    def test_reachability_budget_does_not_invent_later_scope(self):
        graph, sites = classes.prepare_graph([('classes.dex',dict(classes={'Ltest/App;':node(methods=[method('later','(Lmissing/Type;)V')])}))])
        facts = dict(application_class=None,app_component_factory=None,application_meta_data={},components=[],main_activities=[])
        with patch.object(classes,'run_stages',side_effect=classes.ReachabilityBudgetExceeded):
            reached = classes.stages(graph,facts,{})
        self.assertTrue(reached.budget_truncated)
        self.assertEqual(classes.classify_sites(sites,graph,reached,{'Lmissing/Type;'})[0]['tier'],'unanchored-not-proved-later')


class BitVectorTests(unittest.TestCase):
    def test_zero_and_foreign_pid_are_not_positive(self):
        events = [event('[IFACE-RAW] klass=target.Class garbageSetBits=0'),event('[IFACE-BITS] klass=foreign.Class garbageSetBits=7',2,999),event('[IFACE-RAW] klass=target.Other garbageSetBits=3',3)]
        found = bits.extract(events,{123})
        self.assertEqual(len(found['positive']),1)
        self.assertEqual(len(found['zero']),1)
        self.assertEqual(found['foreign_pid_lines_excluded'],1)

    def test_before_terminal_is_suspected_not_causal(self):
        events = [event('[IFACE-RAW] klass=target.Class garbageSetBits=3'),event('FATAL EXCEPTION: main',2),event('java.lang.NullPointerException: target.Class',3)]
        found = bits.extract(events,{123})
        fatal = bits.first_fatal.analyze(events,{123})
        result = bits.correlate(found,fatal)
        self.assertEqual(result['status'],'suspected-class-linked-to-first-fatal')
        self.assertFalse(result['causal'])

    def test_alive_positive_is_only_exposure(self):
        events = [event('[IFACE-RAW] klass=target.Class garbageSetBits=3')]
        result = bits.correlate(bits.extract(events,{123}), bits.first_fatal.analyze(events,{123}))
        self.assertEqual(result['status'],'positive-exposure-without-observed-terminal')

    def test_after_terminal_not_a_first_fatal_victim(self):
        events = [event('FATAL EXCEPTION: main'),event('java.lang.NullPointerException: earlier',2),event('[IFACE-RAW] klass=target.Class garbageSetBits=3',3)]
        result = bits.correlate(bits.extract(events,{123}), bits.first_fatal.analyze(events,{123}))
        self.assertEqual(result['status'],'positive-only-after-or-other-PID-than-first-terminal')

    def test_other_pid_positive_is_not_first_terminal_victim(self):
        events = [event('[IFACE-RAW] klass=target.Class garbageSetBits=3',1,124), event('FATAL EXCEPTION: main',2)]
        result = bits.correlate(bits.extract(events,{123,124}),bits.first_fatal.analyze(events,{123,124}))
        self.assertEqual(result['status'],'positive-only-after-or-other-PID-than-first-terminal')
        self.assertFalse(result['causal'])

    def test_report_refuses_partial_facts(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            report_bits.summarize(dict(mode='partial-unverified-not-final'))

    def test_machine_table_keeps_numeric_pids(self):
        text = report_bits.report.csv_text([dict(key='test',target_pids=[123,124])])
        self.assertEqual(text,'key,target_pids\ntest,123;124\n')

    def test_compact_evidence_keeps_all_coordinates(self):
        events = [event('[IFACE-RAW] klass=target.Class garbageSetBits=3'), event('[IFACE-RAW] klass=target.Clean garbageSetBits=0',2)]
        observations = bits.extract(events,{123})
        facts = dict(rows=[dict(key='test',bits=observations,correlation=bits.correlate(observations,bits.first_fatal.analyze(events,{123})))])
        encoded = report_bits.compact(facts,'0'*64)
        self.assertEqual(encoded['classes'],['target.Class','target.Clean'])
        self.assertEqual(encoded['rows'][0]['bits']['positive'][0], [1,'10-01 04:30:00.000',123,456,0,3])
        self.assertEqual(encoded['rows'][0]['bits']['zero'][0][-1],0)

    def test_wrong_signoff_state_refused(self):
        signed = dict(schema='outer-signoff-v1',state=dict(name='cv2'),keys=[])
        with self.assertRaisesRegex(ValueError,'Wrong signed'):
            report_bits.bind_signoff(dict(state=bits.STATE),json.dumps(signed).encode())


class RunTests(unittest.TestCase):
    def create(self, root, state=None):
        folder = root/'run'/'serial'
        folder.mkdir(parents=True)
        record = dict(key='test',package='test.package',apk_sha256='0'*64,status='foreground_unconfirmed')
        (folder/'plan.json').write_text(json.dumps(dict(apps=[record])))
        (folder/'facts.txt').write_text('\n'.join(field+' fingerprint='+pin for field,pin in (state or bits.STATE).items()))
        (folder/'record.json').write_text(json.dumps(record))
        return dict(test=record)

    def test_incomplete_final_refused_and_partial_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)/'5ea-seq-v1'
            expected = self.create(root)
            expected['missing'] = dict(package='missing',apk_sha256='0'*64)
            with self.assertRaisesRegex(ValueError,'incomplete'):
                bits.admit([root],expected)
            _, coverage = bits.admit([root],expected,full=False)
            self.assertFalse(coverage['full'])
            self.assertEqual(coverage['unobserved_keys'],['missing'])

    def test_invalid_concurrent_root_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)/'5ea-seq-v1'
            expected = self.create(root)
            (root/'INVALID-concurrent-same-board.txt').write_text('invalid')
            with self.assertRaisesRegex(ValueError,'Invalid'):
                bits.admit([root],expected)

    def test_state_and_apk_drift_refused(self):
        for mode in ['state','apk']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)/'5ea-seq-v1'
                expected = self.create(root,{'RUNTIME':'0'*12,'BOOTIMAGE':'0'*12} if mode=='state' else None)
                if mode=='apk':
                    expected['test']['apk_sha256'] = 'f'*64
                with self.assertRaises(ValueError):
                    bits.admit([root],expected)

    def test_duplicate_attempts_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary)/'5ea-seq-v1'
            second = Path(temporary)/'5cd-seq-cv2'
            expected = self.create(first)
            self.create(second)
            with self.assertRaisesRegex(ValueError,'Duplicate'):
                bits.admit([first,second],expected)

    def test_interrupted_cleanup_requires_completed_probe_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)/'5cd-seq-v1'
            expected = self.create(root)
            path = root/'run/serial/record.json'
            record = json.loads(path.read_text())
            record['status'] = 'batch_interrupted'
            path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                bits.admit([root],expected)
            record['diagnostics'] = dict(complete=True)
            record['screenshots'] = [dict(captured=True,scheduled_seconds=20)]
            path.write_text(json.dumps(record))
            selected, coverage = bits.admit([root],expected)
            self.assertEqual(set(selected),{'test'})
            self.assertTrue(coverage['full'])


if __name__=='__main__':
    unittest.main()
