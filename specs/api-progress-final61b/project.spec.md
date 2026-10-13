spec: project
name: "Actual61b evidence addition to the existing315 API atlas"
---
## 意图

复用现有315条API表，把同61b最终128实测的受限判词补入NATIVE-173，保留已有实现和版本边界。

## 约束

- 零设备操作、零运行时改动、零推送；原315包与运行中的round保持不变。
- 只声明真实证据覆盖的OH6.1.0.31；Android版本未知项、API未冻结、普通应用功能未验证不升格。
- 当前全量尚在运行，缺少实际outer128接受回执时只准备代码，禁止生成通过结论或借5ea数据。
