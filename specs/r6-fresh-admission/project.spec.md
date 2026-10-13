spec: project
name: "R6 fresh deployment admission without identity reconstruction"
---
## 意图

只消费主树已冻结337身份及full128/十控输出，独立绑定下一实际部署及新boot。

## 约束

- 零设备调用、零部署、零启用、零推送；只写T0新目录。
- 原40f0是artifact来源；未知candidate boot保持null，不借旧实测PASS。
- 原identity/Reader/driver所有失败门及128时序不改。
- origin仅由本轮签pin实际只读probe/metadata首尾及四recv派生，重试重新pin证据，不硬编码boot常量。
