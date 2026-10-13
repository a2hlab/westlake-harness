spec: project
name: "Final61b disabled source mapping over original seal compilers"
---

## 意图

为已审f28组合准备可迁树的原source-files映射与原CLI入口；原签认和验收条件不变，未知真实参数保留pending。

## 约束

- 零HDC、设备、部署、推送；只创建独立新文件，不改冻结包。
- 仅61b最终同板口径；5ea承担当前f28全量，不新增5cd full128。
- source-files仅824文件，130APK走原packages/raw哈希，完整954不减少。
- 原run.sh只经原独立host/WMS原始回执与running_files派生；不得抄新SHA或猜WID。
