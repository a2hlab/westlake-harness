#!/usr/bin/env python3
"""Check G33's one-row append (63rd observation, G30 locale ABI candidate); no device, REA, build or cited-code run.

Reuses the G31 checker (G15 58 / G17 59 / G25 60 / G29 61 / G31 62 strict prefixes, original-renderer byte
equality of index.html/observations.csv/results.json, G24/G26/G28 failure semantics) and adds: exactly 63
rows, row 63 equals added-row.json, references are exactly the 56 fixed public G30 paths, independent
semantic guards (offline only, not deployed, not frozen, no OS closure or OH semantics claim, rc124 kept as
an environment failure, archive status as a snapshot of the fixed G30 landing), cross-checks against the G30
receipts, positive and negative cases. The archive statement is proven from pinned snapshot sources only, so
a later genuine remote receipt cannot falsify this historical observation.
"""
import argparse, copy, importlib.util, json, os, shutil, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
API = ROOT / 'benchmark/2026-10-19-api-progress-update'
spec = importlib.util.spec_from_file_location('g31_checker', ROOT / 'benchmark/2026-10-21-g28-api-observation/check_observation.py')
g31 = importlib.util.module_from_spec(spec); spec.loader.exec_module(g31)
g25, old = g31.g25, g31.old
L = 'benchmark/2026-10-21-commercial-game/locale-abi-candidate'
RUST = 'tools/spec-checks/tests/commercial_game_locale_abi_candidate.rs'
CANDIDATE = '4296f8052b6ccc130df83366717903695eba38fcde19c462ee64521414696f0b'
G30_MASTER = '8acf1ed616d7110ab72ba9a11c2ba1c423d1e097'
BASELINE = 'd20530661a30b8af7bbfb30a6b7138d0b6a6bb5d82e6cb8d733a41ae23886c65'

def semantic(row):
    old.require(row['frozen'] is False, 'public API freeze claimed')
    old.require(row['status'].startswith('OFFLINE_CANDIDATE_VERIFIED_NOT_DEPLOYED') and 'candidate_currently_deployed=false' in row['status']
                and 'runtime_namespace_binding UNKNOWN' in row['status'] and '无游戏运行证据' in row['status'], 'deployment or game success claimed')
    old.require(row['deployment'].startswith('candidate_currently_deployed=false') and '不部署' in row['deployment'] and '不冻结' in row['deployment']
                and '不称原神可玩' in row['deployment'], 'candidate written as current deployment')
    old.require('G30固定主线8acf1ed61交件时的观察快照' in row['deployment'] and '当时远端未验证；不声称已远端核验' in row['deployment']
                and '日后补齐的远端回执不改变本条历史快照' in row['deployment'], 'remote archive verification claimed without receipt')
    old.require('未上板' in row['apps'] and '游戏帧与可玩均UNKNOWN' in row['apps'] and '不满足2app冻结条件' in row['apps'], 'game frame / playable / two-app claim')
    lim = row['limitations']
    old.require('不是完整Linux OS镜像或宿主动态库闭合' in lim and '也不是OH实际语义验证' in lim, 'full OS closure or OH semantics claimed')
    old.require('rc124超时且无编译证据，是环境失败不是编译失败' in lim and 'host01' in lim, 'rc124/host01 history rewritten')
    old.require('不含__assert2' in row['method'], '__assert2 written as part of the candidate')
    old.require('宿主测试不替代OH运行证据' in row['platform'], 'host test written as OH runtime evidence')

def archive_snapshot(snap, public):
    old.require(snap['commit'] == G30_MASTER and snap['remote_receipts_in_g30_tree'] == [] and snap['remote_receipts_in_g30_landing_paths'] == [], 'archive snapshot pin drift')
    old.require(not any('remote' in p.rsplit('/', 1)[-1] for p in public), 'pinned G30 landing lists a remote receipt')

