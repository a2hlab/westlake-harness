#!/usr/bin/env python3
"""G29: append exactly one G26 observation to the 60-row prefix of master 83d1a6e07.

Snapshots the original 60-row observations.json and README as preimages (first run only), builds the
row from exact repository files (SHA256 + bytes), and writes observations.json with the original
serialization (indent=2, ensure_ascii=False). It never edits the prior 60 objects or the renderer, and
runs no device, REA or build. Re-running is idempotent; the prefix must still match the snapshot.
"""
import hashlib, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
API = ROOT / 'benchmark/2026-10-19-api-progress-update'
C = 'benchmark/2026-10-21-commercial-game'
N, A = f'{C}/native-route-candidate', f'{C}/native-route-build-archive'

def ref(rel):
    b = (ROOT / rel).read_bytes()
    return {'path': rel, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}

ROW = {
 'id': 'OBS-20261021-G26-NATIVE-ROUTE-CANDIDATE',
 'kind': '原生命名空间路由离线候选（公共兼容层源码/构建观察；不是游戏修改，不是公共API冻结）',
 'name': 'G26 原神精确native域共享名单候选：host与ANL成员资格加mediandk，离线构建且未部署',
 'status': 'OFFLINE_CANDIDATES_BUILT_NOT_DEPLOYED；runtime_binding UNKNOWN；candidate_currently_deployed=false；无游戏运行证据',
 'method': '改动3个复制源文件：host与ANL对原神精确包名的成员资格（双selector），以及ANL原神native域app→bridge共享名单加入libmediandk.so；不新增叶库、owner、open-site、runtime/音频发布，不改游戏。两个精确基线复现：host 2a87118e…、ANL eebd62f2…；候选 host ee5649f2…（646840 B）、ANL 640b3c87…（60208 B）。8条compile/link全部rc0：host由inner在Mac执行（DevEco clang 6a5ec844… / ld.lld 489c6d66…），ANL由outer按冻结inner配方执行（clang-15 b107ce03… / ld.lld 8583bdc8…）。',
 'platform': '离线构建与宿主C回归，无设备。每版本实际生产函数回归：ANL 37个domain、host 50条路由，OH回调为替身（fake OH boundary callbacks），不是运行时provider绑定。host 216个动态符号与12个NEEDED、ANL 46个符号与1个NEEDED均不变，无TEXTREL。',
 'apps': '目标为com.miHoYo.Yuanshen（精确游戏3dd8a20d…导入__register_atfork、__FD_SET_chk、__FD_ISSET_chk，复用未改的私有ABI d2053066…三项导出覆盖，其atfork DSO卸载/注销限制仍在）。未上板：实际OH继承/provider赢家、完整加载、游戏帧、音视频与可玩均未验证。仅离线一例，不满足2app冻结条件。',
 'limitations': 'host复用原stock对象/归档与provider库，属增量可复现构建，不是全源清洁重编；超出所记输入的历史源码重建不声明。mediandk只经既有配置bridge的CREATE_INHERIT_DEFAULT共享名单进入，不在host直接owner列表，不是新的GLOBAL发布或已观测的运行时赢家。ANL零命名open-site不代表零open（经host回调）。已初始化域的跨应用复用不受这些测试支持。原G24失败（白屏回桌面exit1、无游戏帧）不因本条改变。',
 'deployment': 'candidate_currently_deployed=false：本条不部署、不授权部署、不冻结。G26 README所写原始日志local-only为交件时刻声明，原README与manifest不改；其后外环远端SHA核验G26原始构建归档e58740f5…（4547472 B），见native-route-build-archive。原stderr与二进制留私有/归档，不入git。',
 'source': [ref(p) for p in (f'{N}/candidate.patch', f'{N}/source-pins.json',
            f'{N}/sources/baseline/anl/flutter_domain.inc', f'{N}/sources/candidate/anl/flutter_domain.inc',
            f'{N}/sources/baseline/anl/app_native_loader.c', f'{N}/sources/candidate/anl/app_native_loader.c',
            f'{N}/sources/baseline/host/candidate-stock-host.c', f'{N}/sources/candidate/host/candidate-stock-host.c',
            f'{N}/evidence/owner-source/native_loader.cpp', f'{N}/evidence/owner-source/native_bridge_policy.h')],
 'build': [ref(p) for p in (f'{N}/build_host.py', f'{N}/build_anl.py', f'{N}/evidence/host-baseline-01.json', f'{N}/evidence/host-candidate-01.json',
           f'{N}/evidence/anl-production-01.json', f'{N}/evidence/raw-index.json', f'{N}/evidence/input-closure.json', f'{N}/evidence/u13-host-build-receipt.json',
           f'{A}/remote-archive.json', f'{A}/README.md')],
 'evidence': [ref(p) for p in (f'{N}/README.md', f'{N}/results.json', f'{N}/validation.json', f'{N}/manifest.json', f'{N}/SHA256SUMS',
              f'{N}/check_delivery.py', f'{N}/check_routes.py', f'{N}/tests/anl_probe.c', f'{N}/tests/host_main.c',
              f'{N}/evidence/host-abi-diff.json', f'{N}/evidence/anl-abi-diff.json', f'{N}/evidence/elf-facts.json',
              f'{N}/evidence/routes-02.json', f'{N}/evidence/peer-final-host-routes.json', f'{N}/evidence/open-sites.json')],
 'frozen': False,
}

def main():
    obs = API / 'observations.json'
    snap = HERE / 'original-60.json'
    if not snap.exists():
        snap.write_bytes(obs.read_bytes())
        (HERE / 'README.before.md').write_bytes((API / 'README.md').read_bytes())
    base = json.loads(snap.read_text())
    assert len(base['rows']) == 60 and base['rows'][-1]['id'] == 'OBS-20261021-G24-GLES-LOADER-TRIAL'
    cur = json.loads(obs.read_text())
    assert cur['rows'][:60] == base['rows'], 'original60 objects changed'
    assert ROW['id'] not in [r['id'] for r in base['rows']]
    out = dict(base); out['rows'] = base['rows'] + [ROW]
    obs.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    (HERE / 'added-row.json').write_text(json.dumps(ROW, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'rows': len(out['rows']), 'refs': sum(len(ROW[g]) for g in ('source', 'build', 'evidence'))}))

if __name__ == '__main__':
    main()
