#!/usr/bin/env python3
"""Check G25's one-row append (60th observation, G24 loader trial); no device, REA, build or cited-code run.

Reuses the G17 checker (strict 59-row prefix, G15 58-row prefix, renderer CSV/HTML/results consistency)
and adds: row 60 equals added-row.json (G29: the 60-row prefix is strict and later rows may follow), independent semantic guards (no game success, candidate not the
current deployment, not frozen), cross-checks against the G24 receipts, and negative cases.
"""
import argparse, copy, hashlib, importlib.util, json, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
API = ROOT / 'benchmark/2026-10-19-api-progress-update'
spec = importlib.util.spec_from_file_location('g17_checker', ROOT / 'benchmark/2026-10-21-launch-observation-update/check_observation.py')
g17 = importlib.util.module_from_spec(spec); spec.loader.exec_module(g17)
old = g17.old
C = 'benchmark/2026-10-21-commercial-game'
RENDER_SHA = '0276c50ee6ae53a6af5e45651a7c727c4cfe8fc4d30b9bb15208d67c780fc147'
OUTPUTS = ('index.html', 'observations.csv', 'results.json')
ALLOWED = (f'{C}/gles-loader-candidate/', f'{C}/gles-window02/closed/', f'{C}/gles-window02/launch-review-01/')

def semantic(row):
    old.require(row['frozen'] is False, 'public API freeze claimed')
    old.require(row['status'].startswith('CANDIDATE_TRIAL_GAME_FAILED') and '无游戏帧' in row['status'] and '已恢复基线' in row['status'], 'game success or recovery state claimed')
    old.require('候选不是当前部署' in row['deployment'] and '当前设备为已恢复基线' in row['deployment'], 'candidate written as current deployment')
    old.require('game_frames_observed=false' in row['apps'] and '不满足2app冻结条件' in row['apps'], 'game frame or two-app claim')
    old.require('不等于GLES功能完成或游戏可用' in row['limitations'] and 'maps未采到' in row['limitations'], 'GLES/game-usable or maps claim')

def expected_render(data, source_root):
    """Run a byte-identical copy of the ORIGINAL renderer on the checked JSON in a mirrored temp tree."""
    old.require(hashlib.sha256((API / 'render.py').read_bytes()).hexdigest() == RENDER_SHA, 'renderer changed')
    with tempfile.TemporaryDirectory(prefix='g25-render-') as t:
        d = Path(t) / API.relative_to(ROOT); d.mkdir(parents=True)
        shutil.copyfile(API / 'render.py', d / 'render.py')
        (d / 'observations.json').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
        r = subprocess.run([sys.executable, '-B', str(d / 'render.py'), '--source-root', str(source_root)], capture_output=True, text=True)
        old.require(r.returncode == 0, 'renderer refused the checked JSON: ' + r.stderr.strip()[-200:])
        return {n: (d / n).read_bytes() for n in OUTPUTS}