def check(data, source_root, rendered=True):
    count = g31.check(data, source_root, rendered)
    base = old.read(HERE / 'original-62.json')
    old.require(len(base['rows']) == 62 and data['rows'][:62] == base['rows'], 'original62 objects changed')
    old.require(len(data['rows']) == 63, 'G33 requires exactly 63 rows')
    row = data['rows'][62]
    semantic(row)
    for g in ('source', 'build', 'evidence'):
        old.require(len(row[g]) > 0, f'G33 {g} references dropped')
    old.require(row == old.read(HERE / 'added-row.json'), 'G33 observation changed')
    public = (source_root / f'{L}/final/landing-paths.txt').read_text().split()
    paths = [i['path'] for g in ('source', 'build', 'evidence') for i in row[g]]
    old.require(len(public) == 56 and sorted(paths) == sorted(public), 'references differ from the 56 fixed G30 public paths')
    for g in ('source', 'build', 'evidence'):
        for item in row[g]:
            old.require(item['path'].startswith(L + '/') or item['path'] == RUST, f"unaccepted evidence source: {item['path']}")
            old.check_ref(source_root, item); count += 1
    res = old.read(source_root / f'{L}/final/results.json')
    old.require(res['status'] == 'OFFLINE_CANDIDATE_VERIFIED_NOT_DEPLOYED' and res['candidate_sha256'] == CANDIDATE and res['baseline_sha256'] == BASELINE
                and res['candidate_reproductions'] == 2 and res['input_bookends'] == 55 and res['old_objects_identical'] is True, 'G30 build receipt drift')
    old.require(res['locale_actual_TU']['classifications'] == 257 and res['locale_actual_TU']['integer_cases'] == 90 and res['abi_counterexample_tests'] == 9, 'G30 test count drift')
    elf = old.read(source_root / f'{L}/evidence/elf-review.json')
    old.require(elf['preserved_dynsym_tuples'] == 44 and elf['added_exports'] == ['_ctype_@@LIBC', 'strtoll_l@@LIBC', 'strtoull_l@@LIBC']
                and elf['needed'] == ['libc.so'] and elf['ctype_pointer_size'] == 8 and elf['ctype_table_bytes_verified'] == 257
                and elf['runtime_namespace_binding'] == 'UNKNOWN' and elf['OH_callbacks_execution'] == 'NOT_TESTED', 'ELF receipt drift')
    book = old.read(source_root / f'{L}/final/candidate02-bookends.json')
    old.require(book['artifact_sha256'] == CANDIDATE and book['input_count'] == 55 and book['rc'] == 0 and all(c['rc'] == 0 for c in book['commands']), 'bookend receipt drift')
    old.require(old.read(source_root / f'{L}/final/host-receipt.json')['status'] == 'HOST_REAL_LOCALE_FUNCTIONS_PASS', 'host receipt drift')
    old.require(old.read(source_root / f'{L}/final/preservation-receipt.json')['status'] == 'BASELINE_CANDIDATE_REAL_BODY_REGRESSION_PASS', 'preservation receipt drift')
    cp = old.read(source_root / f'{L}/build-checkpoint-01/results.json')
    old.require(cp['rc'] == 124 and cp['status'] == 'EXECUTION_ENTRY_TIMEOUT_NO_BUILD_RESULT', 'rc124 checkpoint drift')
    # Archive snapshot: proven only from the SHA-pinned G30 landing list (a row reference) and input pins, never
    # from the current tree, so a later genuine remote receipt leaves this historical observation true.
    archive_snapshot(old.read(HERE / 'input-pins.json')['archive_snapshot'], public)
    before = (HERE / 'README.before.md').read_bytes()
    old.require((API / 'README.md').read_bytes().startswith(before), 'prior README lines changed')
    return count

