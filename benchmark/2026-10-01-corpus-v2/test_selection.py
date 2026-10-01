import copy
import csv
import io
import json
from pathlib import Path
import re
import tempfile
import unittest

import collect
import report

HERE = Path(__file__).resolve().parent


def validate(result):
    rows = result['rows']
    packages = [row['package'] for row in rows]
    hashes = [row['sha256'] for row in rows]
    if len(rows)!=100 or len(set(packages))!=100 or len(set(hashes))!=100:
        raise ValueError('duplicate or wrong population')
    if set(packages) & set(result['existing']['packages']):
        raise ValueError('existing package selected')
    for row in rows:
        if not re.fullmatch('[a-f0-9]{64}',row['sha256']) or row['bytes']<=0:
            raise ValueError('invalid APK identity')
        if row['nativecode'] and 'arm64-v8a' not in row['nativecode']:
            raise ValueError('non-arm64 native artifact')
        if row['group']=='priority' and row['nativecode']:
            raise ValueError('priority native artifact')
        prior=row['prediction']
        if prior['first_wall']!='unknown' or prior['checkpoint']!='unknown' or prior['apk_scanned']:
            raise ValueError('metadata overclaims APK scan')
        if prior['source_language']!='unknown' or prior['androidx_view_classes']!='unknown':
            raise ValueError('metadata overclaims class evidence')


class IdentityTests(unittest.TestCase):
    def test_pinned_index_and_exact_rows(self):
        evidence=report.load_evidence()
        result=report.build(evidence)
        validate(result)
        self.assertEqual(evidence['index']['sha256'],collect.INDEX_SHA)
        self.assertEqual(evidence['entry']['index_reference']['sha256'],collect.INDEX_SHA)
        self.assertEqual(evidence['entry']['index_reference']['size'],61862942)
        self.assertEqual(result['existing']['key_count'],66)
        self.assertEqual({entry['key'] for entry in result['existing']['resolved_null_packages']},{'x','noice'})
        identities={entry['package']:entry for entry in evidence['selected']}
        for row in result['rows']:
            version=identities[row['package']]['version']
            self.assertEqual(row['sha256'],version['file']['sha256'])
            self.assertEqual(row['version_name'],version['manifest']['versionName'])
            self.assertEqual(row['version_code'],version['manifest']['versionCode'])
            self.assertEqual(row['apk_url'],'https://f-droid.org/repo'+version['file']['name'])
            self.assertTrue(row['signer_sha256'])


class RejectionTests(unittest.TestCase):
    def test_mismatched_index_refused_before_use(self):
        with tempfile.TemporaryDirectory(prefix='corpus-v2-reject-') as directory:
            path=Path(directory)/'index.json'
            path.write_text('{"packages":{}}')
            with self.assertRaisesRegex(ValueError,'index SHA mismatch'):
                collect.collect(path,Path(directory)/'missing-entry.jar',Path(directory)/'missing-apps.json')

    def test_abi_channel_and_signer_selection(self):
        artifact=copy.deepcopy(report.load_evidence()['selected'][0]['version'])
        signer=artifact['manifest']['signer']['sha256'][0]
        bad_abi=copy.deepcopy(artifact)
        bad_abi['manifest']['nativecode']=['armeabi-v7a']
        bad_abi['manifest']['versionCode']+=100
        prerelease=copy.deepcopy(artifact)
        prerelease['releaseChannels']=['Beta']
        prerelease['manifest']['versionCode']+=200
        wrong_signer=copy.deepcopy(artifact)
        wrong_signer['manifest']['signer']['sha256']=['0'*64]
        wrong_signer['manifest']['versionCode']+=300
        text_beta=copy.deepcopy(artifact)
        text_beta['manifest']['versionName']='1.0.0-beta06'
        text_beta['manifest']['versionCode']+=400
        package=dict(metadata=dict(preferredSigner=signer),versions=dict(good=artifact,bad_abi=bad_abi,beta=prerelease,wrong=wrong_signer,text_beta=text_beta))
        self.assertEqual(collect.select_version(package),artifact)
        package['versions'].pop('good')
        with self.assertRaisesRegex(ValueError,'no stable'):
            collect.select_version(package)

    def test_duplicate_existing_and_false_scan_rejected(self):
        original=report.build(report.load_evidence())
        duplicate=copy.deepcopy(original)
        duplicate['rows'][1]['package']=duplicate['rows'][0]['package']
        with self.assertRaisesRegex(ValueError,'duplicate'):
            validate(duplicate)
        existing=copy.deepcopy(original)
        existing['rows'][0]['package']=existing['existing']['packages'][0]
        with self.assertRaisesRegex(ValueError,'existing package'):
            validate(existing)
        false_scan=copy.deepcopy(original)
        false_scan['rows'][0]['prediction']['first_wall']='none'
        with self.assertRaisesRegex(ValueError,'overclaims'):
            validate(false_scan)


class PredictionTests(unittest.TestCase):
    def test_coverage_and_prior_limits(self):
        evidence=report.load_evidence()
        result=report.build(evidence)
        self.assertEqual(result['groups'],{'priority':80,'compose':10,'webview':6,'gl':4})
        self.assertEqual(result['prediction_counts'],{'own-ui':80,'unknown':20})
        self.assertEqual(result['apk_scan_count'],0)
        for entry in evidence['selected']:
            if entry['group']=='priority':
                self.assertFalse(entry['version']['manifest'].get('nativecode'))
            else:
                self.assertRegex(entry['coverage_cue']['token'].lower(),collect.GROUP_PATTERNS[entry['group']])
        self.assertFalse(result['freeze_authorized'])
        self.assertFalse(result['apps_json_changed'])


class ReplayTests(unittest.TestCase):
    def test_all_artifacts_and_seed_membership(self):
        evidence=report.load_evidence()
        result=report.build(evidence)
        seeds=json.loads((HERE/'seeds.json').read_text())
        self.assertEqual({package for packages in seeds.values() for package in packages},{row['package'] for row in result['rows']})
        self.assertEqual(json.loads((HERE/'results.json').read_text()),result)
        self.assertEqual((HERE/'CANDIDATES.csv').read_text(),report.csv_text(result))
        self.assertEqual((HERE/'README.md').read_text(),report.markdown(result))
        rows=list(csv.DictReader(io.StringIO(report.csv_text(result))))
        self.assertEqual(len(rows),100)
        self.assertEqual(sum(row['group']=='priority' for row in rows),80)


if __name__=='__main__':
    unittest.main()
