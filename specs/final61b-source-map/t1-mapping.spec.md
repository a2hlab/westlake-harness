spec: task
name: "Original v1 source map plus exact f28 sources and pending dynamic bindings"
inherits: project
---

## 意图

复用原811来源map、f28十一成员七bind与原build_seal/realization编译器，生成disabled静态映射、机器缺口表和真实CLI预演。静态内容与真实观测分离；仅在新实际同板plan、boot/WMS及overlay admission齐后填动态来源。

## 已定决策

- 824文件来源来自原811加13；954计入独立130APK，不把APK塞进原sameboard source_files。
- table/worker必须实际61b七bind metadata/BMSUID派生；run.sh必须独立同boot原始WMS回执派生。
- 原CLI源码逐SHA pin；预演只证明离线接口，不能产运行时PASS或签名。

## 边界

允许修改: benchmark/2026-10-13-final61b-source-map/**、specs/final61b-source-map/**、tools/spec-checks/tests/final61b_source_map.rs。
禁止修改: 主树、T4、原编译器、冻结包、运行中5ea件、设备、授权或验收条件。

## 验收标准

场景: 完整静态来源与动态缺口显式输出
  测试: final61b_source_map
  假设 原811 source map和f28不可变源码逐SHA存在
  当 编译独立disabled source映射
  那么824文件与130APK完整且静态缺口为零或精确列明unknown
  并且table/worker/run.sh未知字段不假填

场景: 错SHA或掉成员拒绝
  测试: final61b_source_map
  假设 原map删项或f28 sourceSHA漂移
  当 离线映射或原CLI预演
  那么拒绝不减守卫且零设备调用

场景: 原CLI完整954兼容性与pending拒绝
  测试: final61b_source_map
  假设 原build_seal和sameboard realization入口可读
  当 明确fixture预演或运行未知boot的disabled模板
  那么完整文件和包集合不减少且pending不能产生实际通过
