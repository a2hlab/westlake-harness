import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from apply_speed_aot import inside, validate
from verify_acceptance import verify

class SpeedTests(unittest.TestCase):
    def test_changed_input_or_report_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve(); stage = root/'stage'; stage.mkdir(); bundle = root/'bundle'; bundle.mkdir()
            def put(folder, name, data):
                p = folder/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
                return hashlib.sha256(data).hexdigest()
            jar = put(stage, 'fw/example.jar', b'jar')
            art = put(stage, 'libart.so', b'current-art'); apk = put(stage, 'toutiao.apk', b'apk')
            odex = put(bundle, 'toutiao.odex', b'odex')
            (stage/'run.sh').write_text('export ASX_APK_PATH=/data/local/tmp/asx/toutiao.apk\n')
            lock = dict(inputs={'fw/example.jar':dict(sha256=jar)}, libart_sha256=art, apk_sha256=apk,
                        artifacts={'toutiao.odex':dict(sha256=odex)},dex_location='/data/local/tmp/asx/toutiao.apk')
            report = dict(files=copy.deepcopy(lock['inputs']))
            validate(stage,bundle,report,lock)
            report['files']['fw/example.jar']['sha256'] = 'bad'
            with self.assertRaises(ValueError): validate(stage,bundle,report,lock)
            report['files']['fw/example.jar']['sha256'] = jar
            (stage/'libart.so').write_bytes(b'other-art')
            with self.assertRaises(ValueError): validate(stage,bundle,report,lock)
            self.assertFalse((stage/'oat').exists())

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'oat').symlink_to('/tmp',target_is_directory=True)
            with self.assertRaises(ValueError): inside(root,'oat/arm64/toutiao.odex')

    def test_acceptance_requires_both_independent_witnesses(self):
        log='[IMG] Loaded /data/local/tmp/asx/oat/arm64/toutiao.art at 0x100000\n'
        maps='100000-200000 r-xp 00000000 00:00 1 /data/local/tmp/asx/oat/arm64/toutiao.odex\n'
        self.assertTrue(verify(log,maps,1000)['passed'])
        self.assertFalse(verify('',maps,1000)['passed'])
        self.assertFalse(verify(log,maps.replace('r-xp','r--p'),1000)['passed'])
        self.assertFalse(verify(log+'oat_file_assistant.cc:1] toutiao checksum mismatch\n',maps,1000)['passed'])
        self.assertTrue(verify(log+'settings toutiao enable_reject=true\n',maps,1000)['passed'])
        self.assertFalse(verify(log,maps,2000000)['passed'])

if __name__ == '__main__': unittest.main()
