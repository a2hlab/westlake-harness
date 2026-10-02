import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('review_wait',HERE/'review_wait.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ReviewWaitTests(unittest.TestCase):
    def test_timeout_bounded_without_waiting_wall_clock(self):
        with tempfile.TemporaryDirectory() as d:
            clock=[0.0];slept=[]
            def sleep(seconds):
                slept.append(seconds);clock[0]+=seconds
            self.assertFalse(m.wait_for_decision(Path(d)/'absent.json',12,lambda:clock[0],sleep))
            self.assertEqual(clock[0],12);self.assertLessEqual(max(slept),5)

    def test_partial_decision_waits_for_atomic_complete_write(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'decision.json';p.write_text('{');clock=[0.0]
            def sleep(seconds):
                clock[0]+=seconds;p.write_text('{"signed_by":"outer(claude)"}')
            self.assertTrue(m.wait_for_decision(p,12,lambda:clock[0],sleep))
            self.assertEqual(clock[0],5)

    def run_fixture(self,passed,notify_error=False):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'runner/smoke').mkdir(parents=True);(root/'post-apply').mkdir()
            (root/'runner/smoke/smoke-result.json').write_text(json.dumps({'passed':passed}))
            (root/'post-apply/candidate-318.json').write_text('{"diff":{},"absent":[],"identity_assertions":318}')
            (root/'window-input.json').write_text('{}')
            plan=root/'plan.json';plan.write_text(json.dumps({'before_unlock_restored_spec':'$TEST_REVIEW_ROOT/restored.json','stage_a_decision':'$TEST_REVIEW_ROOT/A.json'}))
            argv=['review_wait','--serial','serial','--root',str(root),'--plan',str(plan)]
            with patch.dict(os.environ,{'TEST_REVIEW_ROOT':str(root)}),patch('sys.argv',argv),patch.object(m,'wait_for_decision',return_value=False) as wait,patch.object(m.subprocess,'run',side_effect=RuntimeError('board append failed') if notify_error else None),patch.object(m.hook,'finish') as finish:
                if notify_error:
                    with self.assertRaisesRegex(RuntimeError,'board append failed'):m.main()
                else:m.main()
                finish.assert_called_once_with('serial',root,root/'restored.json',root/'outer-promotion.json',root/'A.json')
                self.assertEqual(wait.call_count,1 if passed and not notify_error else 0)
                if passed:
                    x=json.loads((root/'approval-ready.json').read_text());self.assertEqual(x['rollback_reserve_minutes'],6)
                    self.assertLessEqual(x['wait_until_epoch']-m.time.time(),1200)

    def test_expired_review_always_runs_finish(self):self.run_fixture(True)
    def test_failed_smoke_does_not_wait(self):self.run_fixture(False)
    def test_notification_failure_still_runs_finish(self):self.run_fixture(True,True)


if __name__=='__main__':unittest.main()
