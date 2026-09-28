# Fn01 PackageManagementService 拓扑早期实验

本目录只包含 `PACKAGE_MANAGEMENT_SERVICE_TOPOLOGY_PROPOSAL.md` 中
E1/E2/E3 的空壳实验，不是产品实现，也不发布 canonical package generation。

当前 target `fn01_topology_probe` 用项目私有实验 SA ID `127233`
（vendor-reserved range，且构建时必须完成 source collision scan）验证以下最小闭包：

- 先通过 dirfd、`openat`、`O_NOFOLLOW`、`lstat/fstatat` 和 owner/type/mode
  校验安全打开测试 store，再取得跨进程独占锁并写入 recovery marker，
  之后才尝试向 samgr 注册测试 SystemAbility；
- client 通过 samgr 获取服务并发起同步 IPC；
- server 只从 `IPCSkeleton` 读取 peer pid/uid/token/sid，并把 DTO 中自报 uid
  作为不可信字段进行交叉校验；claimed UID 与 peer UID 不一致时服务端拒绝，
  claimed user 只接受由可信服务配置固定的 primary user `0`，不从 DTO 推导；
- server 通过 BMS SA `401` 的只读 `GET_NAME_FOR_UID` transaction 做 E3
  最小权限探针。

这里的两个普通 native client 只能验证 IPC peer identity 机制和拒绝伪 UID，
不能代替 E2 要求的两个真实 `appspawn-x` Android 子进程。SystemAbility 从
shell/debug domain 启动也不能证明最终 init service、独立 SELinux domain 或
access-token profile 已资格化。

## AlexPC source/build-only

```bash
scp -r src/tools/experiments/d600/fn01_package_service_topology \
  AlexPC:/tmp/fn01_package_service_topology
ssh AlexPC \
  '/tmp/fn01_package_service_topology/build_on_alexpc.sh \
   /opt/build-trees/oh610_lts_source'
```

构建脚本固定使用 OH 6.1 source tree 自带的 clang、musl sysroot 与
`out/wukong100` 同代 innerkit shared libraries。它打印 source baseline、
compiler、完整命令和 ELF identity；同时保存 linker map/dependency receipt，
并对实际参与链接的 CRT、对象文件、OH 库和工具链库逐文件计算 SHA-256。
source collision scan、actual-link-input 清单和最终 artifact 一并进入同代
provenance receipt。

## 运行边界

构建不包含部署。后续真机运行只能使用明确选择的非 5EAB 设备，且只允许
`61b0...` 或 `654b...` 两个 allowlist serial；输入先统一为 lowercase，再
hard reject `5eab...`。不得写入 `/data/local/tmp` 以外位置，不得替换系统
分区文件或重启设备。本轮 source/build 修复不执行任何设备动作。
