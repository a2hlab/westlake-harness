# Fn01 构建/部署代际 provenance gate

该工具把下面的链条变成可机械复核的闭包：

`source manifest → builder identity → host/target stages → sealed artifacts → generation identity → device serial/boot_id/readback → gate`

它只证明代际和部署字节一致。`build_pass`、target build pass 或部署哈希一致，
都不自动等于 Action 的 `device_verified`，也不产生正式验收 verdict。

## 生成同代 build closure

```bash
python3 src/tools/experiments/d600/fn01_provenance/fn01_generation_provenance.py \
  --root /opt/Bridge build \
  --config src/tools/experiments/d600/fn01_provenance/fn01-a04-generation.config.json \
  --run-dir var/evidence/atoms/Fn01/A04/runs/<run>/generation
```

输出包括：

- `inputs/source-manifest.json`
- `builder/builder-identity.json`
- `logs/`
- `artifacts/` 下的 sealed 副本
- `build-receipt.json`
- `closure-manifest.sha256`
- `generation-identity.json` 与 SHA sidecar

Enforcing expected hashes 必须从 `generation-identity.json` 导入；不接受调用方
自行拼接的 `PATH=HASH`。

## 只读采集和 gate

```bash
python3 src/tools/experiments/d600/fn01_provenance/fn01_generation_provenance.py \
  --root /opt/Bridge capture-device \
  --build-receipt <generation>/build-receipt.json \
  --serial <D600-serial> \
  --hdc /Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc \
  --output <run>/device.json

python3 src/tools/experiments/d600/fn01_provenance/fn01_generation_provenance.py \
  --root /opt/Bridge verify \
  --build-receipt <generation>/build-receipt.json \
  --device-receipt <run>/device.json \
  --expected-serial <D600-serial> \
  --output <run>/gate.json
```

`capture-device` 只执行 `list targets`、`cat`、`param get`、`getenforce`、
`stat` 和 `sha256sum`。

## AlexPC 预检与 boot 输入检查

```bash
python3 src/tools/experiments/d600/fn01_provenance/capture_alexpc_builder_preflight.py \
  --output-dir <evidence-dir> \
  --remote-workspace /opt/build-trees/.work/fn01-a04-provenance-preflight-r1 \
  --prewarm-aosp-graph

python3 src/tools/experiments/d600/fn01_provenance/check_fn01_a04_boot_inputs.py \
  --root /opt/Bridge \
  --plan src/tools/experiments/d600/fn01_provenance/fn01-a04-boot-image-input-plan.json \
  --output <evidence-dir>/boot-input-check.json
```

预热状态固定为 `CACHE_WARM_ONLY`；最终 generation 必须在 source hash 冻结后
重新构建。boot builder 设计见 `BOOT_IMAGE_BUILDER_DESIGN.md`。

## ARM64 boot generation worker

`build_current_boot_generation.py` 在 AlexPC 的全新 work 目录执行，输入目录契约为：

```text
incoming/mainline-stubs/java/**/*.java
incoming/oh-adapter-framework.jar
incoming/coverage-manifest.json
```

示例：

```bash
python3 build_current_boot_generation.py \
  --aosp-root /opt/build-trees/aosp-arm64-d600 \
  --work /opt/build-trees/.work/<fresh-generation>
```

worker 会从 current AOSP tree 冻结 d8/d8.jar、JDK identity、dex2oat 及动态依赖、
六个 stock/current dex jar，再从 frozen staging 重放 `core-icu4j` 与
`adapter-mainline-stubs` producer，最后生成九组三件套共 27 个 ARM64 boot 文件。
输出包括 build receipt、closure manifest、generation identity 和 SHA sidecar。

`covered_actions` 必须在 coverage manifest 中逐项附 source/producer evidence；
worker 不会从 A04 静默推导 A01–A03，也拒绝未知 Action。资格化运行必须使用
`qualification_only=true`、`eligible_for_deploy=false`，不得进入部署 oracle。

final boot worker 必须再带本轮唯一 frozen build ID：

```bash
python3 build_current_boot_generation.py \
  --aosp-root /opt/build-trees/aosp-arm64-d600 \
  --work /opt/build-trees/.work/<fresh-generation> \
  --frozen-build-id <new-frozen-build-id>
```

成功后额外产生标准 `producer-receipt.json`，其 27 个 output role 为
`boot:<filename>`，供 final controller 导入。

## Final generation controller / packer

final controller 的输入固定为：

- 三个直接 artifact：`oh_adapter_bridge`、`apk_installer`、
  `oh_adapter_framework_jar`；
- 九组三件套、共 27 个 `boot:<filename>` artifact；
- coverage manifest；
- 生成上述 artifact 与 target probe 的全部 producer receipts。

所有 receipt 和 coverage 必须使用同一个新的 `frozen_build_id`。artifact 路径、
哈希与字节数只能从 receipt 导入；三项直接 artifact 加 27 项 boot artifact
必须 exact-set。`covered_actions` 与 `coverage_proofs` 也必须 exact-set。

默认 dry-run：

```bash
python3 src/tools/experiments/d600/fn01_provenance/final_generation_controller.py \
  assemble --dry-run \
  --spec <resolved-final-spec.json> \
  --report <final-check.json>
```

即使全部 producer receipt 通过，默认仍输出 `eligible_for_deploy=false`。只有
非 synthetic 输入、每个 Action 均有 passing target-probe receipt，且操作者显式
增加 `--request-eligible`，controller 才允许生成 eligible bundle。该状态仍不等于
`device_verified`，正式 verdict 仍为 `NOT_ISSUED`。

seam proof 齐备后的“一次重烤并封存”入口：

```bash
python3 src/tools/experiments/d600/fn01_provenance/run_final_generation_pipeline.py \
  --boot-worker src/tools/experiments/d600/fn01_provenance/build_current_boot_generation.py \
  --aosp-root /opt/build-trees/aosp-arm64-d600 \
  --boot-work /opt/build-trees/.work/<fresh-generation> \
  --frozen-build-id <new-frozen-build-id> \
  --spec-template <final-spec-template.json> \
  --resolved-spec <evidence>/resolved-final-spec.json \
  --report <evidence>/final-pipeline-report.json \
  --output-dir <evidence>/final-generation \
  --request-eligible
```

template 中新 boot receipt 的 `path` 必须恰好写成
`@FRESH_BOOT_PRODUCER_RECEIPT@`。pipeline 先执行 fresh boot worker，再以其
标准 receipt 的真实 SHA 解开 marker，最后交给 controller 封存。r6
qualification generation ID 与路径均在 controller 中显式拒绝。
