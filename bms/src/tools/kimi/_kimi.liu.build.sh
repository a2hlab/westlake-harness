#!/bin/bash
# _kimi.liu.build.sh
# Build lane: resolve AlexPC OH patch drift and produce stock Route A generation.
# Run this in its own terminal window for isolation.
set -euo pipefail

WORKDIR="/opt/Bridge"
KIMI_BIN="/Users/alexyang/.kimi-code/bin/kimi"
LOG="${WORKDIR}/evidence/runs/_kimi.liu.build.log"
REPORT="${WORKDIR}/evidence/runs/alexpc-build-lane-report.md"

mkdir -p "$(dirname "$LOG")"

cd "$WORKDIR"

exec > >(tee -a "$LOG") 2>&1

"${KIMI_BIN}" --auto -p "$(cat <<'PROMPT'
You are the Build lane agent for the Bridge Fn01-Fn03 verification goal.

Objective: build a deployable stock Route A generation on AlexPC so that HelloWorld can run on D600.

Authoritative sources:
- Adapter source of truth: local Mac /opt/Bridge/src/adapter/
- AOSP source: AlexPC:/opt/build-trees/aosp-arm64-d600
- OpenHarmony source: AlexPC:/opt/build-trees/oh610_lts_source
- Build host: AlexPC (SSH via ~/.ssh/config Host AlexPC, port 22, user alexyang)

Previously, running `bash build/build_all.sh --dry-run` on AlexPC failed in `build_ohos_service.sh` with:
  [WARN] full-product ets2abc_config.gni drift: expected=... actual=...
  [ERROR] Phase 0: OH patch application failed; refusing a mixed-generation build

Tasks:
1. SSH to AlexPC and back up /opt/build-trees/adapter/ state.
2. Sync local /opt/Bridge/src/adapter/ to AlexPC /opt/build-trees/adapter/, preserving out/, prebuilts/, and other build artifacts. List files that will be overwritten before doing so.
3. On AlexPC, run `export OH_ROOT=/opt/build-trees/oh610_lts_source && export AOSP_ROOT=/opt/build-trees/aosp-arm64-d600 && cd /opt/build-trees/adapter && bash build/build_all.sh --dry-run`. Capture full output.
4. If the ets2abc_config.gni drift recurs, inspect `build/apply_ohos_patches.sh` or the relevant gate to determine whether the OH tree was manually modified or the adapter patches need updating. Try `bash build/build_ohos_service.sh --no-apply` only if the patches are already applied.
5. If the drift cannot be quickly resolved, attempt to build the adapter-specific artifacts directly (`build/build_adapter.sh`, `build/build_appspawn_x.sh`) and reuse existing `out/aosp_lib64/` and `out/adapter/` artifacts to produce the missing stock Route A generation (`appspawn-x-stock` or equivalent).
6. Record the exact commands run, their outputs, produced artifact paths, SHA-256 hashes, and any remaining blockers in /opt/Bridge/evidence/runs/alexpc-build-lane-report.md.

Constraints:
- Do not modify /opt/Bridge/src/adapter/ or any other local source outside of var/evidence/report files.
- Preserve AlexPC build outputs and evidence.
- If you cannot complete, clearly state the blocker and the next step a human must take.
PROMPT
)"
