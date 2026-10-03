import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from class_contracts import contract, parse_blocks
from collect import image_offsets, require_equal
from strict_findings import finding, issue_id

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


def validate_packet(packet):
    if packet['signer'] is not None or packet['signed_at'] is not None:
        raise ValueError('Unsigned review only')
    if any(packet[name] is not False for name in ['execution_enabled', 'rollout_ready', 'gate_registry_applied']):
        raise ValueError('No active approval or execution')
    rows = packet['decisions']
    if len(rows) != 26 or len({row['id'] for row in rows}) != 26:
        raise ValueError('Expected26 unique decisions')
    if any(row['decision'] != 'pending' or row.get('approved_by') is not None for row in rows):
        raise ValueError('Every decision must stay pending')
    gates = packet['outer_image_gates']['faces']
    if {(row['platform'], row['variant']) for row in gates} != {
        ('darwin', 'common'), ('darwin', '61b'), ('linux', 'common'), ('linux', '61b')
    } or len(gates) != 4:
        raise ValueError('Four actual faces required')
    if any(row['exit_code'] != 0 or row['G1'] is not True or row['G2'] is not True for row in gates):
        raise ValueError('All four G1/G2 records must pass')


class PacketTests(unittest.TestCase):
    def test_twenty_six_pending(self):
        validate_packet(load('outer-approval-packet.json'))

    def test_no_accidental_signing(self):
        packet = load('outer-approval-packet.json')
        packet['decisions'][0]['decision'] = 'approve'
        with self.assertRaises(ValueError):
            validate_packet(packet)

    def test_seventeen_scope_bijection_and_artifacts(self):
        packet = load('outer-approval-packet.json')
        original = load('inputs/native-original-request.json')
        signed = load('inputs/native-signed-approval.json')
        native = [row for row in packet['decisions'] if row['id'] in {item['id'] for item in original['decisions']}]
        scopes = {identifier: group['scope'] for group in signed['decisions'] for identifier in group['ids']}
        self.assertEqual(len(native), 17)
        self.assertEqual(set(scopes), {row['id'] for row in native})
        for row in native:
            self.assertEqual(row['previous_signed_scope'], scopes[row['id']])
            self.assertTrue(row['artifact_bytes_unchanged'])
            self.assertTrue(row['semantic_fields_equal'])
            self.assertEqual(row['new_binding']['native_manifest_sha256'], packet['native_manifest_sha256'])
            before = next(item for item in original['decisions'] if item['id'] == row['id'])
            self.assertEqual(before['scope'], row['scope'])
            if 'finding' in before:
                require_equal(finding(before['finding']), finding(row['finding']), 'Exact N1 semantic row')
                self.assertEqual(issue_id('N1', row['finding'], packet['native_manifest_sha256'], packet['native_inputs_sha256']), row['issue_id'])
                self.assertTrue(all(item['equal'] for item in row['field_proofs'].values()))
            for field in ['raw_call_set_diff', 'raw', 'operation', 'disassembly']:
                if field in before:
                    self.assertEqual(before[field], row[field])
        for member in packet['native_transfer']['selected_artifacts'].values():
            self.assertTrue(member['identical_bytes'])
            self.assertEqual(member['deployed_sha256'], member['old'])

    def test_source_line_drift_is_not_binding_only(self):
        original = load('inputs/native-original-request.json')['decisions'][0]['finding']
        changed = copy.deepcopy(original)
        changed['detail']['evidence']['line'] += 1
        with self.assertRaisesRegex(ValueError, 'evidence/line'):
            require_equal(finding(original), finding(changed), 'Not an identity rebind')

    def test_image_exact_pair_and_scope(self):
        image = load('image-review.json')
        self.assertEqual(len(image['input_jars']), 9)
        self.assertEqual(image['field_width_bytes'], 8)
        self.assertEqual(image['changed_byte_count'], 3)
        self.assertEqual(image['interval'], ['0x3e3b8', '0x3e3c0'])
        self.assertEqual(image['elements']['run1'][1], '0x2')
        self.assertEqual(image['elements']['run2'][1], '0x2')
        self.assertNotEqual(image['run1_boot_art_sha256'], image['run2_boot_art_sha256'])
        self.assertTrue(image['not_transferred'])
        self.assertEqual(len(image['dump_evidence']), 2)
        for record in image['dump_evidence']:
            self.assertEqual(record['status'], dict(oatdump_exit_code=0, tee_exit_code=0))
            self.assertFalse(record['full_log_locally_read'])

    def test_outside_image_word_rejected(self):
        before = bytearray(0x3e3d0)
        before[:8] = b'art\n108\x00'
        after = bytearray(before)
        after[0x3e3b9] = 1
        self.assertEqual(image_offsets(before, after), [0x3e3b9])
        after[0x3e3c0] = 1
        with self.assertRaises(ValueError):
            image_offsets(before, after)

    def test_original_native_evidence_sha_is_persisted(self):
        transfer = load('native-transfer.json')
        references = [transfer['original_request'], transfer['signed_approval']] + transfer['exact_disassembly']
        for record in references:
            self.assertEqual(hashlib.sha256((HERE / record['snapshot']).read_bytes()).hexdigest(), record['sha256'])
        self.assertEqual(transfer['original_request']['sha256'], 'da1f47285a639f4594b89464594f326f4a8e9c7c9e89319ff27390ba73fd9667')

    def test_returned_dump_and_paired_receipt_hashes(self):
        image = load('image-review.json')
        references = image['paired_receipts'] + [image['inventory']]
        for record in image['dump_evidence']:
            references.extend(record['pieces'])
        for record in references:
            self.assertEqual(hashlib.sha256((HERE / record['snapshot']).read_bytes()).hexdigest(), record['sha256'])
        self.assertEqual(len(image['outputs']), 27)
        self.assertEqual(sum(record['identical'] for record in image['outputs']), 26)

    def test_class_contracts_and_exact_blob_snapshots(self):
        classes = load('class-review.json')['classes']
        self.assertEqual(len(classes), 8)
        for row in classes:
            self.assertFalse(row['baseline_present'])
            self.assertTrue(row['candidate_present'])
            self.assertEqual(row['descriptor'], row['allow_add'])
            raw = HERE / row['raw']['snapshot']
            self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), row['raw']['sha256'])
            parsed = contract(row['descriptor'], raw.read_text())
            for field in ['superclass', 'interfaces', 'methods']:
                self.assertEqual(parsed[field], row[field])
            source = row['source']
            data = (HERE / source['snapshot']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), source['sha256'])
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            self.assertEqual(blob, source['git_blob'])
            self.assertTrue(all(method['signature'].startswith(row['descriptor'] + '->') for method in row['methods']))
        self.assertEqual(sum(len(row['methods']) for row in classes), 42)

    def test_duplicate_or_empty_dex_rejected(self):
        with self.assertRaises(ValueError):
            parse_blocks('')
        with self.assertRaises(ValueError):
            parse_blocks("Class descriptor : 'Lx;'\nClass descriptor : 'Lx;'\n")

    def test_persisted_four_face_raw_outputs(self):
        packet = load('outer-approval-packet.json')
        for face in packet['outer_image_gates']['faces']:
            contents = (HERE / face['evidence']['snapshot']).read_bytes()
            self.assertEqual(hashlib.sha256(contents).hexdigest(), face['evidence']['sha256'])
            parsed = json.loads(contents.decode().splitlines()[-1])
            self.assertIs(parsed['G1'], True)
            self.assertIs(parsed['G2'], True)
            self.assertIn('cand=36 insns, ref=36 insns -> identical', parsed['log'])
        packet['outer_image_gates']['faces'][0]['G2'] = False
        with self.assertRaises(ValueError):
            validate_packet(packet)

    def test_cold_packet_has_no_artifact_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / 'packet.json'
            copied.write_text((HERE / 'outer-approval-packet.json').read_text())
            validate_packet(json.loads(copied.read_text()))


if __name__ == '__main__':
    unittest.main()
