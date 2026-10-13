spec: task
name: "Prepare disabled fresh boot and original deployment receipt binding"
inherits: project
---
## 意图

增加独立离线准入入口，消费主树a4da proof与两个disabled输出，不重复编身份。

## 已定决策

- 用原三件transaction/intent/placed/source-apply/授权及boot raw回执绑定真实新部署。
- 原Reader与absenceReader执行协议通过逐argv与原始rc/marker离线重放核验；完整337原check重新计算结果。
- 仅提供disabled结果，不调用设备、不自动分发full128或十控。
- 实际origin必须从签pin本轮只读证据派生，不写a75或14a4永久常量。

## 边界

允许修改: benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/r6-fresh-admission/**、specs/r6-fresh-admission/**、tools/spec-checks/tests/r6_fresh_admission.rs、README.md、.octos/KNOWLEDGE-DIGEST.md。
禁止修改: 主树/T4/BMS文件、已冻identity/driver、设备、私有数据。

## 验收标准

场景: 主树输出直接消费且未知boot保持pending
  测试: r6_fresh_admission
  假设 主树a4da proof和八窗与十控首plan完整pin
  当 preview CLI读disabled请求并指定输出
  那么 原身份不重编且candidate boot为null
  并且 实际准入拒绝缺部署与fresh回执且没有设备调用

场景: 新部署与独立Reader回执保持所有原失败门
  测试: r6_fresh_admission
  假设 三件原transaction协议和原337Reader完整模拟命令回执
  当 离线逐argv重放原Reader及原check
  那么 新boot与serial及所有对象一致才产生disabled绑定
  并且 错serial或旧boot或缺对象或坏marker或非零rc或掉ABSENT全部拒绝

场景: 本轮实际只读前像派生origin并允许重试重新pin
  测试: r6_fresh_admission
  层级: integration
  替身: 实际已落只读文件及隔离文件负例，设备不访问
  假设 原capture_readonly源及本轮probe和metadata首尾与四recv回执逐SHA签pin
  当 prepare_origin CLI离线派生origin并指定新的disabled请求输出
  那么 origin来自实际完整boot且未知candidate boot保持null
  并且 首尾boot漂移或串板或缺recv或坏marker拒绝且重试换证据无需改源码
