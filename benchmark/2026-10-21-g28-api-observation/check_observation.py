#!/usr/bin/env python3
"""Check G31's one-row append (62nd observation, G28 native-route trial); no device, REA, build or cited-code run.

Reuses the G29 checker (G15 58 / G17 59 / G25 60 / G29 61 strict prefixes, original-renderer byte equality of
index.html/observations.csv/results.json, G24 and G26 failure semantics) and adds: the 62-row prefix, row 62
equals added-row.json (G33: the 62-row prefix is strict and later rows may follow), independent semantic guards (game failed, baseline restored, candidate not deployed,
not frozen, atfork/maps/held-receipt boundaries), cross-checks against the G28 receipts, and negative cases.
"""
import argparse, copy, importlib.util, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
API = ROOT / 'benchmark/2026-10-19-api-progress-update'
spec = importlib.util.spec_from_file_location('g29_checker', ROOT / 'benchmark/2026-10-21-g26-api-observation/check_observation.py')
g29 = importlib.util.module_from_spec(spec); spec.loader.exec_module(g29)
g25, old = g29.g25, g29.old
C = 'benchmark/2026-10-21-commercial-game'
W, T = f'{C}/native-route-window', f'{C}/runtime-loader-triage/g28-launch-addendum'
ALLOWED = (f'{W}/closed/', f'{W}/admission-01/', f'{T}/', f'{C}/native-route-candidate/', f'{C}/native-route-build-archive/')

def semantic(row):
    old.require(row['frozen'] is False, 'public API freeze claimed')
    old.require(row['status'].startswith('CANDIDATE_TRIAL_GAME_FAILED') and '无游戏帧' in row['status'] and '已恢复基线' in row['status']
                and 'candidate_currently_deployed=false' in row['status'], 'game success or recovery state claimed')
    old.require('game_frames_observed=false' in row['apps'] and 'exit code 1' in row['apps'] and '不满足2app冻结条件' in row['apps'], 'game frame / playable / two-app claim')
    lim = row['limitations']
    old.require('_ctype_@LIBC' in lim and '未证为终止原因' in lim, 'first terminal failure misattributed')
    old.require('只表示报错点推进，不证明atfork' in lim, 'atfork semantics or provider winner claimed')
    old.require('不能认定最终namespace可见性' in lim, 'early maps used as final namespace visibility')
    dep = row['deployment']
    old.require(dep.startswith('当前设备为已恢复基线') and '候选不是当前部署' in dep and '不冻结' in dep, 'candidate written as current deployment')
    old.require('不补造原unlock rc' in dep and '独立只读复查' in dep, 'later held recheck written as original unlock receipt')
    old.require('不能独立重跑全部私有检查' in dep, 'main written as able to rerun private checks')
    old.require('快照早于后续held复查与最终peer审查' in dep, 'archive scope widened past its snapshot')

