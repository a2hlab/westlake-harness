#!/usr/bin/env python3
"""G31: append exactly one G28 observation to the 61-row prefix of master 782b588de8.

Snapshots the original 61-row observations.json and README as preimages (first run only), builds the
row from exact repository files at master 78ea979419 (SHA256 + bytes), and writes observations.json with
the original serialization (indent=2, ensure_ascii=False). It never edits the prior 61 objects or the
renderer, and runs no device, REA or build. Re-running is idempotent; the prefix must still match.
"""
import hashlib, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
API = ROOT / 'benchmark/2026-10-19-api-progress-update'
C = 'benchmark/2026-10-21-commercial-game'
W, T = f'{C}/native-route-window', f'{C}/runtime-loader-triage/g28-launch-addendum'
N, A = f'{C}/native-route-candidate', f'{C}/native-route-build-archive'

def ref(rel):
    b = (ROOT / rel).read_bytes()
    return {'path': rel, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}

ROW = {
 'id': 'OBS-20261021-G28-NATIVE-ROUTE-TRIAL',
 'kind': '原生命名空间路由候选实测（不是新增安卓公共API，不是公共API冻结）',
 'name': 'G28 原神精确native域路由候选实测：主库首终止错误推进到_ctype_@LIBC，游戏白屏后回桌面',
 'status': 'CANDIDATE_TRIAL_GAME_FAILED；无游戏帧；candidate_currently_deployed=false；已恢复基线',
 'method': 'G26离线候选（host ee5649f2…、ANL 640b3c87…）加G24加载器策略，经外环持锁按原U7 apply（rc0，active_verified）；Hello World对照截图已认；普通桌面图标点击原神一次；随后同一journal原rollback（rc0）恢复基线并解锁。',
 'platform': 'OH 5ea / arm64；boot a1d869b4-69a2-40a4-937e-4860f5b54239；parent 12781、child 14857（birth 1768375）、UID 20011077。只覆盖本次窗口，不外推其它版本或其它板。',
 'apps': 'com.miHoYo.Yuanshen：首图白屏、后图为桌面，child exit code 1；game_frames_observed=false，无首帧、无可玩结论。仅一个app，不满足2app冻结条件。',
 'limitations': '本轮主库实际首终止为libyuanshen.so重定位缺OBJECT _ctype_@LIBC（22:02:08.430，hilog L3259），随后Unity加载失败、UnityPlayer.nativeRestartActivityIndicator未绑定、child exit1（L3722）。更早的libMHYComboCrypto.so __assert2缺失（L3118/3119/3144/3145）之后仍继续执行，未证为终止原因。G24的__register_atfork报错在本轮为0条，只表示报错点推进，不证明atfork provider/GOT赢家、完整atfork语义或主库完整重定位成功。maps采样（22:02:06.658）早于本次失败，不能认定最终namespace可见性或provider赢家。下一簇为_ctype_（实际失败）及strtoll_l、strtoull_l（同一locale模块的静态导入，未称当前失败），待独立定源与归属。',
 'deployment': '当前设备为已恢复基线：apply rc0、rollback rc0，外环独立复核319个直接与319个父视图基线哈希、mount栈、Boat3私有库与控制图一致，power恢复SLEEP/30000/10000，测试child不在，318条窗口例外退回原registry；锁于22:09:19.404534释放，闭窗978.404534秒。闭窗时held检查未单独留原始回执，postclose-held.json为其后22:13:48的独立只读复查（rc1、空），不补造原unlock rc。候选不是当前部署；不冻结。G28原始窗口归档8844053f…（69799110 B）已远端SHA核验（22:22:56），其快照早于后续held复查与最终peer审查。addendum检查器原内环46项实跑PASS；主树缺私有dynsym输入，不能独立重跑全部私有检查。',
 'source': [ref(p) for p in (f'{N}/candidate.patch', f'{N}/source-pins.json',
            f'{N}/sources/candidate/anl/flutter_domain.inc', f'{N}/sources/candidate/anl/app_native_loader.c',
            f'{N}/sources/candidate/host/candidate-stock-host.c')],
 'build': [ref(p) for p in (f'{N}/build_host.py', f'{N}/build_anl.py', f'{N}/results.json',
           f'{A}/remote-archive.json', f'{A}/README.md',
           f'{W}/admission-01/README.md', f'{W}/admission-01/decisions.json', f'{W}/admission-01/native-exceptions.json',
           f'{W}/admission-01/preflight-receipt.json', f'{W}/admission-01/static-policy.json')],
 'evidence': [ref(p) for p in (f'{W}/closed/README.md', f'{W}/closed/results.json', f'{W}/closed/remote-archive.json',
              f'{W}/closed/independent-review.json', f'{W}/closed/postclose-held.json', f'{W}/closed/exception-retirement.json',
              f'{W}/closed/original-evidence-index.json', f'{W}/closed/facts.txt', f'{W}/closed/power-after.txt',
              f'{W}/closed/candidate-control.jpeg', f'{W}/closed/game-first.jpeg', f'{W}/closed/game-later.jpeg',
              f'{W}/closed/restored-control.jpeg',
              f'{T}/README.md', f'{T}/ACK.md', f'{T}/results.json', f'{T}/excerpts.txt', f'{T}/maps-excerpts.json',
              f'{T}/provider-matrix.json', f'{T}/next-candidates.json', f'{T}/source-excerpts.json', f'{T}/validation.json',
              f'{T}/manifest.json', f'{T}/input-sha.json', f'{T}/check.py', f'{T}/SHA256SUMS')],
 'frozen': False,
}

def main():
    obs = API / 'observations.json'
    snap = HERE / 'original-61.json'
    if not snap.exists():
        snap.write_bytes(obs.read_bytes())
        (HERE / 'README.before.md').write_bytes((API / 'README.md').read_bytes())
    base = json.loads(snap.read_text())
    assert len(base['rows']) == 61 and base['rows'][-1]['id'] == 'OBS-20261021-G26-NATIVE-ROUTE-CANDIDATE'
    cur = json.loads(obs.read_text())
    assert cur['rows'][:61] == base['rows'], 'original61 objects changed'
    assert ROW['id'] not in [r['id'] for r in base['rows']]
    out = dict(base); out['rows'] = base['rows'] + [ROW]
    obs.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    (HERE / 'added-row.json').write_text(json.dumps(ROW, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'rows': len(out['rows']), 'refs': sum(len(ROW[g]) for g in ('source', 'build', 'evidence'))}))

if __name__ == '__main__':
    main()
