spec: project
name: "N3b Java/native artifact contract"
---

## 意图

离线核实N3b按名查找的Java定义确实存在于配对JAR，而不是仅有引用或近似签名。

## 约束

- 不上板、不改生产JAR/native/boot；真实旧J5作负控。
- 输入记录完整SHA；静态契约通过不等于provider可用或上屏。
