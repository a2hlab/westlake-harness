import importlib.util
import json
from pathlib import Path
import unittest

D = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('wmc_plan', D / 'plan.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class PlanTests(unittest.TestCase):
    def test_original_link_order_retained(self):
        old = json.loads((D / 'recorded-commands.json').read_text())['link']
        new = m.plan()['steps'][0]['argv']
        old = [x.replace('$ORB_WS', '$STAGED_INPUTS') for x in old]
        old[old.index('-o') + 1] = '$OUT/bridge-original-object.so'
        self.assertEqual(old, new)

    def test_only_wmc_and_output_change_between_links(self):
        p = m.plan()
        a, b = p['steps'][0]['argv'], p['steps'][2]['argv']
        delta = [(x,y) for x,y in zip(a,b) if x != y]
        self.assertEqual(len(delta), 2)
        self.assertEqual(sum(x.endswith(m.OBJECT_SUFFIX) for x,y in delta), 1)
        self.assertFalse(p['executes_commands'])

    def test_compile_flags_not_reconstructed(self):
        old = json.loads((D / 'recorded-commands.json').read_text())['compile']
        old = [x.replace('$HISTORICAL_ROOT_0', '$STAGED_INPUTS').replace('$HISTORICAL_ROOT_1', '$STAGED_INPUTS') for x in old]
        old[old.index('-o') + 1] = '$OUT/oh_window_manager_client.o'
        old[old.index('-MF') + 1] = '$OUT/oh_window_manager_client.o.d'
        self.assertEqual(old, m.plan()['steps'][1]['argv'])

if __name__ == '__main__':
    unittest.main()
