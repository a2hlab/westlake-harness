spec: task
name: "61b exact postinstall readonly capture successor"
depends: [t12-routeb-fresh-restore]
---

## 意图

在61b用户解封前离线补齐安装后捕获入口。精确复用已验证5cd collector，只派生serial、schema及61b目标清单，为现有provider提供真实同boot身份；默认预览，当前不调用设备。

## 已定决策

- 原collector只改说明、serial与schema，capture.request逐字复制真实61b清单；497文件、319基线、三目录和根absence范围不变。
- 保留expected-boot、同boot BMS UID原始三联回执、cfg原字节SHA、每条远端rc与metadata校验；不填猜测UID/WID或伪造complete。
- fixture仅替代transport，执行实际入口解析和写件流程；不得访问真实HDC。真实运行须用户解封与外环授权，不在本轮执行。

## 边界

### 允许修改
- benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/capture61b-postinstall/**
- specs/demo-recovery-followup/t13-61b-postinstall-capture.spec.md
- tools/spec-checks/tests/capture61b_postinstall.rs

### 禁止
- 不改冻结collector/provider/原seal及现运行件。
- 不操作61b或任何设备、VM、远端，不签认、不新增框架。

## 验收标准

场景: 参数派生与默认零设备
  测试: capture61b_preview
  假设 已冻结5cd源及61b请求清单
  当 使用新入口的out与expected-boot参数且不带execute
  那么 输出DISABLED_READONLY_PREVIEW且零设备调用、不创建输出目录，源差异仅三处字符串

场景: 完整fixture捕获
  测试: capture61b_complete
  假设 fixture提供497文件metadata、319全等、合法BMS UID、cfg原字节、根不存在及稳定boot
  当 实际入口读取fixture transport
  那么 生成complete捕获及独立BMS原始三联回执、SHA全可验证且设备调用为零

场景: 错板错boot拒绝
  测试: capture61b_identity_reject
  假设 请求serial错误或实际boot不等expected-boot或末尾boot改变
  当 执行fixture入口
  那么 非零拒绝且不得产出complete捕获

场景: 字节身份或传输错误拒绝
  测试: capture61b_content_reject
  假设 cfg被strip或BMS UID缺失或远端rc错误或stderr非空
  当 执行fixture入口
  那么 非零拒绝且不得产出complete捕获，不将错误视为absence

场景: 已有根不伪造absence
  测试: capture61b_root_reject
  假设 fixture的Boat根已存在且其余读取正确
  当 执行fixture入口
  那么 rc2且complete为false并保留真实PRESENT与pending，不删除任何目录

## 排除范围

- 真实61b解封、安装、采集、部署、重启、全128及封板签字。
