import hashlib
import importlib.metadata
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
WORKSPACES = HERE.parents[2]
MASTER = WORKSPACES / 'westlake-harness'
ANDROID = '{http://schemas.android.com/apk/res/android}'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def portable(value):
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, str):
        return value.replace(str(WORKSPACES) + '/', '$WORKSPACES/').replace(str(Path.home()) + '/', '$HOME/')
    return value


def expand(value):
    return Path(value.replace('$WORKSPACES/', str(WORKSPACES) + '/').replace('$HOME/', str(Path.home()) + '/'))


def write(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value), indent=2, ensure_ascii=False) + '\n')


def resolve_labels(apk):
    application = apk.get_android_manifest_xml().find('application')
    raw = application.get(ANDROID + 'label')
    owner = 'application'
    if raw is None:
        mains = sorted(apk.get_main_activities())
        for element in application:
            name = element.get(ANDROID + 'name', '')
            if name.startswith('.'):
                name = apk.get_package() + name
            if name in mains and element.get(ANDROID + 'label'):
                raw = element.get(ANDROID + 'label')
                owner = name
                break
    variants = []
    if raw and raw.startswith('@'):
        resources = apk.get_android_resources()
        if resources:
            resource_id, package = resources.parse_id(raw)
            if package != 'android':
                variants = [dict(locale=config.get_language_and_region().replace('\x00', ''), value=value)
                    for config, value in resources.get_resolved_res_configs(resource_id)
                    if isinstance(value, str) and value and not value.startswith('@')]
    elif raw:
        variants = [dict(locale='', value=raw)]
    return dict(manifest_label=raw, owner=owner, default=apk.get_app_name(), variants=variants)


def main():
    from androguard.core.apk import APK
    from loguru import logger
    logger.remove()
    reference_path = MASTER / 'benchmark/2026-10-03-u14-stage-b/inputs/reference.json'
    signoff_path = MASTER / 'benchmark/2026-10-03-u14-stage-a-plan/window1-signoff/outer-signoff.json'
    reference = json.loads(reference_path.read_text())
    signoff = json.loads(signoff_path.read_text())
    lit = {key: value for key, value in reference['keys'].items() if value['verdict'] == 'lit'}
    gains = signoff['summary']['gains']
    assert len(lit) == 126 and set(gains) == {'vlc', 'termux', 'cv2-org-andresoviedo-dddmodel2'}
    assert not set(lit).intersection(gains)
    write('inputs/reference.json', reference)
    write('inputs/window1-signoff.json', signoff)
    index_path = WORKSPACES / 'westlake-inputs/corpus-v2/fdroid/index-v2.json'
    index = json.loads(index_path.read_text())
    corpus_path = WORKSPACES / 'westlake-harness-t4/benchmark/2026-10-01-corpus-v2-inputs/apps-v2.json'
    corpus = {row['key']: row for row in json.loads(corpus_path.read_text())['apps']}
    rows, metadata, cache = [], {}, {}
    for key in sorted(set(lit) | set(gains)):
        if key in lit:
            screenshot = re.sub(r'\s+\*gain.*$', '', lit[key]['t20'])
            record_path = expand(screenshot).parent / 'record.json'
            signed = dict(kind='reference-lit', source=str(reference_path), verdict='lit', row=lit[key])
        else:
            window = WORKSPACES / 'westlake-harness-u7-executor/benchmark/2026-10-03-u14-stage-a-plan/window1'
            candidates = sorted(window.glob('u14-A1-r3-*/*/runner/*/*/*/' + key + '/record.json'))
            if len(candidates) != 1:
                raise ValueError('Ambiguous signed gain run: ' + key)
            record_path = candidates[0]
            screenshot = str(record_path.parent / 't20.jpeg')
            signed = dict(kind='U14-window1-gain', source=str(signoff_path), verdict='lit', row=signoff['keys'][key], note=gains[key])
        record = json.loads(record_path.read_text())
        apk_path = expand(record['input_apk'])
        digest = sha(apk_path)
        if digest != record['apk_sha256'] or record['key'] != key:
            raise ValueError('APK / run identity conflict: ' + key)
        if digest not in cache:
            apk = APK(str(apk_path))
            cache[digest] = dict(package=apk.get_package(), version=apk.get_androidversion_name(),
                version_code=apk.get_androidversion_code(), labels=resolve_labels(apk))
        identity = cache[digest]
        if identity['package'] != record['package']:
            raise ValueError('Package conflict: ' + key)
        corpus_match = corpus.get(key)
        if corpus_match and (corpus_match['apk_sha256'] != digest or corpus_match['package'] != identity['package']):
            raise ValueError('Corpus identity conflict: ' + key)
        fdroid = index['packages'].get(identity['package'])
        input_receipt_path = apk_path.parent / 'app-input.json'
        input_receipt = None
        if input_receipt_path.is_file():
            receipt = json.loads(input_receipt_path.read_text())
            if receipt.get('apk_sha256') == digest:
                input_receipt = dict(path=str(input_receipt_path), sha256=sha(input_receipt_path),
                    application=receipt.get('application', {}))
        index_matches = []
        if fdroid:
            entry = fdroid['metadata']
            metadata[identity['package']] = {field: entry.get(field) for field in
                ['name', 'summary', 'categories', 'webSite', 'sourceCode', 'license']}
            descriptions = entry.get('description', {})
            metadata[identity['package']]['description_excerpt'] = {
                locale: text[:1200] for locale, text in descriptions.items()
                if locale in ['zh-CN', 'zh-TW', 'en-US', 'en-GB', 'en']}
            for version_sha, version in fdroid['versions'].items():
                if version_sha == digest or version.get('file', {}).get('sha256') == digest:
                    index_matches.append(dict(sha256=version_sha, file=version.get('file'),
                        manifest=version.get('manifest', {})))
        screenshot_path = expand(screenshot)
        signed_sha = lit.get(key, {}).get('t20_sha256')
        screenshot_sha = sha(screenshot_path) if screenshot_path.is_file() else None
        if signed_sha and screenshot_sha != signed_sha:
            raise ValueError('Signed screenshot identity conflict: ' + key)
        rows.append(dict(key=key, apk_path=str(apk_path), apk_sha256=digest, **identity,
            record_identity=dict(key=record['key'], package=record['package'], apk_sha256=record['apk_sha256']),
            record_path=str(record_path), record_sha256=sha(record_path), install_path=str(record_path.parent / 'install.txt'),
            install_sha256=sha(record_path.parent / 'install.txt'), signed=signed, screenshot_reference=screenshot,
            screenshot_sha256=screenshot_sha, source_index_version_matches=index_matches,
            corpus=corpus_match, input_receipt=input_receipt))
        print(key, identity['package'], identity['version'], 'label=' + identity['labels']['default'], flush=True)
    write('inputs/apk-metadata.json', rows)
    write('inputs/fdroid-metadata.json', metadata)
    write('inputs/provenance.json', dict(reference=dict(path=str(reference_path), sha256=sha(reference_path)),
        signoff=dict(path=str(signoff_path), sha256=sha(signoff_path)),
        fdroid_index=dict(path=str(index_path), sha256=sha(index_path)),
        corpus=dict(path=str(corpus_path), sha256=sha(corpus_path)),
        parser=dict(name='androguard', version=importlib.metadata.version('androguard')),
        screenshot_selection='not performed; references only', network_access=False, board_access=False))


if __name__ == '__main__':
    main()
