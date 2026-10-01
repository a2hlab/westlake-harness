import csv
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('icon_format_scanner',Path(__file__).parent/'scan.py')
scan=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scan)


def table(paths, flags=0):
    strings=bytearray();offsets=[]
    for value in paths:
        encoded=value.encode();offsets.append(len(strings));strings.extend(bytes([len(value),len(encoded)])+encoded+b'\0')
    while len(strings)%4:
        strings.append(0)
    pool=struct.pack('<HHIIIIII',1,28,28+4*len(paths)+len(strings),len(paths),0,256,28+4*len(paths),0)+struct.pack('<'+'I'*len(paths),*offsets)+strings
    chunks=[]
    for index in range(len(paths)):
        array=struct.pack('<HH',0,0) if flags==1 else struct.pack('<H',0) if flags==2 else struct.pack('<I',0)
        entry=struct.pack('<HHIHBBI',8,0,0,8,0,3,index)
        chunks.append(struct.pack('<HHIBBHIII',0x201,24,24+len(array)+len(entry),9,flags,0,1,24+len(array),4)+array+entry)
    package=bytearray(288);struct.pack_into('<HHII',package,0,0x200,288,288+sum(map(len,chunks)),127)
    body=pool+package+b''.join(chunks)
    return struct.pack('<HHII',2,12,12+len(body),1)+body


class MappingTests(unittest.TestCase):
    def test_only_application_android_icon_reference(self):
        text='E: manifest\n  A: package="org.example"\n  E: application\n    A: android:icon(0x01010002)=@0x7f090000\n    A: android:roundIcon(0x0101052c)=@0x7f090001\n    E: activity\n      A: android:icon(0x01010002)=@0x7f090002\n'
        self.assertEqual(scan.manifest_icon(text)['icon_id'],'0x7f090000')

    def test_formats_use_magic_not_extension(self):
        self.assertEqual(scan.file_format(b'RIFF1234WEBPpayload'),'WebP')
        self.assertEqual(scan.file_format(b'\x89PNG\r\n\x1a\n'),'PNG')
        self.assertEqual(scan.file_format(b'\xff\xd8\xff'),'JPEG')
        self.assertEqual(scan.file_format(b'\x03\x00\x08\x00'),'XML')
        self.assertEqual(scan.file_format(b''),'missing')
        self.assertEqual(scan.file_format(b'not an image'),'other-unknown')

    def test_identity_drift_refused(self):
        with self.assertRaisesRegex(ValueError,'identity drift'):
            scan.verify(b'changed',scan.RESOLVER_SHA)

    def test_expanded_WebP_is_family_not_valid_container(self):
        valid=b'RIFF'+struct.pack('<I',8)+b'WEBP'+b'\xff\xaa\x80\x90'
        expanded=valid.decode('latin1').encode('utf8')
        details=scan.format_details(expanded)
        self.assertEqual(details['family'],'WebP')
        self.assertEqual(details['validity'],'malformed-UTF8-expanded-WebP')
        self.assertEqual(details['diagnostic_reversed_bytes'],len(valid))
        self.assertEqual(scan.format_details(valid)['validity'],'WebP-header-and-RIFF-size-valid')

    def test_resource_block_excludes_other_ids(self):
        text='    resource 0x7f090000 mipmap/icon\n      (mdpi) (file) res/d2.webp\n    resource 0x7f090001 mipmap/round\n      (xxxhdpi) (file) res/other.png\n'
        result=scan.resource_block(text,'0x7f090000')
        self.assertEqual(len(result),2)
        self.assertNotIn('other.png',str(result))

    def test_record_sha_package_drift_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'record.json').write_text(json.dumps(dict(key='test',package='other',apk_sha256='0'*64)))
            with self.assertRaisesRegex(ValueError,'record APK/package/key drift'):
                scan.observe(root,dict(key='test',package='right',apk_sha256='0'*64),root)


class SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.root=Path(cls.temporary.name);cls.probe=cls.root/'probe';scan.build_probe(cls.probe)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def resolve(self, paths, flags=0):
        source=self.root/'resources.arsc';source.write_bytes(table(paths,flags))
        return subprocess.check_output([str(self.probe),str(source),'0x7f090000'],text=True).strip()

    def test_obfuscated_first_raster_wins_tie_not_actual_density(self):
        self.assertEqual(self.resolve(['res/d2.webp','res/sK.webp','res/BW.xml']),'SELECTED\tres/d2.webp')

    def test_dense_sparse_offset16_parity(self):
        for flags in [0,1,2]:
            with self.subTest(flags=flags):
                self.assertEqual(self.resolve(['res/mipmap-hdpi/icon.png','res/mipmap-xxxhdpi/icon.webp'],flags),'SELECTED\tres/mipmap-xxxhdpi/icon.webp')

    def test_only_xml_selected_not_reclassified_fallback_png(self):
        self.assertEqual(self.resolve(['res/BW.xml']),'SELECTED\tres/BW.xml')

    def test_unresolved_entry_does_not_select_random_member(self):
        source=self.root/'resources.arsc';source.write_bytes(table(['res/unrelated.png']))
        self.assertEqual(subprocess.check_output([str(self.probe),str(source),'0x7f090001'],text=True).strip(),'MISSING')


