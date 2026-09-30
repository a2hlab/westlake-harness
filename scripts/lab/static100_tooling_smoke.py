from westlake_gap.ohresolve import resolve
from westlake_gap.contracts import _attr, manifest_facts
from pathlib import Path
from xml.etree.ElementTree import Element
import json
s={'inventory':{'native_resolution':{'target_abi':'arm64-v8a'},'elfs':[{'abi':'arm64-v8a','name':'a','undefined_symbols':['required64'],'exported_symbols':[]},{'abi':'armeabi-v7a','name':'b','undefined_symbols':['arm32_only'],'exported_symbols':['required64']}]}}
r=resolve(s,set(),{});assert [m['symbol'] for m in r['missing']]==['required64']
assert _attr(Element('provider',{'name':'bare'}),'name')=='bare'
assert _attr(Element('provider',{'name':'bare','{http://schemas.android.com/apk/res/android}name':'namespaced'}),'name')=='namespaced'
import lab_paths
c=json.load(open(lab_paths.inputs()/'corpus100.json'))
f=manifest_facts(Path(c['apps']['co-p2pmobile']['input']));providers=[p for p in f['components'] if p['kind']=='provider']
assert len(providers)==22 and all(p['name'] for p in providers)
print('PASS: selected ABI import/export isolation; namespace precedence; PayPal 22/22 provider identities recovered')
