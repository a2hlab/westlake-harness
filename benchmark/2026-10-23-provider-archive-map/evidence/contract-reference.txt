spec: task
name: "G38 frozen provider input archive mapping"
inherits: project
depends: [t37-provider-build-chain]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
G37找到了精确容器入口但缺冻结775c8ae8编译脚本。本卡沿已存art-r155构建回执和来源索引寻找冻结输入归档映射，结束同名文件猜测，为可复现构建补实际输入。
## 已定决策
- 只读取主干0a52f405ec的G37报告、knowledge/toolchains/art-r155及它直接引用的来源记录；最多两层引用，不全仓SHA搜索不遍历整盘。先列被引用的具体文件再读取。
- 分别记录输入归档、冻结input mount映射、实际775c8ae8脚本、原始构建日志。找到归档路径只能申请outer精确读取，不自行远程/Orb操作；无引用即明确缺口，不能猜路径。
- 只在精确775c8ae8匹配后分析第二层编译脚本；任何同名不同哈希文件保留为不匹配，禁止替换目标sigchain6d5d5538为ea7becd0。两种目标的来源分开。
- 只读源码溯源，不构建、不调试或操作设备，不调用REA，不重试G34/G36被拒动作。源码可复现进展不等于原神运行进展。
- 输出README.md/results.json、引用SHA和逐跳链表、下一步可执行输入请求；离线校验器及Rust测试覆盖引用缺失、脚本哈希不符被冒充匹配、缺原始日志被冒充构建完成。
## 边界
### 允许修改
- benchmark/2026-10-23-provider-archive-map/**
- tools/spec-checks/tests/provider_archive_map.rs
### 禁止
- 修改历史证据、主树、运行时、冻结项、权限、commit/push；设备、远程、Orb、REA、调试器、运行时构建。
## 验收标准
场景: 两层归档映射有真实来源
  测试: provider_archive_map
  假设已有G37精确入口和art-r155记录
  当沿直接引用查找输入归档
  那么逐跳记录文件SHA和引用行，最多两层且无引用的路径不提出为已知来源
场景: 脚本哈希不符拒绝闭环
  测试: provider_archive_map
  假设找到的同名脚本不等于775c8ae8
  当校验可复现结论
  那么非零拒绝匹配声明且保留目标sigchain身份
场景: 缺日志拒绝构建完成
  测试: provider_archive_map
  假设原始编译stdout stderr与rc0未恢复
  当校验报告
  那么不能宣称构建闭环或游戏首屏成功，并明确下一项缺失输入
## 排除范围
原神设备实验、崩溃归因、替换运行库、全面历史搜索、重试被拒诊断。
