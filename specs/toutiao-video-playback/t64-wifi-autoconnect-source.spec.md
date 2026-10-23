spec: task
name: "T64 bounded OH WiFi autoconnect source reference"
inherits: project
depends: [t62-61b-demo-homepage-handoff]
satisfies: [REQ-TTVIDEO]
---
## 意图
配合T63当前网络证据，静态查已有OH WiFi自动连接、关联与DHCP日志含义，找到能指导正常设置恢复的可信入口。源码候选不冒充板上精确版本，不做推测修复。
## 已定决策
- 限10分钟，先仓库知识与本地workspaces/已知OH源位置，再OrbStack已知源码；没有准确位置则报告缺口，不全盘扫描、不下载整树、不搜远程随机目录。只读不碰板。
- 记录实际源码commit/blob SHA、精确文件行号，界定自动连接被禁/候选筛选/认证失败退避/DHCP等待等与本轮日志有关的最多三个分支，给区分这些分支需要的现有日志字段。
- 独立工作先完成来源定位，T63证据到后再交叉归属；没有同版本构建映射时写source_candidate。不得读取凭据、运行REA、debugger、T38或修改配置；缺源码则直交缺口，不能猜实现。
- 公开报告保存小证据与结果，私有用户路径用$HOME或WORKSPACES表述。测试选择器是人工回执入口，尚未实现，不报lifecycle PASS。
## 边界
### 允许修改
- benchmark/2026-10-23-wifi-autoconnect-source/**
### 禁止
- 设备操作、远程扫描、工具权限、凭据、产品源码改动、构建部署；不push。
## 验收标准
场景: 找到可绑定源码
  审核: human
  测试: existing_wifi_autoconnect_source_receipts
  假设本地存在已知OH源码
  当核查自动连接最多三个相关分支
  那么给原文件SHA和行号、触发条件及待匹配日志，区分source_candidate与精确部署来源
场景: 缺精确来源或时间预算用尽
  审核: human
  测试: existing_wifi_autoconnect_source_receipts
  假设没有可绑定来源或超过10分钟
  当结束查找
  那么报告搜索边界与缺项，不扩大扫描或声称全机不存在
## 排除范围
运行时修改、网络配置修改、凭据、头条崩溃、其他APK。
