# 精确物理发布映射（冻结 core 不变）

确定展平一层，最终唯一用户视图目录是：

`$WORKSPACES/westlake-harness/benchmark/2026-10-14-api-progress-final61b/views`

实际 build 放T0 frozen core要求的子目录 `final-build-actual`。其 `final-build-actual/views/<name>` **逐字复制**到T0同包 `views/<name>`，再由原land工具将同相对路径落MAIN；不保留 `final-build-actual/views` 作为发布位置。所有views文件（HTML/JSON/CSV/Markdown/上下文/附录）一同展平，内部相对链接不改。精确逐文件路径/SHA清单只能由实际build产物派生，现在保持null。

build旁边的三个真实回执另放新兄弟包 `benchmark/2026-10-14-api-progress-final61b-publication/actual/{binding.json,request.actual.json,verification.json}`，不覆盖core的pending results/freeze等20件；也不在core HERE子目录放另一份request.actual.json，避免其自动发现逻辑误判发布深度。

root实际authority到达后，原 build/check 仍按已冻协议执行。展平只复制原字节，不改JSON记录或生成链。land之后必须额外跑本包只读物理校验器，**从实际MAIN HTML父目录**解析HTML内已生成的每个`evidenceLinks`，校核真实文件路径、声明fullSHA、双语315 canonical及CSV；同时从实际位置解析Markdown链接。校验器不import core、不调用core.link/link_check，也不用固定逻辑origin计算通过。

```sh
M="$WORKSPACES/westlake-harness"
T="$WORKSPACES/westlake-harness-t0"
# 实际315 views已按映射land后，由T0只读核实MAIN物理路径。
python3 "$T/benchmark/2026-10-14-api-progress-final61b-publication/verify_physical_links.py" \
  --views "$M/benchmark/2026-10-14-api-progress-final61b/views" \
  --receipt "$T/benchmark/2026-10-14-api-progress-final61b-publication/final-main-links.actual.json"
# 原生成/data检查针对展平目录：--out是views的实际父目录，不传build子目录。
python3 "$T/benchmark/2026-10-14-api-progress-final61b/increment.py" check \
  --request "$T/benchmark/2026-10-14-api-progress-final61b-publication/actual/request.actual.json" \
  --out "$M/benchmark/2026-10-14-api-progress-final61b"
```

当前最终views尚不存在，actual-main物理通过回执为null。已对现有MAIN原315 views跑真实物理链接控制，记录为baseline-control，不能冒称新315已落地通过。最终路径不符、保留多一层或目标SHA错均拒绝；失败保留原build/landing，不改core或用逻辑origin放行。全程零设备、不写MAIN、不碰运行round。
