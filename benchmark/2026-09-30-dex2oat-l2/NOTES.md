# T6 板上 L2 验证脚本(cc-wiki #80,离线预备,specs/dex2oat-once/t6-board-l2.spec.md)

`t6_board_test.sh` —— 板重接后**一条命令**跑完 T6 窗口(≤30 分钟),已 `--dry-run` 离线自检(27 文件识别、L1 校验、全流程计划、未碰板)。

## 一条命令
```
benchmark/2026-09-30-dex2oat-l2/t6_board_test.sh --serial <sn> --image-dir <T5产物目录> [--dry-run]
```
`--image-dir` = T5 的 27 个镜像文件 + `boot-image-inputs.sha256`(脚本从 manifest 的 `arm64/*.{art,oat,vdex}` 行取 27 个,libart 不在其中、不动)。

## 流程(与 T6 契约一一对应)
1. 只读预检(boot_id、runtime fingerprint 期望 937e2a6d0d88)+ `board_note.sh lock`。
2. **只读备份** resident 27 文件(sha 到 resident-before.sha256 + `cp -a` 到 /data/local/tmp/t6-backup)。
3. 推 T5 27 文件到 /data/local/tmp/t6-new。
4. `begetctl stop_service appspawn`(**绝不 kill -9**)→ **bind-mount** 27 文件覆盖 `/system/android/framework/arm64/*`(可逆、免 /system rw、libart 不碰)→ socket 属主修正 → `begetctl start_service`。
5. `bms_batch` 跑 HW/ZZ + 5 已亮 app(--hilog 20 --shots 5,20)。
6. grep facts/hilog 有无 `CheckSystemClass` abort;有则当场拉 /data/log/faultlog/temp/ cppcrash 原文。
7. 回滚:stop appspawn → umount 全部 bind → start appspawn → 核 runtime fingerprint==937e2a6d0d88 + resident 27 文件 sha 逐字节还原 → unlock。
8. 30 分钟窗口守卫,超时强制回滚。

## 板重接后需**先确认**的三项(脚本已参数化/占位,勿盲跑真板前先核)
- `APPSPAWN_SVC`:begetctl 服务名(默认 `appspawn`;板上实际可能 `appspawn` 或别名——`begetctl service_control` 列表核对)。
- **socket 属主修正**:appspawn socket 路径与属主(占位;板上 `ls -lZ` 现役 socket 后填精确 chown/chmod)。
- `runtime_fp` 读取路径(默认 /data/local/tmp/asx/runtime-fingerprint.txt;以 run_facts 实际输出为准)。
- 5 个已亮 app:默认 fd-droidify/fd-auxio/aegis/fd-calendar/ooniprobe;以当时 U2/U3 lit 清单为准(--keys 可覆盖或用 APPS 环境变量)。

## 验收(d6_board_accepts_image,human)
facts 无 CheckSystemClass abort + 外环读图 HW/ZZ+5=7 个 app t20 自身界面 + 卸载回 U2(fingerprint 937e2a6d0d88)。**bind-mount 覆盖的是镜像文件、libart 不动**,所以 runtime fingerprint 全程应保持 937e2a6d0d88(该字段是运行时库集,不含 boot 镜像)——回滚主校 = resident 27 文件逐字节还原。
