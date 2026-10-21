#!/usr/bin/env python3
"""G35: append exactly one G34 observation to the 63-row prefix of master 86b9fdb160.

Snapshots the original 63-row observations.json and README as preimages (first run only), builds the row
from exact repository files (SHA256 + bytes) and writes observations.json with the original serialization
(indent=2, ensure_ascii=False). References come from each G34 package's own landing list plus the
admission files, archive receipts and the G30 source/build link. --source-root selects where the input
bytes are read (default: this checkout); the final row must be built from the outer-landed commit. It never
edits the prior 63 objects or the renderer and runs no device, REA or build. Re-running is idempotent.
"""
import argparse, hashlib, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
API = ROOT / 'benchmark/2026-10-19-api-progress-update'
C = 'benchmark/2026-10-21-commercial-game'
W, T, L = f'{C}/locale-runtime-window', f'{C}/runtime-loader-triage', f'{C}/locale-abi-candidate'

ROW_TEXT = {
 'id': 'OBS-20261021-G34-LOCALE-TRIAL',
 'kind': 'locale ABI候选实测（不是新增安卓公共API，不是公共API冻结）',
 'name': 'G34 原神locale ABI候选实测：旧locale重定位错误未见，child signal11，白屏后回桌面',
 'status': 'CANDIDATE_TRIAL_GAME_FAILED_SIGNAL11；无游戏帧；candidate_currently_deployed=false；恢复基线已核',
 'method': 'G30离线候选libwestlake_native_abi.so（4296f805…，源码/配方见G30 locale-abi-candidate，未复制运行时实现）经外环持锁按原U7事务apply（active_verified，rc0，36项操作）；首次UI helper因远端布局目录缺失在点击前失败（本地rc0但远端marker1，未点击、无截图）；第二次普通桌面图标点击原神一次；随后原事务rollback（rolled_back，rc0，36项操作）恢复基线并实际解锁（unlock rc0）。',
 'platform': 'OH 5ea / arm64；boot a1d869b4-69a2-40a4-937e-4860f5b54239；parent 27555、child 29761（birth 2248607）、UID 20011077。只覆盖本次窗口，不外推其它版本或其它板。',
 'apps': 'com.miHoYo.Yuanshen：两张实际截图为白屏（含系统栏）后桌面，父进程于23:22:11.437报告child 29761 signal11（hilog L3791）；game_frames_observed=false，无首帧、无可玩结论。仅一个app，不满足2app冻结条件。',
 'limitations': '所给hilog中未见此前的locale重定位错误，仅表示本次加载推进，不是该API普遍通过。fault PC、faulting TID、栈、故障根因与动态provider winner均UNKNOWN，不作GLES/libc告警归因。窗口内Dfx查询把-x与-z组合，外层rc0但正文CODE:-31，不是成功的空结果；闭窗后单模式tag查询rc0且为空；25秒完整缓冲采样超时，只返回至23:17:38、未覆盖23:22目标时段；其后另一次完整缓冲查询（rc0）覆盖目标时段但PC与栈仍未恢复。以上均不能证明不存在系统崩溃记录。静态预测：主库433个强导入均有命名provider，新修复key为0，运行时winner UNKNOWN。',
 'deployment': '当前设备为已恢复基线：外环独立离线核对319个直接与319个父视图基线哈希、61个挂载目标栈、Boat3输出字节、前后控制图（Hello World自身UI）、power SLEEP/30000/10000与实际解锁；318条窗口临时例外已撤销、registry恢复原SHA，admission为闭窗后撤销声明、原签名未改。清理：两条最终aa force-stop正文报10106401（外层rc0、marker0），不计为成功停止；其后完整进程表另行显示测试UID 20011065/20011077均已不在；原kill shell未复核stat-birth。候选不是当前部署；不冻结。closed包写的远端归档待核是其打包时快照，原样保留；其后执行归档d80d2025…（69903553 B）与闭窗后观察归档2441351e…（2925023 B）已远端SHA核验，后者覆盖前者快照之后的诊断。',
 'frozen': False,
}

def landing(root, rel):
    return (root / rel / 'landing-paths.txt').read_text().split()

def build_row(root):
    def ref(rel):
        b = (root / rel).read_bytes()
        return {'path': rel, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}
    admission = sorted(str(p.relative_to(root)) for p in (root / W / 'admission-01').iterdir() if p.is_file())
    source = [f'{L}/candidate.patch', f'{L}/candidate-source-pins.json', f'{L}/sources/candidate/bionic_locale_compat.c', f'{L}/sources/candidate/native_abi.map']
    build = ([f'{L}/build_candidate.py', f'{L}/final/results.json', f'{L}/final/candidate02-receipt.json', f'{L}/final/remote-archive.json']
             + admission + landing(root, f'{T}/g34-static-prediction'))
    evidence = (landing(root, f'{W}/closed') + landing(root, f'{T}/g34-launch-addendum')
                + [f'{W}/execution-archive/{n}' for n in ('README.md', 'archive-receipt.json', 'membership-addendum.json')]
                + [f'{W}/postclose-observations/{n}' for n in ('README.md', 'results.json', 'raw-index.json', 'remote-archive.json')]
                + [f'{W}/outer-review/{n}' for n in ('closure-independent.json', 'closure-force-stop-correction.json', 'postclose-query02-addendum.json')])
    allp = source + build + evidence
    assert len(allp) == len(set(allp)), 'duplicate reference'
    return dict(ROW_TEXT, source=[ref(p) for p in source], build=[ref(p) for p in build], evidence=[ref(p) for p in evidence], frozen=False)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root', type=Path, default=ROOT)
    root = ap.parse_args().source_root.resolve()
    row = build_row(root)
    row = {k: row[k] for k in ('id', 'kind', 'name', 'status', 'method', 'platform', 'apps', 'limitations', 'deployment', 'source', 'build', 'evidence', 'frozen')}
    obs = API / 'observations.json'
    snap = HERE / 'original-63.json'
    if not snap.exists():
        snap.write_bytes(obs.read_bytes())
        (HERE / 'README.before.md').write_bytes((API / 'README.md').read_bytes())
    base = json.loads(snap.read_text())
    assert len(base['rows']) == 63 and base['rows'][-1]['id'] == 'OBS-20261021-G30-LOCALE-ABI-CANDIDATE'
    cur = json.loads(obs.read_text())
    assert cur['rows'][:63] == base['rows'], 'original63 objects changed'
    assert row['id'] not in [r['id'] for r in base['rows']]
    out = dict(base); out['rows'] = base['rows'] + [row]
    obs.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    (HERE / 'added-row.json').write_text(json.dumps(row, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'rows': len(out['rows']), 'refs': {g: len(row[g]) for g in ('source', 'build', 'evidence')}}))

if __name__ == '__main__':
    main()