def check(data, source_root, rendered=True):
    count = g29.check(data, source_root, rendered)
    base = old.read(HERE / 'original-61.json')
    old.require(len(base['rows']) == 61 and data['rows'][:61] == base['rows'], 'original61 objects changed')
    old.require(len(data['rows']) >= 62, 'G31 requires the 62-row prefix')
    row = data['rows'][61]
    semantic(row)
    for g in ('source', 'build', 'evidence'):
        old.require(len(row[g]) > 0, f'G31 {g} references dropped')
    old.require(row == old.read(HERE / 'added-row.json'), 'G31 observation changed')
    for g in ('source', 'build', 'evidence'):
        for item in row[g]:
            old.require(item['path'].startswith(ALLOWED), f"unaccepted evidence source: {item['path']}")
            old.check_ref(source_root, item); count += 1
    closed = old.read(source_root / f'{W}/closed/results.json')
    old.require(closed['status'] == 'CLOSED_RESTORED_GAME_FAILED' and closed['apply_rc'] == 0 and closed['rollback_rc'] == 0
                and closed['game_frames_observed'] is False, 'apply/rollback/game receipt drift')
    old.require(closed['direct_baseline_hashes'] == 319 and closed['parent_baseline_hashes'] == 319 and closed['mounts_equal'] is True
                and closed['boat3_equal'] is True and closed['control_visual_verified'] is True and closed['test_children_absent'] is True
                and closed['lock_released'] is True and closed['elapsed_seconds'] == 978.404534 and closed['exceptions_retired'] == 318, 'restoration receipt drift')
    tri = old.read(source_root / f'{T}/results.json')
    blk = tri['actual_first_load_blocker_in_terminal_chain']
    old.require(tri['pid'] == 14857 and blk['symbol'] == '_ctype_' and blk['version'] == 'LIBC' and blk['line'] == 3259
                and tri['terminal']['exit_code'] == 1 and tri['atfork_comparison']['g28_pid_log_count'] == 0
                and tri['maps']['winner'] == 'UNKNOWN' and tri['maps']['before_library_failure'] is True and tri['runtime_pass'] is False, 'launch analysis receipt drift')
    held = old.read(source_root / f'{W}/closed/postclose-held.json')
    old.require(held['rc'] == 1 and held['started_at'].startswith('2026-10-21T22:13:48'), 'later held recheck drift')
    arch = old.read(source_root / f'{W}/closed/remote-archive.json')
    old.require(arch['status'] == 'remote_sha256_verified' and arch['bytes'] == 69799110
                and arch['archive_sha256'] == '8844053ffd021606fac21e58b73543fea753a7a1b523927baa777a15c76aabd2', 'execution archive not remote-verified')
    old.require(old.read(source_root / f'{C}/native-route-build-archive/remote-archive.json')['status'] == 'remote_sha256_verified', 'build archive not remote-verified')
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
    item = data['rows'][61]['evidence'][0]
    def guard(k, v):  # tamper row 62 (and, by implication, added-row.json) so only the semantic guard can refuse
        r = copy.deepcopy(data['rows'][61]); r[k] = v; semantic(r)
    def forged_html():  # JSON, article count and IDs unchanged; only row 62's rendered status text forged
        html = (API / 'index.html').read_text(); real = data['rows'][61]['status']
        old.require(html.count(real) == 1, 'row62 status not uniquely rendered')
        return html.replace(real, 'GAME_PLAYABLE；有游戏帧；候选当前部署').encode()
    files = lambda: {n: (API / n).read_bytes() for n in g25.OUTPUTS}
    lim, dep = data['rows'][61]['limitations'], data['rows'][61]['deployment']
    cases = [
        ('history object changed', lambda: check(mut(lambda d: d['rows'][3].__setitem__('status', 'changed')), source_root, False), 'original58 objects changed'),
        ('G26 row changed', lambda: check(mut(lambda d: d['rows'][60].__setitem__('frozen', True)), source_root, False), 'freeze'),
        ('false success in table', lambda: guard('status', 'GAME_STARTED；有游戏帧'), 'game success'),
        ('HTML-only fake game frame', lambda: g25.rendered_equal(data, source_root, dict(files(), **{'index.html': forged_html()})), 'index.html differs'),
        ('CSV-only edit', lambda: g25.rendered_equal(data, source_root, dict(files(), **{'observations.csv': files()['observations.csv'] + b'x'})), 'observations.csv differs'),
        ('rows truncated below 62', lambda: check(mut(lambda d: d['rows'].__delitem__(slice(61, None))), source_root, False), '62-row prefix'),
        ('appended row with unverified missing reference', lambda: g25.rendered_equal(mut(lambda d: d['rows'].append(dict(d['rows'][61], id='OBS-FUTURE',
            evidence=[dict(item, path=f'{W}/closed/intentionally-missing.json')]))), source_root, {}), 'renderer refused'),
        ('row62 edited', lambda: check(mut(lambda d: d['rows'][61].__setitem__('name', 'changed')), source_root, False), 'G31 observation changed'),
        ('evidence dropped', lambda: check(mut(lambda d: d['rows'][61].__setitem__('evidence', [])), source_root, False), 'evidence references dropped'),
        ('claimed playable', lambda: guard('apps', '原神可玩，有游戏帧'), 'playable'),
        ('claimed frozen', lambda: guard('frozen', True), 'freeze'),
        ('claimed current deployment', lambda: guard('deployment', '候选为当前部署'), 'current deployment'),
        ('atfork semantics claimed', lambda: guard('limitations', lim.replace('只表示报错点推进，不证明atfork', 'atfork实现已证')), 'atfork semantics'),
        ('early maps as final visibility', lambda: guard('limitations', lim.replace('不能认定最终namespace可见性', '已认定最终namespace可见性')), 'early maps'),
        ('fabricated unlock receipt', lambda: guard('deployment', dep.replace('不补造原unlock rc', '原unlock rc0')), 'original unlock receipt'),
        ('main runs all private checks', lambda: guard('deployment', dep.replace('不能独立重跑全部私有检查', '可独立重跑全部私有检查')), 'private checks'),
        ('missing reference', lambda: old.check_ref(source_root, dict(item, path=f'{W}/closed/intentionally-missing.json')), 'missing/nonregular'),
        ('reference SHA drift', lambda: old.check_ref(source_root, dict(item, sha256='0' * 64)), 'SHA drift'),
    ]
    later = mut(lambda d: d['rows'].append(dict(d['rows'][61], id='OBS-FUTURE')))
    old.require(check(later, source_root, False) == count, 'G31 allows a later append')
    refusals = []
    for name, call, expected in cases:
        try: call()
        except ValueError as exc:
            old.require(expected in str(exc), f'unexpected refusal for {name}: {exc}')
            refusals.append({'case': name, 'refused': True, 'reason': str(exc)})
        else: raise ValueError(f'negative case accepted: {name}')
    print(json.dumps({'status': 'PASS', 'rows': len(data['rows']), 'original_rows_unchanged': 61, 'added_rows': 1,
        'exact_references': count, 'html_csv_results_byte_equal_to_original_renderer': True, 'historical315_unchanged': True,
        'g15_g17_g25_g29_prefix_checks_pass': True, 'negative_cases': refusals, 'current_deployment': 'restored baseline',
        'candidate_currently_deployed': False, 'game_frames_observed': False, 'public_api_freeze': False,
        'execution_archive_remote_sha256_verified': True, 'private_addendum_checks_rerun_from_main': False,
        'device_calls': 0, 'rea_calls': 0, 'runtime_builds': 0}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
