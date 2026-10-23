spec: task
name: "T116 current launch-control identity inventory"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t115-launch-policy-provenance]
---
## 意图
把T115历史两板启动管理代次差异绑定到当前同boot的实装文件。仅采普通配置元数据和文件哈希，不读取或分析watchdog实现内容，不执行旧部署预检。
## 已定决策
- CC唯一设备操作者，61b和5cd各先held/boot/相关进程读检，冲突停止。仅只读每板60秒全批120秒，不UI/重启/进程信号/修改配置。
- 精确现有init配置/system/etc/init/01_westlake_u13_toutiao.cfg，保留SHA和受限服务名/启动argv以发现实际ROOT。仅在该已观测ROOT及当前boot子目录读startup.env/startup.expected/members.tsv之配置元数据，公开只ROOT/serial/版本/重试与人工重入参数/哈希字段；没有明确参数则unknown。
- entry.sh/config-common.sh/boot-entry及watchdog实现仅sha256sum和stat，禁止cat、strings、反汇编或源码内容分析；这是新hash-only身份采集，不运行T71/T74/T91已停止分析/部署流程。不存在的文件保留unknown，不扫描其他应用数据。boot副本文件名来自已有manifest或精确目录名清单，不猜根目录。
- 最后复核boot身份，原始argv/rc/正文/时间持久保存，哈希比较由Codex对T115 metadata完成；文件SHA相同不等于运行时模式已证。
## 边界
### 允许修改
- benchmark/2026-10-23-current-control-fingerprint/**
- 私有 $HOME/.local/share/westlake/current-control-fingerprint-20261023/**
### 禁止
- 任何设备写、源码内容/停止流程、全盘扫描、退出归因、部署
## 验收标准
场景: 实装配置哈希可绑定
  审核: human
  测试: current_control_fingerprint_review
  假设fresh空闲板和明确initROOT
  当只读配置元数据及哈希并核前后boot
  那么给对应board/boot/root/实装SHA，区分历史记录与当前配置
场景: 文件不存在或路径身份不明
  审核: human
  测试: current_control_fingerprint_review
  假设holder冲突、超时、缺文件或根目录无法绑定
  当触发停止条件
  那么保留unknown且不转为源码读取或修改设备补齐
## 排除范围
改变重试策略、部署、随机退出、T91候选。
