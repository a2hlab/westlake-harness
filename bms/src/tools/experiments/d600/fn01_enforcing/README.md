# Fn01 A01–A04 Enforcing 真机证据采集器

这是实现者侧的安全环境证据工具，不是验收官，也不签发 `PASS`、`FAIL`、
`BLOCK` 或 `SPEC_GAP`。输出只可能表明证据包是否具备交给独立 agent 复核的
内部一致性，固定写入 `formal_verdict: NOT_ISSUED`。

## 契约审计结论

| Action | Enforcing 证据证明什么 | 仍必须由 Action 自己证明什么 |
|---|---|---|
| A01 | 安装请求发生在同一 Enforcing boot、同代产物与稳定进程身份下；相关 denial 不被静默忽略 | P0–P6、PublicationToken、唯一 active generation、typed negative、rollback/forward recovery |
| A02 | 查询请求的 caller/service 身份、文件标签和部署哈希可复核 | caller-visible 单代 snapshot、分页/visibility/typed failure、零 mutation |
| A03 | parser 请求确实运行于目标架构与 Enforcing 安全边界 | immutable bytes、ManifestFactsV1、字段 provenance、负向与重放 |
| A04 | Android 入口请求与同一 bridge/installer 代、boot、进程和日志窗口绑定 | flags/caller/user/generation-aware PackageInfo、字段矩阵、跨代 fail-closed |

因此，“`getenforce` 是 Enforcing 且没有看到 denial”不是任何 Action 的成功
oracle；反过来，Permissive、产物哈希错代、boot 改变、进程身份变化、陈旧日志
或请求回执无法关联时，这份真机证据必须拒绝。

## 两阶段采集

`begin` 只读采集请求前状态。它不再接受调用者自报的 `--expected-hash`；
所有远端产物路径和 SHA-256 只能从卡 1 的闭合 receipt chain 导入。

当前显式 adapter 接受：

- `bridge.fn01.generation-gate-report.v1`，且必须是 `PASS`、
  `target_deployment_generation_bound=true`；
- gate 引用的 `bridge.fn01.generation-build-receipt.v1`；
- gate 引用的 `bridge.fn01.device-generation-receipt.v1`；
- 一个覆盖上述三份 receipt 以及 bundle 内全部其他 payload 的
  `MANIFEST.sha256`。

三份 receipt 必须位于同一 manifest root 内，gate/build/device 之间的
Action、generation、serial、body digest、文件 SHA、artifact role/path/hash/size
必须完全闭合。absolute、`..`、symlink、重复 manifest 路径、未列文件和未知
schema 字段全部 fail-closed。由于卡 1 v1 尚未表达 `covered_actions`，adapter
暂时只接受与 `--action-id` 相同的 receipt Action；当前先用于 A04，不能把 A04
receipt 静默扩张为 A01–A03 coverage。

示例：

```bash
python3 src/tools/experiments/d600/fn01_enforcing/fn01_enforcing.py begin \
  --action-id Fn01.A04 \
  --serial 61b0657200000000000000000324012c \
  --out-dir /tmp/fn01-a04-enforcing-run \
  --provenance-receipt /path/to/card1-bundle/gate-report.json \
  --provenance-manifest /path/to/card1-bundle/MANIFEST.sha256
```

通过 adapter 后，整个卡 1 bundle 会被冻结到
`inputs/provenance/`。session 只允许 provenance receipt 中的唯一 serial，
同时锁定 original serial、boot ID、generation ID 和导入的 artifact hashes。

独立刺激程序随后生成一个 JSON request receipt。它必须包含：

