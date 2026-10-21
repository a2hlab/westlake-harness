#!/usr/bin/env python3
"""Check G35's one-row append (64th observation, G34 locale ABI trial); no device, REA, build or cited-code run.

Reuses the G33 checker (G15 58 / G17 59 / G25 60 / G29 61 / G31 62 / G33 63 strict prefixes, original-renderer
byte equality of index.html/observations.csv/results.json, G24/G26/G28/G30 semantics) and adds: exactly 64
rows, row 64 equals added-row.json, references are exactly the set derived from the G34 packages' own landing
lists, admission files, archive receipts and the G30 link (each SHA verified), independent semantic guards
(signal11, no game frame, baseline restored, not deployed, not frozen, fault PC/stack/cause unknown, the
force-stop and Dfx body errors, the closed package's pending archive kept as a historical snapshot),
cross-checks against the G34 receipts, positive and negative cases.
"""
import argparse, copy, importlib.util, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
API = ROOT / 'benchmark/2026-10-19-api-progress-update'
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
g33 = load('g33_checker', ROOT / 'benchmark/2026-10-21-g30-api-observation/check_observation.py')
mk = load('g35_make_row', HERE / 'make_row.py')
g25, old = g33.g25, g33.old
W, T, L = mk.W, mk.T, mk.L
ALLOWED = tuple(f'{p}/' for p in (f'{W}/closed', f'{W}/admission-01', f'{W}/execution-archive', f'{W}/postclose-observations',
                                  f'{W}/outer-review', f'{T}/g34-launch-addendum', f'{T}/g34-static-prediction', L))
CANDIDATE = '4296f8052b6ccc130df83366717903695eba38fcde19c462ee64521414696f0b'

def semantic(row):
    old.require(row['frozen'] is False, 'public API freeze claimed')
    old.require(row['status'].startswith('CANDIDATE_TRIAL_GAME_FAILED_SIGNAL11') and '无游戏帧' in row['status']
                and 'candidate_currently_deployed=false' in row['status'] and '恢复基线已核' in row['status'], 'game success or recovery state claimed')
    old.require('game_frames_observed=false' in row['apps'] and 'signal11' in row['apps'] and '无首帧、无可玩结论' in row['apps']
                and '不满足2app冻结条件' in row['apps'], 'game frame / playable / two-app claim')
    lim = row['limitations']
    old.require('仅表示本次加载推进，不是该API普遍通过' in lim, 'locale error absence written as general API pass')
    old.require('fault PC、faulting TID、栈、故障根因与动态provider winner均UNKNOWN' in lim and '不作GLES/libc告警归因' in lim, 'root cause or PC/stack claimed known')
    old.require('外层rc0但正文CODE:-31，不是成功的空结果' in lim and '均不能证明不存在系统崩溃记录' in lim, 'Dfx body error read as no crash record')
    dep = row['deployment']
    old.require(dep.startswith('当前设备为已恢复基线') and '候选不是当前部署' in dep and '不冻结' in dep, 'candidate written as current deployment')
    old.require('不计为成功停止' in dep and '其后完整进程表另行显示' in dep, 'outer rc0 force-stop counted as a successful stop')
    old.require('318条窗口临时例外已撤销' in dep, 'exception retirement missing')
    old.require('closed包写的远端归档待核是其打包时快照，原样保留' in dep, 'historical pending archive statement rewritten')
    old.require('首次UI helper因远端布局目录缺失在点击前失败' in row['method'] and '点击原神一次' in row['method'], 'UI attempt history rewritten')

def ref_set(row, expected):
    paths = [i['path'] for g in ('source', 'build', 'evidence') for i in row[g]]
    old.require(len(paths) == len(set(paths)) and sorted(paths) == sorted(expected), 'references differ from the G34 landing-derived set')

