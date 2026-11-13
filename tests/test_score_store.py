"""device/play/score_store.py: Play client-library calls and callbacks per service family, from app hilogs."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / 'device' / 'play' / 'score_store.py'


def load():
    spec = importlib.util.spec_from_file_location('score_store', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def line(pid, service, message, tag='PlayCore'):
    return (f'11-12 06:55:04.343 {pid} {pid + 1} I C00f00/{tag}: UID: [20010054]  PID: [{pid}] '
            f'{service} : {message}')


class ScoreStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.logs = Path(self.tmp.name)
        self.score = load()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def app(self, package, *lines):
        (self.logs / f'hk-{package}.hilog').write_text('\n'.join(lines) + '\n')

    def test_callbacks_count_with_their_service(self):
        self.app('a.update', line(10, 'AppUpdateService', 'requestUpdateInfo(a.update)'),
                 line(10, 'OnRequestInstallCallback', 'onRequestInfo'))
        self.app('b.integrity', line(20, 'IntegrityService', 'requestIntegrityToken(IntegrityTokenRequest{nonce=x})'),
                 line(20, 'OnRequestIntegrityTokenCallback', 'onRequestIntegrityToken'),
                 line(20, 'IntegrityService', 'ServiceConnectionImpl.onServiceConnected(ComponentInfo{x/y})'))
        calls, callbacks, errors, _ = self.score.score(self.logs)
        self.assertEqual(calls['in-app update'], {'a.update'})
        self.assertEqual(dict(callbacks['in-app update']), {'onRequestInfo': {'a.update'}})
        # A service connection is not an answer.
        self.assertEqual(dict(callbacks['integrity']), {'onRequestIntegrityToken': {'b.integrity'}})
        self.assertEqual(dict(errors), {})

    def test_errors_and_families(self):
        self.app('c.assets', line(30, 'AssetPackServiceImpl', 'getPackStates([x])'),
                 line(30, 'AssetPackServiceImpl', 'onError(-2)'))
        self.app('d.split', line(40, 'SplitInstallService', 'startInstall([m],[])'),
                 line(40, 'SplitInstallService', 'onStartInstall(1)'),
                 'unrelated line without the tag')
        self.app('e.express', line(50, 'ExpressIntegrityService', 'warmUpIntegrityToken failed: -12'))
        calls, callbacks, errors, _ = self.score.score(self.logs)
        self.assertEqual(dict(errors['asset delivery']), {'-2': {'c.assets'}})
        self.assertEqual(dict(callbacks['split install']), {'onStartInstall': {'d.split'}})
        self.assertEqual(dict(errors['express integrity']), {'-12': {'e.express'}})
        self.assertNotIn('integrity', calls)

    def test_review_callback_counts_for_review(self):
        # Play Core's review callback logs under the in-app update callback's class name.
        self.app('h.review', line(80, 'ReviewService', 'requestInAppReview (h.review)'),
                 line(80, 'OnRequestInstallCallback', 'onGetLaunchReviewFlowInfo'))
        calls, callbacks, _, _ = self.score.score(self.logs)
        self.assertEqual(dict(callbacks['in-app review']), {'onGetLaunchReviewFlowInfo': {'h.review'}})
        self.assertNotIn('in-app update', calls)

    def test_binds_that_never_connect(self):
        self.app('i.age', line(90, 'AgeSignalsService', 'Initiate binding to the service.'))
        self.app('j.update', line(91, 'AppUpdateService', 'requestUpdateInfo(j.update)'),
                 line(91, 'AppUpdateService', 'Initiate binding to the service.'),
                 line(91, 'AppUpdateService', 'linkToDeath'))
        _, _, _, unconnected = self.score.score(self.logs)
        self.assertEqual(unconnected, {'AgeSignalsService': {'i.age'}})

    def test_list_limits_the_apps(self):
        self.app('f.one', line(60, 'ReviewService', 'requestInAppReview (f.one)'))
        self.app('g.two', line(70, 'ReviewService', 'requestInAppReview (g.two)'))
        calls, _, _, _ = self.score.score(self.logs, only={'g.two'})
        self.assertEqual(calls['in-app review'], {'g.two'})

    def stderr(self, package, *lines):
        (self.logs / f'hk-{package}.stderr').write_text('\n'.join(lines) + '\n')

    def test_binder_trace_answers(self):
        # Engage logs no callback; its answer is a call back on an interface of its own package.
        self.stderr('k.engage',
                    '[WL-PLAY-TRACE] out com.google.android.engage.protocol.IAppEngageService code=3 oneway x1',
                    '[WL-PLAY-TRACE] in com.google.android.engage.protocol.IAppEngageServiceAvailableCallback '
                    'code=1598968902  x1',
                    '[WL-PLAY-TRACE] in com.google.android.engage.protocol.IAppEngageServiceAvailableCallback code=1  x1')
        # A two-way call answers in its reply (exception code 0) or fails with a code; an empty reply means the
        # store's side is one-way, and only a call back answers it. Play services' interfaces are not the store's.
        self.stderr('l.billing',
                    '[WL-PLAY-TRACE] out com.android.vending.billing.IInAppBillingService code=1 0 x1',
                    '[WL-PLAY-TRACE] out com.android.vending.billing.IInAppBillingService code=11 -1 x2',
                    '[WL-PLAY-TRACE] out com.android.vending.licensing.ILicensingService code=3 empty x1',
                    '[WL-PLAY-TRACE] out com.google.android.gms.common.internal.IGmsServiceBroker code=46 0 x1')
        # Only the one-way call that got a call back of its own package counts.
        self.stderr('m.prewarm',
                    '[WL-PLAY-TRACE] out com.google.android.play.core.prewarm.protocol.IPrewarmService code=1 oneway x1',
                    '[WL-PLAY-TRACE] in com.google.android.engage.protocol.IAppEngageServiceAvailableCallback code=1  x1')
        calls, replied, failed, oneway, called_back = self.score.traces(self.logs)
        engage = 'com.google.android.engage.protocol.IAppEngageService'
        billing = 'com.android.vending.billing.IInAppBillingService'
        licensing = 'com.android.vending.licensing.ILicensingService'
        prewarm = 'com.google.android.play.core.prewarm.protocol.IPrewarmService'
        self.assertEqual(set(calls), {engage, billing, licensing, prewarm})
        self.assertEqual(called_back[engage], {'k.engage'})
        self.assertEqual(replied[billing], {'l.billing'})
        self.assertEqual({c: a for c, a in failed[billing].items()}, {'-1': {'l.billing'}})
        self.assertEqual(oneway[licensing], {'l.billing'})
        self.assertEqual(dict(failed[licensing]), {'empty': {'l.billing'}})
        self.assertEqual(called_back[licensing], set())
        self.assertEqual(oneway[prewarm], {'m.prewarm'})
        self.assertEqual(called_back[prewarm], set())
        calls, _, _, _, _ = self.score.traces(self.logs, only={'k.engage'})
        self.assertEqual(set(calls), {engage})

    def test_one_way_codes_apart(self):
        # Licensing's checkLicense (code 1) is called back; PairIP's report (code 3) expects no answer. An app that
        # sent both cannot say which one its call back answered.
        licensing = 'com.android.vending.licensing.ILicensingService'
        out = f'[WL-PLAY-TRACE] out {licensing}'
        back = '[WL-PLAY-TRACE] in com.android.vending.licensing.ILicenseResultListener code=1  x1'
        self.stderr('n.lvl', f'{out} code=1 oneway x1', back)
        self.stderr('o.pairip', f'{out} code=3 empty x1')
        self.stderr('p.pairip', f'{out} code=3 empty x2')
        self.stderr('q.both', f'{out} code=3 empty x1', f'{out} code=1 oneway x1', back)
        # A reply is not a one-way call; Play services' interfaces are not the store's.
        self.stderr('r.billing', '[WL-PLAY-TRACE] out com.android.vending.billing.IInAppBillingService code=1 0 x1',
                    '[WL-PLAY-TRACE] out com.google.android.gms.common.internal.IGmsServiceBroker code=46 oneway x1')
        codes = self.score.oneway_codes(self.logs)
        self.assertEqual(set(codes), {licensing})
        self.assertEqual(dict(codes[licensing]), {'n.lvl': {'1'}, 'o.pairip': {'3'}, 'p.pairip': {'3'},
                                                  'q.both': {'1', '3'}})
        _, _, _, _, called_back = self.score.traces(self.logs)
        self.assertEqual(self.score.code_lines(codes[licensing], called_back[licensing]), [
            '    code 3: 3 apps; of the 2 that sent no other one-way code, 0 called back',
            '    code 1: 2 apps; of the 1 that sent no other one-way code, 1 called back'])
        # One code: the interface's own line says it all.
        self.assertEqual(self.score.code_lines({'n.lvl': {'1'}}, {'n.lvl'}), [])
        self.assertEqual(self.score.oneway_codes(self.logs, only={'o.pairip'})[licensing], {'o.pairip': {'3'}})


if __name__ == '__main__':
    unittest.main()
