spec: task
name: "F28 same-board 61b/5cd complete identity and original full128 successor"
inherits: project
depends: [t1-proof, t2-driver]
---

## 意图

继承已冻结身份门与原128驱动，只消费主树 T4 f28 新 composition，生成独立 disabled sibling。61b 与5cd各自绑定原940真实来源、UID与RouteB488，不借5ea缺席或安装回执。

## 已定决策

- 原 Reader、presence parser、完整检查函数与原 driver 函数保留；runtime 四共享替换中的947改为f28。
- 由主树精确58ee编译器重新验证原raw/R5来源并消费单一954 union；507文件metadata与5目录全部保留。
- 原128、121t10+7t20、8窗与resolve/records/collect不变；当前无同板installed记录或reboot前像时round明确pending。

## 边界

允许修改: benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-identity-f28*/**、本契约、tools/spec-checks/tests/final_v2_identity_f28.rs、README.md、.octos/KNOWLEDGE-DIGEST.md。
禁止修改: 已冻结原件、主树、T4、运行中5ea件、设备、授权、运行时产物。

## 验收标准

场景: 主树5cd完整真实前像离线编译
  测试: final_v2_identity_f28
  假设 主树新capture与T4 composition逐SHA闭合
  当 prepare_identity.py使用独立composition pin输出disabled proof
  那么319仅4替换且完整954及507metadata与5目录保留
  并且保留原940来源与UID并不产生新boot或live PASS

场景: 真实输入错误拒绝
  测试: final_v2_identity_f28
  假设 composition SHA错误或仅原940输入或61b pending模板
  当 本地CLI运行
  那么非零拒绝且零设备调用

场景: 原完整驱动行为及失败门保留
  测试: final_v2_driver_f28
  假设 已冻结原driver与128manifest/tier可读
  当 比较函数AST并以明确synthetic索引离线准备8窗
  那么全部driver函数保留并输出121t10+7t20默认disabled

场景: 借板安装回执与缺record拒绝
  测试: final_v2_driver_f28
  假设 5cd proof输入61b索引或synthetic安装记录
  当 原installed-record guard执行
  那么拒绝且不执行任何窗口

## 排除范围

新板capture、安装或部署、新boot、用户解封、真实全954及fresh128、UI签认均留pending；不生成新授权或签名。