def rendered_equal(data, source_root, actual=None):
    if actual is None:  # checking the files on disk: they must be rendered from exactly this JSON
        old.require((API / 'observations.json').read_bytes() == (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode(), 'JSON serialization drift')
        actual = {n: (API / n).read_bytes() for n in OUTPUTS}
    want = expected_render(data, source_root)
    for n in OUTPUTS:
        old.require(actual[n] == want[n], f'{n} differs from original renderer output for the checked JSON')

def check(data, source_root, rendered=True):
    count = g17.check(data, source_root, rendered)
    base = old.read(HERE / 'original-59.json')
    old.require(len(base['rows']) == 59 and data['rows'][:59] == base['rows'], 'original59 objects changed')
    old.require(len(data['rows']) >= 60, 'G25 requires the 60-row prefix')
    row = data['rows'][59]
    semantic(row)
    old.require(row == old.read(HERE / 'added-row.json'), 'G25 observation changed')
    for g in ('source', 'build', 'evidence'):
        for item in row[g]:
            old.require(item['path'].startswith(ALLOWED), f"unaccepted evidence source: {item['path']}")
            old.check_ref(source_root, item); count += 1
    closed = old.read(source_root / f'{C}/gles-window02/closed/results.json')
    review = old.read(source_root / f'{C}/gles-window02/launch-review-01/results.json')
    old.require(closed['apply_rc'] == 0 and closed['rollback_rc'] == 0 and closed['baseline_all_equal'] is True, 'apply/rollback/baseline receipt drift')
    old.require(closed['game'] == 'white_then_desktop_exit1' and closed['game_child_maps'] == 'not captured', 'game/maps receipt drift')
    old.require(review['game_frames_observed'] is False and review['comparison']['candidate']['libGLESv2.so']['count'] == 0
                and review['comparison']['candidate']['__register_atfork']['count'] >= 1 and review['comparison']['candidate']['__errno']['count'] >= 1, 'loader-progress receipt drift')
    old.require(old.read(source_root / f'{C}/gles-window02/closed/remote-archive.json')['status'] == 'remote_sha256_verified', 'execution archive not remote-verified')
    old.require(old.read(source_root / f'{C}/gles-loader-candidate/outer-archive/receipt.json')['status'] == 'REMOTE_ARCHIVE_SHA_VERIFIED', 'build archive not remote-verified')
    if rendered:
        rendered_equal(data, source_root)
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
    item = data['rows'][59]['evidence'][0]
    def forged_html():  # JSON, article count and IDs unchanged; only row 60's rendered status text forged
        html = (API / 'index.html').read_text(); real = data['rows'][59]['status']
        old.require(html.count(real) == 1, 'row60 status not uniquely rendered')
        return html.replace(real, 'GAME_PLAYABLE；有游戏帧；候选当前部署').encode()
    def both(d, k, v):  # tamper the table AND a copy of added-row, so only the semantic guard can refuse
        d['rows'][59][k] = v; semantic(d['rows'][59])
    cases = [
        ('history object changed', lambda: check(mut(lambda d: d['rows'][10].__setitem__('status', 'changed')), source_root, False), 'original58 objects changed'),
        ('G17 row changed', lambda: check(mut(lambda d: d['rows'][58].__setitem__('apps', 'changed')), source_root, False), 'new observation changed'),
        ('game success claimed', lambda: both(copy.deepcopy(data), 'status', 'GAME_STARTED；有游戏帧'), 'game success'),
        ('candidate as current deployment', lambda: both(copy.deepcopy(data), 'deployment', '候选为当前部署'), 'current deployment'),
        ('API frozen', lambda: both(copy.deepcopy(data), 'frozen', True), 'freeze'),
        ('row60 edited', lambda: check(mut(lambda d: d['rows'][59].__setitem__('name', 'changed')), source_root, False), 'G25 observation changed'),
        ('missing reference', lambda: old.check_ref(source_root, dict(item, path=f'{C}/gles-window02/closed/intentionally-missing.json')), 'missing/nonregular'),
        ('reference SHA drift', lambda: old.check_ref(source_root, dict(item, sha256='0' * 64)), 'SHA drift'),
        ('rows truncated below 60', lambda: check(mut(lambda d: d['rows'][59:] and d['rows'].__delitem__(slice(59, None))), source_root, False), '60-row prefix'),
        ('appended row with unverified missing reference', lambda: rendered_equal(mut(lambda d: d['rows'].append(dict(d['rows'][59], id='OBS-FUTURE',
            evidence=[dict(item, path=f'{C}/gles-window02/closed/intentionally-missing.json')]))), source_root, {}), 'renderer refused'),
        ('HTML-only status forgery', lambda: rendered_equal(data, source_root, dict({n: (API / n).read_bytes() for n in OUTPUTS},
            **{'index.html': forged_html()})), 'index.html differs'),
    ]
    later = mut(lambda d: d['rows'].append(dict(d['rows'][59], id='OBS-FUTURE')))
    old.require(check(later, source_root, False) == count, 'G25 allows a later append')
    refusals = []
    for name, call, expected in cases:
        try: call()
        except ValueError as exc:
            old.require(expected in str(exc), f'unexpected refusal for {name}: {exc}')
            refusals.append({'case': name, 'refused': True, 'reason': str(exc)})
        else: raise ValueError(f'negative case accepted: {name}')
    print(json.dumps({'status': 'PASS', 'rows': len(data['rows']), 'original_rows_unchanged': 59, 'added_rows': 1,
        'exact_references': count, 'html_csv_results_byte_equal_to_original_renderer': True, 'historical315_unchanged': True,
        'g15_and_g17_prefix_checks_pass': True, 'negative_cases': refusals, 'current_deployment': 'restored baseline',
        'game_frames_observed': False, 'public_api_freeze': False, 'device_calls': 0, 'rea_calls': 0, 'runtime_builds': 0,
        'remote_publication_verified': False}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
