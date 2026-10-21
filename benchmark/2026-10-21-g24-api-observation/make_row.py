#!/usr/bin/env python3
"""G25: append exactly one G24 observation to the 59-row prefix of master b2d14677a6.

Snapshots the original 59-row observations.json and README as preimages (first run only), builds the
row from exact repository files (SHA256 + bytes), and writes observations.json with the original
serialization (indent=2, ensure_ascii=False). It never edits the prior 59 objects or the renderer, and
runs no device, REA or build. Re-running is idempotent; the prefix must still match the snapshot.
"""
import hashlib, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
API = ROOT / 'benchmark/2026-10-19-api-progress-update'
C = 'benchmark/2026-10-21-commercial-game'
L, W = f'{C}/gles-loader-candidate', f'{C}/gles-window02'

def ref(rel):
    b = (ROOT / rel).read_bytes()
    return {'path': rel, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}

ROW = {
 'id': 'OBS-20261021-G24-GLES-LOADER-TRIAL',
 'kind': '原生加载器候选实测（不是新增安卓公共API，不是公共API冻结）',
 'name': 'G24 libGLESv2共享名候选实测：依赖错误推进到__register_atfork，游戏白屏后回桌面',
 'status': 'CANDIDATE_TRIAL_GAME_FAILED；无游戏帧；已恢复基线',
 'method': 'G18离线构建的libnativeloader候选（878c7019…，相对基线b8be63d2…仅在共享名单新增libGLESv2.so）经外环持锁apply（rc0）后，普通桌面图标启动原神一次；随后原rollback（rc0）恢复基线并解锁。',
 'platform': 'OH 5ea / arm64；boot a1d869b4-69a2-40a4-937e-4860f5b54239；parent 29504、child 31523（birth 1251118）、UID 20011077。只覆盖本次窗口，不外推其它版本或其它板。',
 'apps': 'com.miHoYo.Yuanshen：白屏后回桌面，child exit code 1；game_frames_observed=false，无首帧、无可玩结论。仅一个app，不满足2app冻结条件。',
 'limitations': '本次完整启动至退出的日志中，原libyuanshen.so依赖libGLESv2.so的缺库错误未再出现，libyuanshen.so改为在重定位阶段缺__register_atfork；这只是有界的加载器推进，不等于GLES功能完成或游戏可用。较早libMHYComboCrypto.so的__errno缺失仍在（基线已有）；libGLESv3.so在ndk/default不可访问及OpenGLWrapper错误仍在；逃出main的仍为UnityPlayer.nativeRestartActivityIndicator UnsatisfiedLinkError。各错误间因果未证实。游戏child的maps未采到，不推断实际加载器inode或库实例。',
 'deployment': '当前设备为已恢复基线：apply rc0、rollback rc0，319个基线目标全部一致，mount栈与Boat3一致，power恢复（30000/10000）且boot未变，锁于2026-10-21T20:43:19+08:00释放。候选不是当前部署；不新增公共API冻结。构建原始归档9b3f27bd…与G24执行原始归档57b760d3…均已远端SHA核验，大日志不入git。',
 'source': [ref(p) for p in (f'{L}/shared-gles.patch', f'{L}/source-pins.json',
            f'{L}/sources/baseline/src/native_loader.cpp', f'{L}/sources/candidate/src/native_loader.cpp',
            f'{L}/sources/candidate/policy/native_bridge_policy.v1.json')],
 'build': [ref(p) for p in (f'{L}/build_candidate.py', f'{L}/upstream/build.py', f'{L}/upstream/source-identity.json',
           f'{L}/build-01-receipt.json', f'{L}/raw-index.json', f'{L}/archive-receipt.json', f'{L}/outer-archive/receipt.json',
           f'{L}/README.md', f'{L}/results.json')],
 'evidence': [ref(p) for p in (f'{W}/closed/README.md', f'{W}/closed/results.json', f'{W}/closed/window-closed.json',
              f'{W}/closed/validation.json', f'{W}/closed/remote-archive.json', f'{W}/closed/power.txt',
              f'{W}/closed/game-first.jpeg', f'{W}/closed/game-later.jpeg', f'{W}/closed/restored-control.jpeg',
              f'{W}/launch-review-01/README.md', f'{W}/launch-review-01/results.json', f'{W}/launch-review-01/facts.txt',
              f'{W}/launch-review-01/log-excerpts.json', f'{W}/launch-review-01/validation.json',
              f'{W}/launch-review-01/manifest.json', f'{W}/launch-review-01/raw-index.json')],
 'frozen': False,
}

def main():
    obs = API / 'observations.json'
    snap = HERE / 'original-59.json'
    if not snap.exists():
        snap.write_bytes(obs.read_bytes())
        (HERE / 'README.before.md').write_bytes((API / 'README.md').read_bytes())
    base = json.loads(snap.read_text())
    assert len(base['rows']) == 59 and base['rows'][-1]['id'] == 'OBS-20261021-G17-NORMAL-UI-LAUNCH'
    cur = json.loads(obs.read_text())
    assert cur['rows'][:59] == base['rows'], 'original59 objects changed'
    assert ROW['id'] not in [r['id'] for r in base['rows']]
    out = dict(base); out['rows'] = base['rows'] + [ROW]
    obs.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    (HERE / 'added-row.json').write_text(json.dumps(ROW, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'rows': len(out['rows']), 'refs': sum(len(ROW[g]) for g in ('source', 'build', 'evidence'))}))

if __name__ == '__main__':
    main()