class TileTests(unittest.TestCase):
    def tree(self, identifier, visible='true', owner='com.ohos.sceneboard'):
        return dict(attributes=dict(bundleName=owner),children=[dict(attributes=dict(id=identifier,visible=visible,enabled='true',clickable='true'),children=[])])

    def test_exact_package_and_activity(self):
        self.assertEqual(len(scan.tiles(self.tree('AppIconCommonView_org.example.Main'),'org.example','Main')['matches']),1)
        self.assertEqual(scan.tiles(self.tree('AppIconCommonView_org.example.other.Main'),'org.example','Main')['matches'],[])
        self.assertEqual(scan.tiles(self.tree('AppIconCommonView_org.example.Alias'),'org.example','Main')['matches'],[])

    def test_wrong_window_not_desktop_tile(self):
        self.assertEqual(scan.tiles(self.tree('AppIconCommonView_org.example.Main',owner='org.example'),'org.example','Main')['matches'],[])

    def test_hidden_tile_exists_but_visibility_not_actionability(self):
        row=scan.tiles(self.tree('AppIconCommonView_org.example.Main',visible='false'),'org.example','Main')
        self.assertEqual(scan.tile_status([row],'Main'),'found')
        self.assertFalse(row['matches'][0]['visible'])

    def test_absent_cold_and_missing_evidence_distinct(self):
        self.assertEqual(scan.tile_status([],'Main'),'unknown-no-snapshots')
        self.assertEqual(scan.tile_status([dict(matches=[],all_tile_ids=[])],'Main'),'unknown-cold-desktop')
        self.assertEqual(scan.tile_status([dict(matches=[],all_tile_ids=['other'])],'Main'),'not-found-in-captured-pages')
        self.assertEqual(scan.tile_status([dict(matches=[],all_tile_ids=['other'])],None),'unknown-desktop-activity')


class OutputTests(unittest.TestCase):
    def test_published_166_rows_and_csv_match_evidence_counts(self):
        directory=Path(__file__).parent
        result=json.loads((directory/'results.json').read_text())
        summary=scan.summarize(result['rows'])
        self.assertEqual(summary['formats'],{'PNG':130,'WebP':25,'XML':11})
        self.assertEqual(summary['WebP_validity'],{'WebP-header-and-RIFF-size-valid':24,'malformed-UTF8-expanded-WebP':1})
        self.assertEqual(summary['WebP_latest_not_found_keys'],['cv2-com-frequent-habits'])
        self.assertEqual(summary['latest_tile_status'],{'found':165,'not-found-in-captured-pages':1})
        with (directory/'ICONS.csv').open(newline='') as file:
            rows=list(csv.DictReader(file))
        self.assertEqual(len(rows),166)
        self.assertEqual({row['key']:row['selected_file'] for row in rows},{row['key']:row['selected_file'] for row in result['rows']})
        self.assertEqual(result['dependencies']['benchmark/2026-10-01-icon-format-scan/scan.py'],scan.sha((directory/'scan.py').read_bytes()))

    def test_complete_cohort_json_csv_and_separate_rerun(self):
        rows=[dict(key='test-'+str(index),package='org.example',apk_sha256='0'*64,icon_id='0x7f090000',selected_file='res/d2.webp',selected_format='WebP',selection_status='resolved-file',
            U8_full_signed=dict(verdict='app_failed'),U8_full_tile=dict(tile_status='unknown-cold-desktop'),U8_rerun_signed=None,U8_rerun_tile=None) for index in range(166)]
        rows[0].update(U8_rerun_signed=dict(rerun='lit'),U8_rerun_tile=dict(tile_status='found'))
        summary=scan.summarize(rows)
        self.assertEqual(summary['WebP_count'],166)
        self.assertEqual(summary['WebP_latest_tile_status']['found'],1)
        self.assertEqual(summary['full_signed']['app_failed'],166)
        self.assertEqual(summary['latest_signed']['lit'],1)
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary);scan.emit(output,dict(rows=rows,summary=summary))
            self.assertEqual(len(json.loads((output/'results.json').read_text())['rows']),166)
            with (output/'ICONS.csv').open() as file:
                flat=list(csv.DictReader(file))
            self.assertEqual(len(flat),166)
            self.assertEqual(flat[0]['U8_full_t20'],'app_failed')
            self.assertEqual(flat[0]['U8_rerun_t20'],'lit')

    def test_incomplete_or_duplicate_keys_refused(self):
        with self.assertRaisesRegex(ValueError,'Incomplete/duplicate'):
            scan.summarize([])


if __name__=='__main__':
    unittest.main()
