import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
PLACEHOLDER = '53ce1f45f81705a84f05aa0d6956a64180d1fd6984a79b7a784f3931a311bd6f'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def portable(path):
    path = Path(path).resolve()
    main = WS / 'westlake-harness'
    if path.is_relative_to(main):
        return str(path.relative_to(main))
    if path.is_relative_to(WS):
        return '$WORKSPACES/' + str(path.relative_to(WS))
    return str(path)


def reference(path):
    return dict(path=portable(path), sha256=sha(path))


def verify_received(row, root):
    if not row.get('equal') or row['remote_sha256'] != row['local_sha256']:
        raise ValueError('remote/local mismatch')
    local = root / row['local']
    if sha(local) != row['remote_sha256']:
        raise ValueError('received bytes changed')
    return local


def exact_tiles(app, desktop):
    ability = app.get('expected_desktop_ability')
    if not ability:
        return []
    tile_id = 'AppIconCommonView_' + app.get('launch_package', app['package']) + '.' + ability
    return [dict(page=page['tag'], tile_id=tile_id, bounds=tile['bounds'])
            for page in desktop['pages'] for tile in page['visible_tiles']
            if tile.get('id') == tile_id and tile.get('visible') == 'true']


def classify(current_sha, resource_format):
    if current_sha == PLACEHOLDER and resource_format == 'XML':
        return 'CONFIRMED_TEMPLATE_NOT_ORIGINAL_ARTWORK'
    return 'UNKNOWN_ARTWORK_REQUIRES_CURRENT_BYTES_AND_VISUAL_REVIEW'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha', required=True)
    parser.add_argument('--main', type=Path, required=True)
    parser.add_argument('--render', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sha(args.manifest) != args.manifest_sha:
        raise ValueError('inventory binding changed')
    manifest = json.loads(args.manifest.read_text())
    packages = [app['package'] for app in manifest['apps']]
    if len(packages) != len(set(packages)):
        raise ValueError('duplicate package')
    base = args.main / 'benchmark/2026-10-14-demo-desktop-ready'
    desktop_path = base / 'desktop-before/results.json'
    desktop = json.loads(desktop_path.read_text())
    if desktop['boot'] != manifest['observed_boot'] or desktop['serial'] != manifest['serial']:
        raise ValueError('desktop identity drift')
    history_path = HERE.parents[0] / '2026-10-01-icon-format-scan/ICONS.csv'
    history = {row['key']: row for row in csv.DictReader(history_path.open())}
    metadata = base / 'icon-metadata'
    before = (metadata / 'ICONS-BOOT-BEFORE.stdout.txt').read_text().strip()
    after = (metadata / 'ICONS-BOOT-AFTER.stdout.txt').read_text().strip()
    if before != after or before != manifest['observed_boot']:
        raise ValueError('metadata boot drift')
    dumps = {}
    metadata_text_path = metadata / 'ICONS-XML-CANDIDATES.stdout.txt'
    sidecar_pins = {path: digest for digest, path in re.findall(r'([0-9a-f]{64})  (/data/app/el1/bundle/public/[^\s]+/android/icon\.png)', metadata_text_path.read_text())}
    for path in sorted(metadata.glob('ICONS-BMS-*.stdout.txt')):
        text = path.read_text()
        value = json.loads(text[text.index('{'):])
        dumps[value['name']] = (path, value)
    received_path = base / 'three-icons/byte-verification.json'
    received = json.loads(received_path.read_text())
    receipts_path = args.render / 'receipts.json'
    renders = {row['package']: row for row in json.loads(receipts_path.read_text())}
    verified = {row['remote']: verify_received(row, args.main) for row in received['rows']}
    rows = []
    repairs = []
    for app in manifest['apps']:
        historical = history.get(app['key'])
        if historical and historical['apk_sha256'] != app['source_apk_sha256']:
            raise ValueError('historical APK mismatch')
        dump_path, dump = dumps.get(app['package'], (None, {}))
        tile_evidence = exact_tiles(app, desktop)
        icon = '/data/app/el1/bundle/public/' + app['package'] + '/android/icon.png'
        hap = '/data/app/el1/bundle/public/' + app['package'] + '/entry.hap'
        current_sha = sha(verified[icon]) if icon in verified else sidecar_pins.get(icon)
        resource_format = historical['selected_format'] if historical else None
        row = dict(key=app['key'], package=app['package'], disposition=app['disposition'],
                   apk_sha256=app['source_apk_sha256'], original_record=app.get('record'),
                   historical_resource=historical, original_launch_method=app.get('desktop_click', {}).get('launch_method'),
                   current_desktop_tiles=tile_evidence, desktop_complete=False,
                   current_label=dump.get('applicationInfo', {}).get('label'),
                   current_bms=reference(dump_path) if dump_path else None,
                   observation_phase='BEFORE_REMOVAL_AND_ICON_REPAIR',
                   current_icon_sha256=current_sha, artwork_status=classify(current_sha, resource_format),
                   click_retest_required=app.get('desktop_click', {}).get('launch_method') == 'ability-fallback')
        if app['disposition'] == 'remove':
            row['artwork_status'] = 'EXCLUDED_NO_ICON_REPAIR'
        if app['package'] in renders:
            if app['disposition'] not in ('keep', 'protect') or current_sha != PLACEHOLDER:
                raise ValueError('repair target drift')
            png = args.render / (app['package'] + '.png')
            if sha(png) != renders[app['package']]['png_sha256']:
                raise ValueError('render changed')
            packed = []
            with zipfile.ZipFile(verified[hap]) as archive:
                for name in ['resources/base/media/icon.png', 'resources/base/media/app_icon.png']:
                    value = hashlib.sha256(archive.read(name)).hexdigest()
                    if value != PLACEHOLDER:
                        raise ValueError('HAP icon is not same template')
                    packed.append(dict(entry=name, before_sha256=value))
            row['original_artwork_candidate'] = renders[app['package']]
            repairs.append(dict(package=app['package'], key=app['key'], execution_enabled=False,
                                sidecar=dict(path=icon, before_sha256=current_sha, after=reference(png),
                                             uid=3060, gid=3060, mode='0644', label='u:object_r:data_app_el1_file:s0'),
                                hap=dict(path=hap, before_sha256=sha(verified[hap]), entries=packed,
                                         replacement_enabled=False, reason='No signed HAP/resource-cache refresh provider admitted'),
                                cache=dict(provider=None, execution_enabled=False,
                                           database='/data/service/el1/public/bms/bundle_resources/bundleResource.db',
                                           required='Pinned exact app/ability rows, transaction backup/CAS/readback and launcher refresh evidence'),
                                rollback=dict(sidecar_before=reference(verified[icon]), hap_before=reference(verified[hap]),
                                              cache_before=None, enabled=False),
                                forbidden=['uninstall', 'reinstall user data', 'change installer/runtime', 'overwrite whole live database'],
                                acceptance=['original artwork visible', 'label unchanged', 'exact desktop tile click', 'UID/data unchanged']))
        rows.append(row)
    result = dict(schema='demo-desktop-icons-audit/v1', execution_enabled=False, device_calls=0,
                  status='STATIC_EVIDENCE_COMPLETE_REPAIR_DISABLED_CACHE_PROVIDER_PENDING',
                  inventory=reference(args.manifest), desktop=reference(desktop_path), received=reference(received_path),
                  historical_selection=reference(history_path), render_receipts=reference(receipts_path),
                  serial=manifest['serial'], boot=before, rows=rows,
                  summary=dict(rows=len(rows), dispositions=dict(Counter(row['disposition'] for row in rows)),
                               confirmed_wrong_artwork=sum(row['artwork_status'] == 'CONFIRMED_TEMPLATE_NOT_ORIGINAL_ARTWORK' for row in rows),
                               initial_three_repair_targets=len(repairs),
                               sampled_tile_packages=sum(bool(row['current_desktop_tiles']) for row in rows),
                               retained_missing_from_partial_pages=[row['key'] for row in rows if row['disposition'] in ('keep', 'protect') and not row['current_desktop_tiles']],
                               fallback_click_retest=[row['key'] for row in rows if row['click_retest_required']]))
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    (args.out / 'repair-plan.disabled.json').write_text(json.dumps(dict(execution_enabled=False, inventory=reference(args.manifest), repairs=repairs), indent=2) + '\n')
    print(json.dumps(result['summary'], indent=2))


if __name__ == '__main__':
    main()
