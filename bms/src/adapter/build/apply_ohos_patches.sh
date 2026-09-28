#!/bin/bash
# ============================================================================
# apply_ohos_patches.sh — OH 源 .patch 应用(sourceable 函数库)
# ============================================================================
# 仅作为兼容入口文件：canonical wrapper 脚本统一放在 inner/ 版本，避免列表/逻辑分裂。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/inner/apply_ohos_patches.sh"

