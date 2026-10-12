import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
import uuid

import adapter
import collect

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
T5 = REPO / 'benchmark/2026-10-09-demo-baseline/t5'
sys.path.insert(0, str(T5))
import build_seal
spec = importlib.util.spec_from_file_location('original_fixture', T5/'test_seal.py')
fixture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)


class Identity(unittest.TestCase):
    def test_real_bundle_top_level(self):
        for file, name, code, suffix in [('anki', 'com.ichi2.anki', 22401300, '.apk'),
                                        ('imehost', 'org.westlake.imehost', 2, '.hap')]:
            text = (HERE/'fixtures'/(file+'.stdout.txt')).read_text()
            row = adapter.bundle_identity(text, name)
            self.assertEqual(row['version_code'], code)
            self.assertTrue(row['apk_path'].endswith(suffix))
            with self.assertRaises(ValueError): adapter.bundle_identity(text, 'wrong.name')
            data = json.JSONDecoder().raw_decode(text[text.index('{'):])[0]
            data.pop('versionCode')
            with self.assertRaises(ValueError): adapter.bundle_identity(json.dumps(data), name)

    def test_actual_selfcheck_read_live_with_bms_nested_zero(self):
        script = (REPO/'scripts/lab/demo_selfcheck.sh').read_text().split("<<'PY'\n",1)[1].rsplit('\nPY',1)[0]
        tree = ast.parse(script)
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'read_live')
        source = (HERE/'fixtures/anki.stdout.txt').read_text().split('\nREMOTE_RC=',1)[0]
        def run(argv, **kwargs):
            command = argv[-1]
            marker = re.search(r'__DEMO_READ_RC_[0-9a-f]+__', command).group()
            value = source if command.startswith('bm dump') else 'same-boot'
            return SimpleNamespace(returncode=0, stdout=value+'\n'+marker+'0\n', stderr='')
        scope = dict(Path=Path, os=os, re=re, shlex=shlex, sys=sys, json=json, uuid=uuid,
                     shutil=SimpleNamespace(which=lambda _: 'mac'),
                     subprocess=SimpleNamespace(run=run, TimeoutExpired=TimeoutError),
                     lab_paths=SimpleNamespace(tools=lambda: Path('/fixture')))
        exec(compile(ast.Module(body=[function],type_ignores=[]),'actual-selfcheck-read-live','exec'),scope)
        observed = scope['read_live']({'packages':[{'package':'com.ichi2.anki','apk_path':'/fixture.apk'}],
                                      'system_params':{}}, 'fixture-serial', {})
        self.assertEqual(observed['errors'], [])
        self.assertEqual(observed['packages']['com.ichi2.anki']['version_code'], '22401300')


class Completeness(unittest.TestCase):
    def prepare(self, folder):
        snapshot, overlays, manifest = fixture_module.fixture()
        capture = dict(serial=snapshot['serial'], captured_at=snapshot['captured_at'], synthetic=True,
                       groups={g:list(v) for g,v in snapshot['files'].items()}, receipts={},
                       hash_receipts=['hashes'], package_names=[p['package'] for p in snapshot['packages']],
                       param_names=list(snapshot['system_params']))
        def add(key, command, text):
            file=str(len(capture['receipts']))+'.stdout.txt'; data=(text+'\nSEAL_READ_RC=0\n').encode()
            (folder/file).write_bytes(data)
            capture['receipts'][key]=dict(stdout=file,sha256=hashlib.sha256(data).hexdigest(),host_rc=0,command=command)
        for edge in ('before','after'): add('boot-'+edge,'cat /proc/sys/kernel/random/boot_id','01234567-1111-2222-3333-444444444444')
        hashes={p:h for v in snapshot['files'].values() for p,h in v.items()}
        hashes.update(snapshot['apk_hashes'])
        add('hashes','sha256sum '+' '.join(hashes),'\n'.join(h+'  '+p for p,h in hashes.items()))
        for p in snapshot['packages']:
            body=dict(name=p['package'],versionCode=int(p['version_code']),versionName=p['version_name'])
            if p['apk_path'].endswith('.apk'): body['applicationInfo']={'codePath':p['apk_path'],'versionCode':0}
            else: body['hapModuleInfos']=[dict(moduleName='entry',hapPath=p['apk_path'])]
            add('bundle:'+p['package'],'bm dump -n '+p['package'],json.dumps(body))
        for k,v in snapshot['system_params'].items(): add('param:'+k,'param get '+k,v)
        (folder/'capture.json').write_text(json.dumps(capture))
        return capture, overlays, manifest

    def test_compiler_and_three_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp); capture, overlays, manifest=self.prepare(folder)
            result=adapter.convert(folder)
            self.assertTrue(result['synthetic'])
            self.assertEqual(build_seal.build(result,overlays,manifest)['schema'],'demo-seal/v1')
            for fault in ('missing-hash','remote-failure','cross-boot'):
                capture, _, _=self.prepare(folder)
                key='hashes' if fault=='missing-hash' else 'boot-after'
                receipt=capture['receipts'][key];file=folder/receipt['stdout'];text=file.read_text()
                if fault=='missing-hash':text='\n'.join(text.splitlines()[1:])+'\n'
                elif fault=='remote-failure':text=text.replace('SEAL_READ_RC=0','SEAL_READ_RC=1')
                else:text=text.replace('01234567','11234567')
                file.write_text(text);receipt['sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
                (folder/'capture.json').write_text(json.dumps(capture))
                with self.subTest(fault=fault), self.assertRaises(ValueError):adapter.convert(folder)

    def test_readonly_collector_uses_real_receipt_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp); recorded=folder/'recorded'; recorded.mkdir()
            capture, _, _=self.prepare(recorded)
            commands={r['command']:(recorded/r['stdout']).read_bytes() for r in capture['receipts'].values()}
            all_hashes={}
            for r in capture['receipts'].values():
                if r['command'].startswith('sha256sum '):
                    for line in (recorded/r['stdout']).read_text().splitlines():
                        if re.fullmatch(r'[0-9a-f]{64}\s+/\S+',line):
                            sha,path=line.split(); all_hashes[path]=sha
            calls=[]
            def run(argv, **kwargs):
                self.assertEqual(argv[1:4],['-t',capture['serial'],'shell'])
                command=argv[-1].split('; seal_read_rc=',1)[0]; calls.append(command)
                if command.startswith('sha256sum '):
                    data=('\n'.join(all_hashes[p]+'  '+p for p in command.split()[1:])+'\nSEAL_READ_RC=0\n').encode()
                else:data=commands[command]
                return SimpleNamespace(returncode=0,stdout=data,stderr=b'')
            out=folder/'observed'
            result=collect.collect(capture['serial'],capture['groups'],capture['package_names'],out,runner=run)
            self.assertEqual(result['files'],adapter.convert(recorded)['files'])
            self.assertFalse(result['collection_provenance']['ui_accepted'])
            self.assertTrue(all(c.startswith(('cat ','sha256sum ','bm dump -n ','param get ')) for c in calls))
            with self.assertRaises(ValueError): collect.collect('wrong',capture['groups'],capture['package_names'],folder/'invalid',runner=run)


if __name__ == '__main__':
    unittest.main()
