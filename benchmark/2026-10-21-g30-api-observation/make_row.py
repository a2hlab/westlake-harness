#!/usr/bin/env python3
"""G33: append exactly one G30 observation to the 62-row prefix of master e4cd7d753.

Snapshots the original 62-row observations.json and README as preimages (first run only), builds the
row from the 56 public G30 paths fixed at master 8acf1ed61 (SHA256 + bytes), and writes observations.json
with the original serialization (indent=2, ensure_ascii=False). It never edits the prior 62 objects or the
renderer, and runs no device, REA or build. Re-running is idempotent; the prefix must still match.
"""
import hashlib, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
API = ROOT / 'benchmark/2026-10-19-api-progress-update'
L = 'benchmark/2026-10-21-commercial-game/locale-abi-candidate'
RUST = 'tools/spec-checks/tests/commercial_game_locale_abi_candidate.rs'

def ref(rel):
    b = (ROOT / rel).read_bytes()
    return {'path': rel, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}

PUBLIC = (ROOT / f'{L}/final/landing-paths.txt').read_text().split()
SOURCE = ('/sources/', '/candidate.patch', '/candidate-source-pins.json', '/source-index.json', '/source-excerpts.json', '/baseline-input-audit.json')
BUILD = ('/build_baseline.py', '/build_candidate.py', '/build-checkpoint-01/', '/final/baseline-receipt.json', '/final/candidate01-receipt.json',
         '/final/candidate02-receipt.json', '/final/candidate02-bookends.json', '/final/input-closure.json', '/final/raw-index.json', '/final/manifest.json')
pick = lambda keys: [p for p in PUBLIC if any(k in p for k in keys)]

ROW = {
 'id': 'OBS-20261021-G30-LOCALE-ABI-CANDIDATE',
 'kind': 'locale ABI离线兼容候选（公共兼容层源码/构建观察；不是游戏修改，不是公共API冻结）',
 'name': 'G30 原神_ctype_簇locale ABI候选：在已有native ABI库d205上新增3个LIBC导出，离线两次构建一致且未部署',
 'status': 'OFFLINE_CANDIDATE_VERIFIED_NOT_DEPLOYED；candidate_currently_deployed=false；runtime_namespace_binding UNKNOWN；无游戏运行证据',
 'method': '在既有libwestlake_native_abi.so（基线d2053066…，39520 B，原两对象重编后精确复现）上追加一个locale对象：bionic_locale_compat.c与本地历史模块逐字相同（21e52d1e…），version script仅新增LIBC下_ctype_（8字节OBJECT指针，指向257项分类表）与strtoll_l/strtoull_l（转发strtoll/strtoull并忽略locale）；不含__assert2，不改G26 host/ANL、namespace、selector、运行时/音频发布与游戏。候选4296f805…（41984 B）两次完整构建SHA相同，原两对象逐字相同；构建由外环在VM交接后执行。',
 'platform': '离线构建与宿主测试，无设备。真实生产locale TU仅为避免与宿主libc冲突改名，在Darwin上跑通257项分类与90个有/无符号整数用例；原native生产TU带宿主依赖替身（dlsym/pthread_atfork注入、__errno_location）对基线与候选均通过；9个ABI守卫反例；独立ELF检查：44个原动态符号tuple保留、26个原定义导出不变并仅增3个、新增导入仅strtoll/strtoull、NEEDED仍libc.so、构造/析构序列与.init/.fini字节不变、无TEXTREL。宿主测试不替代OH运行证据，OH回调未在本任务执行。',
 'apps': '目标为com.miHoYo.Yuanshen（G28实测主库首终止为_ctype_@LIBC，仍白屏后回桌面exit1）。G30未上板：实际重定位赢家、后续阻塞、游戏帧与可玩均UNKNOWN；预计移走首个致命点的key为genshin，属待运行验证的预测。仅离线一例，不满足2app冻结条件。',
 'limitations': '候选02在同一配方前后对55个输入逐一哈希且完全一致，input-closure指向全部55个持久副本；这不是完整Linux OS镜像或宿主动态库闭合（配置的tc/runtime目录不存在），也不是OH实际语义验证。locale源上游归属仅为源码注释，未独立核对AOSP字节。候选策略拒绝无版本导出不代表OH拒绝所有无版本provider。历史保留：内环VM入口rc124超时且无编译证据，是环境失败不是编译失败；host01因假设无转换时errno不变而失败（Darwin底层设EINVAL），host02直接比对转发后通过，生产源未改。',
 'deployment': 'candidate_currently_deployed=false：本条不部署、不授权部署、不冻结，也不称原神可玩。归档状态为G30固定主线8acf1ed61交件时的观察快照：原始双流、rc与构建日志在本地持久存储（raw-index.json所列$HOME/.local/share/westlake与.private路径），该交件56个公开路径中无远端回执，故当时远端未验证；不声称已远端核验。日后补齐的远端回执不改变本条历史快照，应另以新观察记录。',
 'source': [ref(p) for p in pick(SOURCE)],
 'build': [ref(p) for p in pick(BUILD)],
 'evidence': [ref(p) for p in PUBLIC if not any(k in p for k in SOURCE + BUILD)],
 'frozen': False,
}

def main():
    assert len(PUBLIC) == 56 and len(set(PUBLIC)) == 56 and all(p.startswith(L + '/') or p == RUST for p in PUBLIC)
    assert sum(len(ROW[g]) for g in ('source', 'build', 'evidence')) == 56
    obs = API / 'observations.json'
    snap = HERE / 'original-62.json'
    if not snap.exists():
        snap.write_bytes(obs.read_bytes())
        (HERE / 'README.before.md').write_bytes((API / 'README.md').read_bytes())
    base = json.loads(snap.read_text())
    assert len(base['rows']) == 62 and base['rows'][-1]['id'] == 'OBS-20261021-G28-NATIVE-ROUTE-TRIAL'
    cur = json.loads(obs.read_text())
    assert cur['rows'][:62] == base['rows'], 'original62 objects changed'
    assert ROW['id'] not in [r['id'] for r in base['rows']]
    out = dict(base); out['rows'] = base['rows'] + [ROW]
    obs.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    (HERE / 'added-row.json').write_text(json.dumps(ROW, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'rows': len(out['rows']), 'refs': {g: len(ROW[g]) for g in ('source', 'build', 'evidence')}}))

if __name__ == '__main__':
    main()
