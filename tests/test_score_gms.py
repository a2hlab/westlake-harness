"""device/play/score_gms.py: what apps got from the shared Play services process, from their binder traces."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / 'device' / 'play' / 'score_gms.py'
BROKER = '[WL-PLAY-TRACE] out com.google.android.gms.common.internal.IGmsServiceBroker code=46'
CALLBACK = '[WL-PLAY-TRACE] in com.google.android.gms.common.internal.IGmsCallbacks code=3'


def load():
    spec = importlib.util.spec_from_file_location('score_gms', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScoreGmsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.logs = Path(self.tmp.name)
        self.score = load()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def stderr(self, package, *lines):
        (self.logs / f'hk-{package}.stderr').write_text('\n'.join(lines) + '\n')

    def test_service_names_come_from_the_table(self):
        names = self.score.service_names()
        self.assertEqual(names[93], 'MEASUREMENT')
        self.assertEqual(names[51], 'PHENOTYPE')

    def test_broker_requests_and_connections(self):
        # Taken and connected; taken and refused with a ConnectionResult; refused with an exception.
        self.stderr('a.ok', f'{BROKER} service=51 0 x1', f'{CALLBACK} status=0 afterService=51 x1')
        self.stderr('b.invalid', f'{BROKER} service=93 0 x1', f'{CALLBACK} status=9 afterService=93 x2')
        self.stderr('c.denied', f'{BROKER} service=326 -1 x1',
                    # Another broker's interfaces and the Play Store's are not counted here.
                    '[WL-PLAY-TRACE] out com.android.vending.billing.IInAppBillingService code=1 0 x1')
        asked, answered, refused = self.score.broker(self.logs)
        self.assertEqual({s: a for s, a in asked.items()}, {51: {'a.ok'}, 93: {'b.invalid'}, 326: {'c.denied'}})
        self.assertEqual(answered[93], {'b.invalid'})
        self.assertEqual(dict(refused[326]), {'-1': {'c.denied'}})
        results = self.score.connections(self.logs)
        self.assertEqual(dict(results[51]), {0: {'a.ok'}})
        self.assertEqual(dict(results[93]), {9: {'b.invalid'}})
        self.assertNotIn(326, results)
        asked, _, _ = self.score.broker(self.logs, only={'a.ok'})
        self.assertEqual(set(asked), {51})

    def test_interfaces_other_than_the_broker(self):
        self.stderr('d.ads',
                    '[WL-PLAY-TRACE] out com.google.android.gms.ads.identifier.internal.IAdvertisingIdService code=1 0 x1',
                    f'{BROKER} service=93 0 x1')
        self.stderr('e.clearcut',
                    '[WL-PLAY-TRACE] out com.google.android.gms.clearcut.internal.IClearcutLoggerService code=1 oneway x1',
                    '[WL-PLAY-TRACE] in com.google.android.gms.clearcut.internal.IClearcutLoggerCallbacks code=1  x1')
        calls, replied, failed, oneway, called_back = self.score.interfaces(self.logs)
        ads = 'com.google.android.gms.ads.identifier.internal.IAdvertisingIdService'
        clearcut = 'com.google.android.gms.clearcut.internal.IClearcutLoggerService'
        self.assertEqual(set(calls), {ads, clearcut})
        self.assertEqual(replied[ads], {'d.ads'})
        self.assertEqual(oneway[clearcut], {'e.clearcut'})
        self.assertEqual(called_back[clearcut], {'e.clearcut'})

    def test_push_registrations_by_last_count(self):
        play = self.logs / 'play'
        play.mkdir()
        (play / 'play-tokens.log').write_text('T f.app 0 1\nT f.app 1 1\nT g.app 0 0\nnot a count\n')
        files, registered = self.score.push(play)
        self.assertEqual(files, {'f.app', 'g.app'})
        self.assertEqual(registered, {'f.app'})
        self.assertIsNone(self.score.push(self.logs / 'missing'))


if __name__ == '__main__':
    unittest.main()
