import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('n11d_hook',H/'window_hook.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

class Window(unittest.TestCase):
    def test_same_bind_and_output_for_apply_and_rollback(self):
        with patch.object(h.subprocess,'run') as run:
            run.return_value.returncode=0
            h.sweep('serial',Path('/tmp/n11d-test'))
            first=run.call_args.args[0]
            h.sweep('serial',Path('/tmp/n11d-test'),True)
            second=run.call_args.args[0]
        for option in ['--bind','--out']:
            self.assertEqual(first[first.index(option)+1],second[second.index(option)+1])
        self.assertIn('--rollback-only',second)
        self.assertEqual(second[second.index('--rollback-runtime-fp')+1],'565fc6fdc116')

    def test_hard_control_and_advisory_zigzag_are_actual_flags(self):
        smoke=json.loads((H/'smoke.json').read_text())
        controls={k for g in smoke['groups'] if g.get('controls') for k in g['keys']}
        self.assertEqual(controls,{'helloworld'})
        self.assertNotIn('expect_copies',smoke['probe'])
        recovery=json.loads((H/'restored-smoke.json').read_text())
        self.assertEqual(recovery['expect']['runtime_fp'],'565fc6fdc116')
        self.assertEqual(recovery['probe']['expect_copies']['liboh_adapter_bridge.so'],2)

    def test_call_diffs_are_only_log_dependencies_in_two_expected_functions(self):
        report=json.loads((H/'abi-diff.json').read_text())
        self.assertFalse(report['removed'] or report['added'] or report['drift'])
        self.assertEqual({r['function'] for r in report['call_diffs']},{'RealOpenLocalNow','WLSCPL_LoadSealedProvider'})
        for row in report['call_diffs']:
            self.assertFalse(row['removed_callees'])
            self.assertLessEqual(set(row['added_callees']),{'HiLogPrint','dlerror'})

if __name__=='__main__':unittest.main()