```json
{
  "schema_version": "1.0",
  "action_id": "Fn01.A04",
  "request_id": "request-unique-id",
  "serial": "61b0657200000000000000000324012c",
  "boot_id": "uuid-from-device",
  "started_uptime_seconds": 123.0,
  "finished_uptime_seconds": 124.0,
  "artifact_hashes": {
    "/system/android/lib64/liboh_adapter_bridge.so": "64-lowercase-hex"
  },
  "contract_sha256": {
    "definition": "64-lowercase-hex",
    "verification": "64-lowercase-hex",
    "implementation": "64-lowercase-hex"
  },
  "request_file": "request.json",
  "request_sha256": "64-lowercase-hex",
  "response_file": "response.json",
  "response_sha256": "64-lowercase-hex",
  "request_process": {
    "pid": 1234,
    "uid": 0,
    "gid": 0,
    "name": "appspawn-x",
    "selinux_context": "u:r:appspawn:s0"
  }
}
```

`request_file` 与 `response_file` 必须是 receipt 所在目录内的普通相对路径；
absolute、`..`、任何 symlink 组件和非普通文件都会被拒绝。复制后的 normalized
receipt、request 和 response 也必须严格位于 `run_dir` 内。两者都必须含相同
`request_id`。

`request_process.name` 必须已经出现在 `begin --process` 白名单和 begin 快照；
receipt 不能在 finalize 时扩张可信进程集合。该进程的
`{pid,uid,gid,name,context,exe,cmdline_sha256}` 必须在 begin/end 唯一且连续。
默认绑定 `appspawn-x` 与 `foundation`。`begin` 还会从 `--root` 复制并冻结该
Action 的 `atom.yaml`、`verification.md` 与 `IMPLEMENTATION.yaml`；receipt 的
`contract_sha256` 必须逐项等于 `session.json` 中的冻结哈希。

`finalize` 在执行任何 HDC 命令前，先验证 begin bundle 的闭合 manifest、
begin validation、原始 raw hashes、冻结的卡 1 receipt chain，以及
`serial == original_serial == allowed_serials[0]`。任一项变化都会在设备访问前
拒绝。

随后才只读采集结束状态并离线校验：

```bash
python3 src/tools/experiments/d600/fn01_enforcing/fn01_enforcing.py finalize \
  --run-dir /tmp/fn01-a04-enforcing-run \
  --request-receipt /path/to/request-receipt.json

python3 src/tools/experiments/d600/fn01_enforcing/fn01_enforcing.py validate \
  --run-dir /tmp/fn01-a04-enforcing-run
```

工具保存 `session.json`、原始命令输出、请求/响应/receipt、请求窗口 hilog delta、
SELinux denial delta、`validation.json` 与 `MANIFEST.sha256`。离线重放会重新核验
所有原始文件哈希。

## 拒绝条件

- `getenforce` 不是逐字 `Enforcing`；
- 卡 1 receipt 未导入至少一个 artifact hash，或设备/receipt 任一哈希不一致；
- 卡 1 gate/build/device receipt schema 未知、字段缺失/多余、body digest 或
  manifest closure 不一致；
- 卡 1 gate 非 PASS、未绑定部署代际、Action/generation/serial/boot 不一致；
- receipt 未绑定本次冻结的 definition/verification/implementation 哈希；
- serial、boot ID 或关键进程
  `{pid,uid,gid,name,context,exe,cmdline_sha256}` 改变；
- 文件或进程 SELinux context 缺失/格式无效；
- receipt uptime 落在采集窗口之外；
- request/response 哈希不符或 request ID 无法 join；
- hilog 前后窗口无法证明连续（旧窗口或 ring rotation）；
- 与 request ID / 绑定进程 PID/name/context 相关的 SELinux denial；
- 请求窗口内存在无法可靠归因的 SELinux denial。工具选择 fail-closed，不把
  “暂时关联不上”解释为“与请求无关”。

安全护栏会硬拒绝 `5EAB` serial。本工具不执行部署、重启、日志清空、系统分区
写入或任何 Action 刺激。

## 自测

```bash
cd src/tools/experiments/d600/fn01_enforcing
python3 -m unittest -v test_fn01_enforcing.py
```
