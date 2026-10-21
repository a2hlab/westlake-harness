#!/usr/bin/env python3
"""Check G29's one-row append (61st observation, G26 native-route candidate); no device, REA, build or cited-code run.

Reuses the G25 checker (G15 58 / G17 59 / G25 60 strict prefixes, original-renderer byte equality of
index.html/observations.csv/results.json, G24 failure semantics) and adds: the 61-row prefix, row 61 equals
added-row.json (G31: the 61-row prefix is strict and later rows may follow), independent semantic guards (offline only, not deployed, not frozen, not a clean rebuild,
no game evidence), cross-checks against the G26 receipts, and negative cases.
"""
import argparse, copy, importlib.util, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
API = ROOT / 'benchmark/2026-10-19-api-progress-update'
spec = importlib.util.spec_from_file_location('g25_checker', ROOT / 'benchmark/2026-10-21-g24-api-observation/check_observation.py')
g25 = importlib.util.module_from_spec(spec); spec.loader.exec_module(g25)
old = g25.old
C = 'benchmark/2026-10-21-commercial-game'
ALLOWED = (f'{C}/native-route-candidate/', f'{C}/native-route-build-archive/')

def semantic(row):
    old.require(row['frozen'] is False, 'public API freeze claimed')
    old.require(row['status'].startswith('OFFLINE_CANDIDATES_BUILT_NOT_DEPLOYED') and 'candidate_currently_deployed=false' in row['status']
                and '无游戏运行证据' in row['status'] and 'runtime_binding UNKNOWN' in row['status'], 'deployment or game success claimed')
    old.require(row['deployment'].startswith('candidate_currently_deployed=false') and '不部署' in row['deployment'], 'candidate written as current deployment')
    old.require('不是全源清洁重编' in row['limitations'], 'full-source clean rebuild claimed')
    old.require('游戏帧、音视频与可玩均未验证' in row['apps'] and '不满足2app冻结条件' in row['apps'], 'game frame / playable / two-app claim')
    old.require('OH回调为替身' in row['platform'], 'regression written as runtime provider binding')

