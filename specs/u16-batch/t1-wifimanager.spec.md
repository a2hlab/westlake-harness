spec: task
name: "T1 fd-wifianalyzer: stubs WifiManager 按『无 Wi-Fi』补 8 方法"
inherits: project
tags: [stubs, wifi, bcp]
depends: []
---

## 意图

fd-wifianalyzer 死因是 `android.net.wifi.WifiManager` 在 adapter-mainline-stubs 里只有构造器的空壳(u16 簇 N):app 调 `getConnectionInfo`/`getScanResults` 等 8 个方法全部 `NoSuchMethodError`。本任务在 BCP stubs 里按『设备无 Wi-Fi』的语义补齐这 8 个方法——返回空扫描结果、disconnected 的 WifiInfo、false 开关——让首墙从 NoSuchMethodError 移走,app 走到自己的『无网』UI。

来源:benchmark/2026-10-03-u16-wall-clusters/clusters.csv 簇 N(owner_deliverable 已点名 adapter-mainline-stubs WifiManager 8 方法)。

## 已定决策

- 8 个方法清单从 fd-wifianalyzer 的 dex 调用点取(stub_member_gap 输出),不凭记忆列。
- 语义取『无 Wi-Fi』:getScanResults→空列表;getConnectionInfo→SSID 空的 WifiInfo;isWifiEnabled→false;startScan→false;其余按 AOSP 返回类型的空值/默认值,不抛异常。
- 改的是 adapter-mainline-stubs.jar 的内容——属 BCP 烤制(FZ-005):按 project 约束走『加新功能且原行为保留』,外环批准后在单板重验 FZ-005 原 4 个证据 app,再登记新版。
- 观察点:fd-wifianalyzer 进 U16 键表 movers(来源=簇 N),check_fix_observers 的 stubs token 命中。

## 边界

### 允许修改
- benchmark/2026-10-03-u16-t1-wifimanager/**(新目录)
- adapter-mainline-stubs 源新增 WifiManager 方法体(经外环批的 FZ-005 路径)
- tools/spec-checks/tests/u16_t1_wifi.rs

### 禁止
- 不动 WifiManager 之外的 stubs 类
- 不实现真 Wi-Fi 语义(不连 OH Wi-Fi 服务)

## 验收标准

场景: 8 方法补齐且按无 Wi-Fi 语义答
  测试: u16_t1_wifi_methods
  假设 新 stubs JAR 经 baksmali/dexdump 反查 WifiManager
  当 数新增方法
  那么 恰 8 个且签名与 fd-wifianalyzer 调用点一致
  并且 每个方法体不含 throw(空值/默认返回)

场景: 首墙移动
  测试: u16_t1_first_fatal_moves
  假设 U16 窗口跑 fd-wifianalyzer 1 次
  当 first_fatal.py 取首个致命点
  那么 不再是 WifiManager NoSuchMethodError
  并且 若 app 进入自有 UI 则 t20 判定交外环(审核: human)

## 排除范围

- 不含真 Wi-Fi 服务适配(那是后续 OH Wi-Fi 服务桥的独立任务)。
