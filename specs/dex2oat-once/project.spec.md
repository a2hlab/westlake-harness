spec: project
name: "一劳永逸的 ART 工具链:libart、dex2oat、boot image 出自同一份有记录的源码"
tags: [dex2oat, art, boot-image, toolchain]
---

## 意图

板上 route-A R155 的 libart 是 android-14.0.0_r1 加寒冰 ART 补丁、在一台已释放的 ECS 上编的,只留了产物;生成板上 boot image 的 dex2oat 也没留配方。官方 android-14.0.0_r16 dex2oat 生成的镜像被板上 libart 的 ClassLinker::CheckSystemClass 以布局不符 abort(oc-t4 2026-09-30 14:01,cppcrash-9465)。本战役用 r1 完整源码树加入库的补丁序列,在同一棵树里编出 libart 与 host dex2oat,生成能被板子接受的 9 段 boot image,并把源码、补丁、配方、哈希全部入库、登记冻结,从此改 boot 类(tagsoup、MediaStore 字段)不再考古。

## 约束

- 源码只认 AOSP 官方 tag 加入库的补丁文件;补丁序列放 `knowledge/toolchains/art-r155/patches/`,每个补丁写来源(寒冰两版目录之一、B6 重建树、或按 R155 反汇编补写)
- 构建只在 hw248 自建目录 `/home/alvin/aosp-14.0.0_r1-art/` 下进行,共享树只读;磁盘剩余低于 30 GB 即停
- 板上验证只用短窗叠加:叠加前 board_note.sh lock,≤30 分钟,结束卸载回 U2 并核 runtime fingerprint 937e2a6d0d88 后 unlock;绝不 kill -9 appspawn-x,停起用 begetctl
- 只对 knowledge/boards.json 白名单内的板下命令
- 判定以 t20 截图为准,ACK 的数字原样引用 facts.txt
- 不提交密码、服务器账号;提交信息不带 Claude 署名行;不推送,等外环

## 已定决策

- 底子用 android-14.0.0_r1(R155 同底,kImageVersion 108 / kOatVersion 230,与板上一致),不用 r16
- 补丁基线先取 B6 重建树 `bms/src/.work/b6-art14-recovery/art-hanbin` 相对 `art-r1` 的 20 个差异文件,再与 `~/workspace/hanbin_adapter/aosp_patches` 和 `~/orca/HanBingChen/adapter/aosp_patches` 两版逐一对账
- 板上现役 libart 不动为首选路径(只换镜像);只有镜像在现役 libart 下仍被拒,才改为 libart 与镜像同换,并按分级冻结走全量回归
- 输入 jar 与镜像文件的参考哈希以 `knowledge/toolchains/boot-image-inputs.sha256` 为准