def check(data, source_root, rendered=True):
    count = g33.check(data, source_root, rendered)
    base = old.read(HERE / 'original-63.json')
    old.require(len(base['rows']) == 63 and data['rows'][:63] == base['rows'], 'original63 objects changed')
    old.require(len(data['rows']) == 64, 'G35 requires exactly 64 rows')
    row = data['rows'][63]
    semantic(row)
    for g in ('source', 'build', 'evidence'):
        old.require(len(row[g]) > 0, f'G35 {g} references dropped')
    old.require(row == old.read(HERE / 'added-row.json'), 'G35 observation changed')
    want = mk.build_row(source_root)
    ref_set(row, [i['path'] for g in ('source', 'build', 'evidence') for i in want[g]])
    for g in ('source', 'build', 'evidence'):
        for item in row[g]:
            old.require(item['path'].startswith(ALLOWED), f"unaccepted evidence source: {item['path']}")
            old.check_ref(source_root, item); count += 1
    rd = lambda rel: old.read(source_root / rel)
    c = rd(f'{W}/closed/results.json'); ind = c['independent_offline_restore_checks']; game = c['game']
    old.require(c['status'] == 'CLOSED_RESTORED_GAME_FAILED' and c['apply']['rc'] == 0 and c['apply']['status'] == 'active_verified' and c['apply']['operations'] == 36
                and c['rollback']['rc'] == 0 and c['rollback']['status'] == 'rolled_back' and c['rollback']['operations'] == 36, 'apply/rollback receipt drift')
    old.require(ind['direct_baseline_hashes_equal'] == 319 and ind['parent_baseline_hashes_equal'] == 319 and ind['original_mount_stack_equal'] is True
                and ind['mount_targets_compared'] == 61 and ind['boat3_original_stdout_bytes_equal'] is True and ind['unlock_rc'] == 0
                and ind['power'] == 'SLEEP/30000/10000' and ind['test_uids_absent_from_final_ps'] == [20011065, 20011077], 'restoration receipt drift')
    old.require(game['frames_observed'] is False and game['pid'] == 29761 and game['fault_pc'] == 'UNKNOWN' and game['fault_stack'] == 'UNKNOWN'
                and game['cause'] == 'UNKNOWN' and 'signal11' in game['terminal'] and 'CODE:-31' in game['dfx_query'], 'game receipt drift')
    old.require(c['archive'].startswith('REMOTE_RECEIPT_PENDING') and rd(f'{W}/closed/remote-archive-pending.json')['status'] == 'PENDING_REMOTE_RECEIPT'
                and c['postclose_dfx']['target_time_covered'] is False, 'closed historical snapshot drift')
    old.require(rd(f'{W}/closed/admission-retirement.json')['exceptions_retired'] == 318 and rd(f'{W}/closed/admission-retirement.json')['original_admission_modified'] is False, 'retirement receipt drift')
    old.require(rd(f'{W}/closed/receipts/game-ui/failure.json')['game_clicked'] is False, 'first UI attempt drift')
    old.require(rd(f'{W}/outer-review/closure-force-stop-correction.json')['status'].startswith('CORRECTION_APPEND_ONLY'), 'force-stop correction drift')
    a = rd(f'{T}/g34-launch-addendum/results.json')['terminal']
    old.require(a['signal'] == 11 and a['line'] == 3791 and a['fault_pc'] == 'UNKNOWN', 'launch addendum drift')
    s = rd(f'{T}/g34-static-prediction/results.json')
    old.require(s['candidate_sha256'] == CANDIDATE and s['counts']['strong_evaluated'] == 433 and s['counts']['strong_without_named_provider_in_review_set'] == 0
                and s['new_fix_keys'] == [] and s['runtime_winner'] == 'UNKNOWN', 'static prediction drift')
    ex = rd(f'{W}/execution-archive/archive-receipt.json')
    old.require(ex['status'] == 'remote_sha256_verified' and ex['bytes'] == 69903553 and ex['archive_sha256'].startswith('d80d2025') and ex['game_frames_observed'] is False, 'execution archive not remote-verified')
    pc = rd(f'{W}/postclose-observations/remote-archive.json'); po = rd(f'{W}/postclose-observations/results.json')
    old.require(pc['status'] == 'remote_sha256_verified' and pc['bytes'] == 2925023 and pc['archive_sha256'].startswith('2441351e'), 'postclose archive not remote-verified')
    old.require(po['query_rc'] == 0 and po['target_time_in_output'] is True and po['fault_pc'] == 'UNKNOWN' and po['fault_stack'] == 'NOT_RECOVERED' and po['cause'] == 'UNKNOWN', 'postclose observation drift')
    vis = {i['path']: i['visual_verdict'] for i in rd(f'{W}/closed/images.json')}
    old.require('no game frame' in vis['images/game-white.jpeg'] and 'no game frame' in vis['images/game-desktop.jpeg'], 'image verdict drift')
    old.require(rd(f'{L}/final/results.json')['candidate_sha256'] == CANDIDATE, 'G30 candidate link drift')
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
    r = data['rows'][63]; item = r['evidence'][0]
    def guard(k, v):  # tamper row 64 (and, by implication, added-row.json) so only the semantic guard can refuse
        x = copy.deepcopy(r); x[k] = v; semantic(x)
    def swap(k, a, b):
        old.require(r[k].count(a) == 1, f'guard text not unique: {a}'); guard(k, r[k].replace(a, b))
    def forged(name, real):  # JSON unchanged; one output file alone claims success
        text = (API / name).read_text(); old.require(text.count(real) == 1, f'row64 status not uniquely rendered in {name}')
        return text.replace(real, 'GAME_PLAYABLE；有游戏帧；候选当前部署').encode()
    files = lambda: {n: (API / n).read_bytes() for n in g25.OUTPUTS}
    paths = [i['path'] for g in ('source', 'build', 'evidence') for i in r[g]]
    cases = [
        ('history object changed', lambda: check(mut(lambda d: d['rows'][3].__setitem__('status', 'changed')), source_root, False), 'original58 objects changed'),
        ('G30 row changed', lambda: check(mut(lambda d: d['rows'][62].__setitem__('frozen', True)), source_root, False), 'freeze'),
        ('truncated to 63', lambda: check(mut(lambda d: d['rows'].pop()), source_root, False), 'exactly 64 rows'),
        ('65th row appended', lambda: check(mut(lambda d: d['rows'].append(dict(d['rows'][63], id='OBS-FUTURE'))), source_root, False), 'exactly 64 rows'),
        ('row64 edited', lambda: check(mut(lambda d: d['rows'][63].__setitem__('name', 'changed')), source_root, False), 'G35 observation changed'),
        ('evidence dropped', lambda: check(mut(lambda d: d['rows'][63].__setitem__('evidence', [])), source_root, False), 'evidence references dropped'),
        ('landing path omitted', lambda: ref_set(dict(r, evidence=r['evidence'][1:]), paths), 'landing-derived set'),
        ('missing reference', lambda: old.check_ref(source_root, dict(item, path=f'{W}/closed/intentionally-missing.json')), 'missing/nonregular'),
        ('reference SHA drift', lambda: old.check_ref(source_root, dict(item, sha256='0' * 64)), 'SHA drift'),
        ('HTML-only false success', lambda: g25.rendered_equal(data, source_root, dict(files(), **{'index.html': forged('index.html', r['status'])})), 'index.html differs'),
        ('CSV-only false success', lambda: g25.rendered_equal(data, source_root, dict(files(), **{'observations.csv': forged('observations.csv', r['status'])})), 'observations.csv differs'),
        ('false success in table', lambda: guard('status', 'GAME_STARTED；有游戏帧'), 'game success'),
        ('claimed game frame from screenshot count', lambda: guard('apps', '截图2/2，有游戏帧'), 'game frame'),
        ('claimed current deployment', lambda: swap('deployment', '候选不是当前部署', '候选为当前部署'), 'current deployment'),
        ('claimed frozen', lambda: guard('frozen', True), 'freeze'),
        ('claimed root cause known', lambda: swap('limitations', 'fault PC、faulting TID、栈、故障根因与动态provider winner均UNKNOWN', '故障根因已知：GLES告警'), 'root cause'),
        ('locale absence as API pass', lambda: swap('limitations', '仅表示本次加载推进，不是该API普遍通过', 'locale API已普遍通过'), 'general API pass'),
        ('Dfx CODE-31 as empty result', lambda: swap('limitations', '外层rc0但正文CODE:-31，不是成功的空结果', 'rc0空结果，无崩溃记录'), 'Dfx body error'),
        ('force-stop rc0 as success', lambda: swap('deployment', '不计为成功停止', '已成功停止'), 'force-stop'),
        ('historical pending rewritten', lambda: swap('deployment', 'closed包写的远端归档待核是其打包时快照，原样保留', 'closed包的待核为错误'), 'historical pending'),
    ]
    refusals = []
    for name, call, expected in cases:
        try: call()
        except ValueError as exc:
            old.require(expected in str(exc), f'unexpected refusal for {name}: {exc}')
            refusals.append({'case': name, 'refused': True, 'reason': str(exc)})
        else: raise ValueError(f'negative case accepted: {name}')
    print(json.dumps({'status': 'PASS', 'rows': len(data['rows']), 'original_rows_unchanged': 63, 'added_rows': 1,
        'exact_references': count, 'g34_row_references': len(paths), 'html_csv_results_byte_equal_to_original_renderer': True,
        'historical315_unchanged': True, 'g15_g17_g25_g29_g31_g33_prefix_checks_pass': True, 'negative_cases': refusals,
        'game_frames_observed': False, 'terminal': 'signal11', 'fault_pc_stack_cause': 'UNKNOWN', 'current_deployment': 'restored baseline',
        'candidate_currently_deployed': False, 'public_api_freeze': False,
        'closed_pending_kept_as_historical_snapshot': True, 'execution_and_postclose_archives_remote_verified': True,
        'device_calls': 0, 'rea_calls': 0, 'runtime_builds': 0}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
