# T5 boot-image 生成脚本(cc-wiki #80,离线预备,specs/dex2oat-once/t5-boot-image.spec.md)

`t5_gen_image.sh` —— hw248 上 **T3 一出 dex2oat64 就跑**,已 `--check` 离线自检(9 jar 哈希对上 boot-image-inputs.sha256、cmdline 组装正确)。

## 一条命令
```
knowledge/toolchains/art-r155/t5_gen_image.sh --dex2oat <T3的dex2oat64> --jars-dir <9jar目录> \
  [--work /opt/build-trees/.work/fn03-r29-boot-20260728T0635Z] [--out <dir>]
# 离线自检:t5_gen_image.sh --check --jars-dir <9jar目录>
```

## 依板 boot.oat 记录(dex2oat-a14.md OatHeader key-value 节)
- **9 jar bootclasspath 顺序**:core-oj → core-libart → core-icu4j → okhttp → bouncycastle → apache-xml → adapter-mainline-stubs → framework → oh-adapter-framework。
- **cmdline**:`--android-root=/system --instruction-set=arm64 --base=0x70000000 --compiler-filter=speed --runtime-arg -Xms64m --runtime-arg -Xmx512m --runtime-arg -Xverify:none --image=<work>/products/arm64/boot.art --oat-file=…/boot.oat`,每 jar `--dex-file=<work>/incoming/<jar> --dex-location=/system/android/framework/<jar>`。
- **键值集**:compiler-filter=speed、concurrent-copying=false、debuggable=false、native-debuggable=false、requires-image=true、apex-versions=(空);isa-features bitmap=0x3、无显式 --instruction-set-features。
- **work 路径**默认取板上原件 `/opt/build-trees/.work/fn03-r29-boot-20260728T0635Z`,--dex-file 走其 incoming/——oc-t4 证:同 work 路径把 .oat/.art 差异缩到只剩 boot.art/boot.oat(路径串嵌进 OatHeader kv)。

## 验收(d5_image_headers_match)
- **9 个 .vdex 与参考逐字节一致**(oc-t4 官方 r16 复现已证 vdex 层 L1 全中)。
- boot.oat oat 版本 230、boot.art image 版本 108;键值集与板一致。
- **.oat/.art 不要求逐字节**:其 OatHeader 嵌 dex2oat-cmdline 路径串 + 源树指纹;脚本记录差异文件与归因(oc-t4:9/27 逐字节 = 全部 vdex;18 差 = 9 .oat + 9 .art)。

## 脚本行为
- 先核 9 jar 哈希;stage 到 <work>/incoming;跑 dex2oat 出 27 文件;L1 逐个比参考(报 same/diff/missing + vdex 命中);L2 断言 boot.oat oat\n230 + boot.art art\n108;vdex 9/9 则 exit 0。
- 输入取自 payload 的 9 jar(v3c-candidate/payload/android/framework 等,9/9 与清单 MATCH)。

## 待 T3
需 T3 的 dex2oat64(hw248 x86-64 host)+ arm64 libart。T3 一出即跑,产物与 L1/L2 报告存 hw248 + 写回 knowledge/toolchains/art-r155/。接 T6(板测,脚本已备)。