def later_receipt_root(source_root):
    """Positive case: a temp source root equal to source_root plus a later, genuine-shaped G30 remote-archive.json.
    Directories along the receipt path are real; siblings are symlinked directories or copied files."""
    t = Path(tempfile.mkdtemp(prefix='g33-later-receipt-'))
    src, dst = source_root, t
    for part in Path(f'{L}/final').parts:
        for e in os.scandir(src):
            if e.name == part: continue
            (os.symlink(e.path, dst / e.name) if e.is_dir(follow_symlinks=False) else shutil.copy2(e.path, dst / e.name, follow_symlinks=False))
        src, dst = src / part, dst / part; dst.mkdir()
    for e in os.scandir(src):
        shutil.copy2(e.path, dst / e.name)
    (dst / 'remote-archive.json').write_text(json.dumps({'status': 'remote_sha256_verified', 'archive_sha256': 'f' * 64, 'bytes': 1,
        'verified_at': '2026-10-22T00:00:00+08:00', 'note': 'synthetic later receipt for the G33 positive case'}, indent=2) + '\n')
    return t

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root', type=Path, default=ROOT)
    source_root = ap.parse_args().source_root.resolve()
    data = old.read(API / 'observations.json')
    count = check(data, source_root)
    def mut(fn):
        d = copy.deepcopy(data); fn(d); return d
    item = data['rows'][62]['evidence'][0]
    def guard(k, v):  # tamper row 63 (and, by implication, added-row.json) so only the semantic guard can refuse
        r = copy.deepcopy(data['rows'][62]); r[k] = v; semantic(r)
    def forged_html():  # JSON, article count and IDs unchanged; only row 63's rendered status text forged
        html = (API / 'index.html').read_text(); real = data['rows'][62]['status']
        old.require(html.count(real) == 1, 'row63 status not uniquely rendered')
        return html.replace(real, 'GAME_PLAYABLE；有游戏帧；候选当前部署').encode()
    files = lambda: {n: (API / n).read_bytes() for n in g25.OUTPUTS}
    r = data['rows'][62]
    cases = [
        ('history object changed', lambda: check(mut(lambda d: d['rows'][3].__setitem__('status', 'changed')), source_root, False), 'original58 objects changed'),
        ('G28 row changed', lambda: check(mut(lambda d: d['rows'][61].__setitem__('status', 'GAME_STARTED；有游戏帧')), source_root, False), 'game success'),
        ('false success in table', lambda: guard('status', 'GAME_PLAYABLE；已部署'), 'game success'),
        ('HTML-only false success', lambda: g25.rendered_equal(data, source_root, dict(files(), **{'index.html': forged_html()})), 'index.html differs'),
        ('CSV-only edit', lambda: g25.rendered_equal(data, source_root, dict(files(), **{'observations.csv': files()['observations.csv'] + b'x'})), 'observations.csv differs'),
        ('truncated to 62', lambda: check(mut(lambda d: d['rows'].pop()), source_root, False), 'exactly 63 rows'),
        ('64th row appended', lambda: check(mut(lambda d: d['rows'].append(dict(d['rows'][62], id='OBS-FUTURE'))), source_root, False), 'exactly 63 rows'),
        ('row63 edited', lambda: check(mut(lambda d: d['rows'][62].__setitem__('name', 'changed')), source_root, False), 'G33 observation changed'),
        ('evidence dropped', lambda: check(mut(lambda d: d['rows'][62].__setitem__('evidence', [])), source_root, False), 'evidence references dropped'),
        ('claimed frozen', lambda: guard('frozen', True), 'freeze'),
        ('claimed current deployment', lambda: guard('deployment', '候选为当前部署'), 'current deployment'),
        ('claimed playable', lambda: guard('apps', '原神可玩，有游戏帧'), 'playable'),
        ('remote archive claimed without evidence', lambda: guard('deployment', r['deployment'].replace('当时远端未验证；不声称已远端核验', '已远端SHA核验')), 'remote archive'),
        ('snapshot pin rewritten to a receipt', lambda: archive_snapshot(dict(snap, remote_receipts_in_g30_tree=[f'{L}/final/remote-archive.json']), public), 'archive snapshot pin drift'),
        ('landing list with a receipt', lambda: archive_snapshot(snap, public + [f'{L}/final/remote-archive.json']), 'pinned G30 landing lists a remote receipt'),
        ('full OS closure claimed', lambda: guard('limitations', r['limitations'].replace('不是完整Linux OS镜像或宿主动态库闭合', '已完成完整OS闭合')), 'OS closure'),
        ('rc124 as compile failure', lambda: guard('limitations', r['limitations'].replace('是环境失败不是编译失败', '是编译失败')), 'rc124'),
        ('__assert2 claimed', lambda: guard('method', r['method'].replace('不含__assert2', '含__assert2')), '__assert2'),
        ('missing reference', lambda: old.check_ref(source_root, dict(item, path=f'{L}/final/intentionally-missing.json')), 'missing/nonregular'),
        ('reference SHA drift', lambda: old.check_ref(source_root, dict(item, sha256='0' * 64)), 'SHA drift'),
    ]
    public = (source_root / f'{L}/final/landing-paths.txt').read_text().split()
    snap = old.read(HERE / 'input-pins.json')['archive_snapshot']
    later = later_receipt_root(source_root)
    try:
        old.require((later / f'{L}/final/remote-archive.json').is_file(), 'positive-case receipt not created')
        old.require(check(data, later, False) == count, 'a later genuine remote receipt falsified the historical observation')
    finally:
        shutil.rmtree(later)
    refusals = []
    for name, call, expected in cases:
        try: call()
        except ValueError as exc:
            old.require(expected in str(exc), f'unexpected refusal for {name}: {exc}')
            refusals.append({'case': name, 'refused': True, 'reason': str(exc)})
        else: raise ValueError(f'negative case accepted: {name}')
    print(json.dumps({'status': 'PASS', 'rows': len(data['rows']), 'original_rows_unchanged': 62, 'added_rows': 1,
        'exact_references': count, 'g30_public_paths_referenced': 56, 'html_csv_results_byte_equal_to_original_renderer': True,
        'historical315_unchanged': True, 'g15_g17_g25_g29_g31_prefix_checks_pass': True, 'negative_cases': refusals,
        'candidate_currently_deployed': False, 'public_api_freeze': False, 'game_evidence': False,
        'full_os_closure': False, 'archive_snapshot': 'G30 landing 8acf1ed61: local persistent, remote not verified at that time',
        'later_remote_receipt_keeps_observation_true': True,
        'device_calls': 0, 'rea_calls': 0, 'runtime_builds': 0}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
