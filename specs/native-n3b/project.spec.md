spec: project
name: "N3b offline WebView publication"
---

## 意图

按外环19:44派单，以N3 8a7880fa为底，只补Westlake 532633da已经实现的native WebView发布边界，Java配套交cc-t3。

## 约束

- 只离线，不向任何板发命令；不改变已导出N3包。
- 冻结源与provider不变；JAR/APK/boot/ART/host/ANL/installer不变。
- native原逻辑整段照抄，Java入口薄包装另文件；无provider或Application时不发布true。
