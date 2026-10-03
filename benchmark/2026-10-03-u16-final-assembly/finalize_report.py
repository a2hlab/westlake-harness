"""Summarize local gate evidence and pending bindings; never apply approvals."""
from prepare import HERE, MASTER, RELEASE, load, portable, save, sha


def main():
    summaries = {}
    for variant in ('common', '61b'):
        raw = sorted((HERE / '.artifacts/raw' / variant).glob('darwin-*'))[-1]
        native = load(raw / 'native.txt')
        static = load(raw / 'static.json')
        image_text = (raw / 'image.txt').read_text()
        image = __import__('json').loads(image_text.splitlines()[-1])
        save(HERE / variant / 'native-report.json', native)
        save(HERE / variant / 'static-report.json', static)
        save(HERE / variant / 'image-report.json', image)
        save(HERE / variant / 't4b-report.json', load(raw / 't4b.json'))
        summaries[variant] = {'native_status': native['status'], 'native_errors': native['errors'],
            'native_counts': {gate: {name: row.get(name) for name in ('rejected', 'excepted')} for gate, row in native['gates'].items()},
            'static_status': static['status'], 'static_members': [{name: row.get(name) for name in ('target', 'status', 'delta_sha256')} for row in static['members']],
            'G1': image['G1'], 'G2': image['G2'], 'raw_report_folder': raw}
    for source in sorted((RELEASE / 'logs').iterdir()):
        if source.is_file():
            destination = HERE / 'evidence/build' / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(portable(source.read_text(errors='backslashreplace')))
    save(HERE / 'fresh-gates-summary.json', {'variants': summaries, 'execution_enabled': False,
         'rollout_ready': False, 'object_chain': 'pending outer frozen oatdump', 'new_pair_exception': 'pending outer signature'})
    for variant in ('common', '61b'):
        composition = load(HERE / variant / 'composition.json')
        native = load(HERE / variant / 'native-report.json')
        rows = [{'gate': gate, 'issue_id': finding['issue_id'], 'package_manifest_sha256': composition['native_manifest_sha256'],
                 'inputs_sha256': composition['native_inputs_sha256'], 'status': 'unsigned-preview',
                 'approved_by': None, 'approved_at': None, 'finding': finding,
                 'required': 'outer transfer/review against U15 bindings plus U16 signed17-row scope; no table apply'}
                for gate, report in native['gates'].items() for finding in report['findings']]
        save(HERE / variant / 'registry-preview.json', {'rows': rows, 'count': len(rows), 'applied': False})
    save(HERE / 'results.json', {'execution_enabled': False, 'rollout_ready': False, 'board_access': False, 'vm_ssh_access': False,
          'strict_identical': 26, 'pair_total': 27, 'compiler_receipts_verified': 2,
          'content_variants': {variant: load(HERE / variant / 'composition.json') for variant in ('common', '61b')},
          'pending': ['new boot.art object chain and exact-pair approval', 'fresh remote G2 Mac/VM',
                      'eight WifiManager donor allow_add descriptors', '208 native finding bindings transfer/review',
                      'Flutter static delta190c0607 approval binding', 'future promoted U15 transaction BASE'],
          'not_production_pass': True})


if __name__ == '__main__':
    main()