def check(data, source_root, rendered=True):
    count = g25.check(data, source_root, rendered)
    base = old.read(HERE / 'original-60.json')
    old.require(len(base['rows']) == 60 and data['rows'][:60] == base['rows'], 'original60 objects changed')
    old.require(len(data['rows']) >= 61, 'G29 requires the 61-row prefix')
    row = data['rows'][60]
    semantic(row)
    for g in ('source', 'build', 'evidence'):
        old.require(len(row[g]) > 0, f'G29 {g} references dropped')
    old.require(row == old.read(HERE / 'added-row.json'), 'G29 observation changed')
    for g in ('source', 'build', 'evidence'):
        for item in row[g]:
            old.require(item['path'].startswith(ALLOWED), f"unaccepted evidence source: {item['path']}")
            old.check_ref(source_root, item); count += 1
    res = old.read(source_root / f'{C}/native-route-candidate/results.json')
    old.require(res['status'] == 'OFFLINE_CANDIDATES_BUILT_NOT_DEPLOYED' and res['runtime_binding'] == 'UNKNOWN' and res['device_calls'] == 0, 'G26 status receipt drift')
    old.require(res['candidate_sha256'] == {'host': 'ee5649f2778430e1c997f4bb2d4d4f42f53a46208b4a1b1bbaca185ddf401887', 'anl': '640b3c87e2f0f86d31b7defbd8b892515636afa61dcbbab5030d422ec1fb7d86'}, 'candidate SHA drift')
    old.require(res['baseline_sha256'] == {'host': '2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e', 'anl': 'eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c'}, 'baseline SHA drift')
    old.require(len(res['executed_commands']) == 8 and all(c['rc'] == 0 for c in res['executed_commands']), 'compile/link receipt drift')
    old.require(res['tests']['actual_c_per_version'] == {'ANL_domains': 37, 'host_routes': 50}, 'regression count drift')
    arch = old.read(source_root / f'{C}/native-route-build-archive/remote-archive.json')
    old.require(arch['status'] == 'remote_sha256_verified' and arch['archive_sha256'].startswith('e58740f5'), 'build archive not remote-verified')
    before = (HERE / 'README.before.md').read_bytes()
    old.require((API / 'README.md').read_bytes().startswith(before), 'prior README lines changed')
    return count

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root', type=Path, default=ROOT)
    source_root = ap.parse_args().source_root.resolve()
    data = old.read(API / 'observations.json')
    count = check(data, source_root)
    def mut(fn):
        d = copy.deepcopy(data); fn(d); return d
    item = data['rows'][60]['evidence'][0]
    def guard(k, v):  # tamper row 61 (and, by implication, added-row.json) so only the semantic guard can refuse
        r = copy.deepcopy(data['rows'][60]); r[k] = v; semantic(r)
    def forged_html():
        html = (API / 'index.html').read_text(); real = data['rows'][60]['status']
        old.require(html.count(real) == 1, 'row61 status not uniquely rendered')
        return html.replace(real, 'GAME_PLAYABLE；有游戏帧；候选当前部署').encode()
    files = lambda: {n: (API / n).read_bytes() for n in g25.OUTPUTS}
    cases = [
        ('history object changed', lambda: check(mut(lambda d: d['rows'][3].__setitem__('status', 'changed')), source_root, False), 'original58 objects changed'),
        ('G24 row changed', lambda: check(mut(lambda d: d['rows'][59].__setitem__('status', 'GAME_STARTED')), source_root, False), 'game success'),
        ('HTML-only success forgery', lambda: g25.rendered_equal(data, source_root, dict(files(), **{'index.html': forged_html()})), 'index.html differs'),
        ('CSV-only edit', lambda: g25.rendered_equal(data, source_root, dict(files(), **{'observations.csv': files()['observations.csv'] + b'x'})), 'observations.csv differs'),
        ('rows truncated below 61', lambda: check(mut(lambda d: d['rows'].__delitem__(slice(60, None))), source_root, False), '61-row prefix'),
        ('appended row with unverified missing reference', lambda: g25.rendered_equal(mut(lambda d: d['rows'].append(dict(d['rows'][60], id='OBS-FUTURE',
            evidence=[dict(item, path=f'{C}/native-route-candidate/intentionally-missing.json')]))), source_root, {}), 'renderer refused'),
        ('row61 edited', lambda: check(mut(lambda d: d['rows'][60].__setitem__('name', 'changed')), source_root, False), 'G29 observation changed'),
        ('evidence dropped', lambda: check(mut(lambda d: d['rows'][60].__setitem__('evidence', [])), source_root, False), 'evidence references dropped'),
        ('claimed frozen', lambda: guard('frozen', True), 'freeze'),
        ('claimed current deployment', lambda: guard('deployment', 'candidate_currently_deployed=true；当前部署'), 'current deployment'),
        ('claimed game playable', lambda: guard('apps', '原神可玩，有游戏帧'), 'playable'),
        ('claimed clean rebuild', lambda: guard('limitations', '全源清洁重编'), 'clean rebuild'),
        ('missing reference', lambda: old.check_ref(source_root, dict(item, path=f'{C}/native-route-candidate/intentionally-missing.json')), 'missing/nonregular'),
        ('reference SHA drift', lambda: old.check_ref(source_root, dict(item, sha256='0' * 64)), 'SHA drift'),
    ]
    later = mut(lambda d: d['rows'].append(dict(d['rows'][60], id='OBS-FUTURE')))
    old.require(check(later, source_root, False) == count, 'G29 allows a later append')
    refusals = []
    for name, call, expected in cases:
        try: call()
        except ValueError as exc:
            old.require(expected in str(exc), f'unexpected refusal for {name}: {exc}')
            refusals.append({'case': name, 'refused': True, 'reason': str(exc)})
        else: raise ValueError(f'negative case accepted: {name}')
    print(json.dumps({'status': 'PASS', 'rows': len(data['rows']), 'original_rows_unchanged': 60, 'added_rows': 1,
        'exact_references': count, 'html_csv_results_byte_equal_to_original_renderer': True, 'historical315_unchanged': True,
        'g15_g17_g25_prefix_checks_pass': True, 'negative_cases': refusals, 'candidate_currently_deployed': False,
        'public_api_freeze': False, 'full_source_clean_rebuild': False, 'game_evidence': False,
        'device_calls': 0, 'rea_calls': 0, 'runtime_builds': 0, 'remote_publication_verified': False}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
