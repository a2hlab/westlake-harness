# 重现说明(非自动执行脚本):dex2oat 工具链从源到镜像到门
#
# 前提:hw248 上有 /home/alvin/aosp-14.0.0_r1-art(AOSP 14.0.0_r1,art/ 已应用 series 的补丁)
# 与本机 knowledge/toolchains/art-r155/{patches,series} 同步(22 件)。
#
# 一条命令(在 hw248 上,从干净 r1 树到出件过门):
#
#   bash reproduce-from-scratch.sh
#
# 该脚本按以下步骤执行(每步失败即停):
#
# 1. 应用 22 个补丁到 art/(逐字节验收由 check_series.py 做):
#      cd /home/alvin/aosp-14.0.0_r1-art/art
#      for p in $(cat /path/to/series); do git apply --check /path/to/patches/$p && git apply /path/to/patches/$p; done
#
# 2. 编译 dex2oat64(6 项环境):
#      cd /home/alvin/aosp-14.0.0_r1-art
#      source build/envsetup.sh && lunch aosp_arm64-userdebug
#      export ART_USE_READ_BARRIER=false ART_DEFAULT_GC_TYPE=CMS \
#             ART_USE_GENERATIONAL_CC=false ART_HEAP_POISONING=false ART_TEST_DEBUG_GC=false
#      export ALLOW_MISSING_DEPENDENCIES=true
#      m -j32 dex2oat
#    验收:sha256sum out/host/linux-x86/bin/dex2oat64 == ae865ddd6a7e4b25…(全值见冻结条目)
#
# 3. 出镜像(9 jar,T5c 或 T7c 版 stubs):
#      /home/alvin/cc-wiki-t5/tool/t5_gen_image.sh \
#        --dex2oat out/host/linux-x86/bin/dex2oat64 \
#        --jars-dir <9-jar 目录> --out <输出目录> --ref <对应 boot-image-inputs.sha256>
#    验收:27/27 出件,vdex 9/9 逐字节同(T5c)或 8/9(T7c,stubs 件差为预期),oat230/image108
#
# 4. 过门:
#    a. rb 门:python3 knowledge/toolchains/art-r155/check_boot_oat_rb.py <out>/boot.oat
#       → PASS(concurrent-copying=false)
#    b. t4b 门:先按 BUILD.template.md 生成回执(程序生成,不手抄哈希):
#         python3 生成 <evidence>/<name>-BUILD-snapshot.md(t4b-build-json 围栏,绑 libart=R155
#         59e1bb45… 与 boot.oat 实算 sha256,environment 6 项,native_debug_build=false)
#       然后:python3 knowledge/toolchains/art-r155/t4b_build_switch_gate.py \
#         --libart <板上 R155 libart 路径> --oat <out>/boot.oat --build <快照> → exit 0
#
# 红线:不从别处拷 dex2oat;不改 frozen.json;T6c/T7c 板上过了才登记冻结。
