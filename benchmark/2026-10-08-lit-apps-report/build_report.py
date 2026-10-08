import collections
import csv
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def read(name):
    return json.loads((HERE / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def choose_localized(mapping, language):
    preferred = ['zh-CN', 'zh-Hans', 'zh', 'zh-TW'] if language == 'zh' else ['en-US', 'en-GB', 'en']
    return next(((mapping[locale], locale) for locale in preferred if mapping.get(locale)), ('', ''))


def choose_name(labels, metadata, language):
    variants = labels['variants']
    preferred = ['zh-rCN', 'zh', 'zh-rSG', 'zh-rTW', 'zh-rHK'] if language == 'zh' else ['en-rUS', 'en', 'en-rGB', '']
    for locale in preferred:
        for variant in variants:
            if variant['locale'] == locale:
                return variant['value'], 'APK AndroidManifest/resource label', locale or 'default'
    value, locale = choose_localized(metadata.get('name') or {}, language)
    if value:
        return value, 'F-Droid localized name (APK locale absent)', locale
    return labels['default'], 'APK default label (locale absent; original name retained)', 'default'


def validate_identity(row):
    for field in ['key', 'package', 'apk_sha256']:
        if row[field] != row['record_identity'][field]:
            raise ValueError('Identity conflict: ' + field)
    if not re.fullmatch('[0-9a-f]{64}', row['apk_sha256']):
        raise ValueError('Invalid APK SHA')


def classify_source(row):
    if row.get('corpus'):
        return 'cv2 语料（F-Droid）', 'APK SHA/package match the corpus manifest and F-Droid index', 'verified'
    if row['source_index_version_matches']:
        return 'F-Droid', 'Exact APK SHA in the frozen F-Droid index', 'verified'
    receipt = row.get('input_receipt') or {}
    application = receipt.get('application') or {}
    delivery = application.get('delivery', '')
    reference = application.get('reference', '')
    if 'APKPure' in delivery:
        return '第三方 APK（APKPure）', delivery + '; open-source project, not a commercial-app classification', 'receipt-backed'
    if 'F-Droid' in reference:
        return 'F-Droid', reference + '; input receipt matched APK SHA; this older version is absent from the current index', 'receipt-backed'
    return 'uncertain', 'No exact repository match or attributable delivery receipt', 'uncertain'


def assemble():
    reference = read('inputs/reference.json')
    signoff = read('inputs/window1-signoff.json')
    expected = {key for key, value in reference['keys'].items() if value['verdict'] == 'lit'}
    if len(expected) != 126 or set(signoff['summary']['gains']) != {'vlc', 'termux', 'cv2-org-andresoviedo-dddmodel2'}:
        raise ValueError('Signed scope drift')
    expected.update(signoff['summary']['gains'])
    metadata = read('inputs/fdroid-metadata.json')
    input_rows = read('inputs/apk-metadata.json')
    with (HERE / 'purposes.tsv').open() as stream:
        purposes = list(csv.DictReader(stream, delimiter='\t'))
    by_key = {row['key']: row for row in purposes}
    if len(by_key) != len(purposes) or set(by_key) != expected:
        raise ValueError('Purpose keys missing, extra or duplicated')
    if {row['key'] for row in input_rows} != expected or len(input_rows) != len(expected):
        raise ValueError('APK metadata scope drift')
    output = []
    for row in input_rows:
        validate_identity(row)
        description = by_key[row['key']]
        purpose = description['purpose_zh']
        if len(re.findall('[。！？]', purpose)) != 1 or not purpose.endswith('。') or not re.search('[\u4e00-\u9fff]', purpose):
            raise ValueError('Purpose must be one Chinese sentence')
        info = metadata.get(row['package'], {})
        evidence_field = description['evidence_field']
        evidence, evidence_locale = choose_localized(info.get(evidence_field) or {}, 'zh')
        if not evidence:
            evidence, evidence_locale = choose_localized(info.get(evidence_field) or {}, 'en')
        if not evidence:
            raise ValueError('Missing purpose evidence: ' + row['key'])
        name_zh, name_zh_source, name_zh_locale = choose_name(row['labels'], info, 'zh')
        name_en, name_en_source, name_en_locale = choose_name(row['labels'], info, 'en')
        source, source_detail, source_status = classify_source(row)
        signed = row['signed']
        output.append(dict(key=row['key'], package=row['package'], version=str(row['version']),
            version_code=str(row['version_code']), apk_path=row['apk_path'], apk_sha256=row['apk_sha256'],
            display_name_zh=name_zh, display_name_en=name_en, source=source, source_status=source_status,
            source_detail=source_detail, category=description['category'], purpose_zh=purpose,
            purpose_status='F-Droid metadata-backed; not a platform functional-test result',
            purpose_evidence='inputs/fdroid-metadata.json#' + row['package'] + '/' + evidence_field + '/' + evidence_locale,
            purpose_evidence_text=evidence, purpose_evidence_locale=evidence_locale,
            name_zh_source=name_zh_source, name_zh_locale=name_zh_locale,
            name_en_source=name_en_source, name_en_locale=name_en_locale,
            manifest_label=str(row['labels']['manifest_label']), record_path=row['record_path'],
            record_sha256=row['record_sha256'], install_path=row['install_path'], install_sha256=row['install_sha256'],
            signed_scope=signed['kind'], signoff_path=signed['source'],
            signed_ui_note=signed.get('note', ''), screenshot_reference=row['screenshot_reference'],
            screenshot_sha256=row['screenshot_sha256'] or '',
            lighting_scope='自有界面已签认上屏；不表示全部功能可用'))
    output.sort(key=lambda row: row['key'])
    packages = collections.defaultdict(list)
    for row in output:
        packages[row['package']].append(row['key'])
    return dict(schema='lit-apps-report/v1', scope_keys=129, distinct_packages=len(packages),
        count_interpretation='Historical signed own-UI keys, not all-function compatibility or current simultaneous board state',
        duplicate_packages={package: keys for package, keys in packages.items() if len(keys) > 1},
        provenance=read('inputs/provenance.json'), apps=output)


def main():
    report = assemble()
    (HERE / 'apps.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    with (HERE / 'apps.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(report['apps'][0]))
        writer.writeheader()
        writer.writerows(report['apps'])
    results = dict(keys=len(report['apps']), reference_lit=126, signed_window1_gains=3,
        distinct_packages=report['distinct_packages'], duplicate_packages=report['duplicate_packages'],
        distinct_apk_sha256=len({row['apk_sha256'] for row in report['apps']}),
        apk_labels_resolved=sum(bool(row['display_name_en']) for row in report['apps']),
        chinese_apk_labels=sum(row['name_zh_source'] == 'APK AndroidManifest/resource label' for row in report['apps']),
        names_by_zh_source=dict(collections.Counter(row['name_zh_source'] for row in report['apps'])),
        purpose_metadata_backed=len(report['apps']),
        uncertain_sources=[row['key'] for row in report['apps'] if row['source_status'] == 'uncertain'],
        source_counts=dict(collections.Counter(row['source'] for row in report['apps'])),
        category_counts_by_key=dict(collections.Counter(row['category'] for row in report['apps'])),
        category_counts_by_package=dict(collections.Counter(next(row['category'] for row in report['apps'] if row['package'] == package)
            for package in sorted({row['package'] for row in report['apps']}))),
        apps_csv_sha256=sha(HERE / 'apps.csv'), apps_json_sha256=sha(HERE / 'apps.json'),
        screenshots_selected=0, board_operations=0, network_operations=0)
    (HERE / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()
