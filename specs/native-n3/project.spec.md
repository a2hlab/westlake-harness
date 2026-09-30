spec: project
name: "N3 native cluster batch on U2"
---

## 意图

以 U2 N2 51a78bde 为基线，按实际首墙与验证过的上游实现合并下一版 native 候选，离线完成后交外环排板。

## 约束

- 不写板，截图与运行期结论须外环验证；保留同 JAR 与安装器作为将来的对照条件。
- 冻结源与 provider 字节不变；新功能另起文件。
- 已公示 N2 包不覆盖，只生成新包并提供回滚命令。
