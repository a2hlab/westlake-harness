#!/usr/bin/env bash
# 5ea34a45 probe_source_app.py launch config (the exact set claude board-runner used for LocalSend/X).
# claude-3: copy the command, change --app <KEY> + --app-input + --out per app, iterate.
# Base: framework-2 = a2hlab-framework-cab462ff (passed=True files=306); host = verify signed-host.
S5=5ea34a4500000000000000001123012c
W=/home/dspfac/a2hlab/source-closure/verify              # --workspace
# run from the manifest dir on VM (orb -m a2hlab):  cd ~/a2hlab/manifest && python3 tools/probe_source_app.py \
#   --workspace              $W
#   --westlake-source        $W/westlake
#   --framework-report       ~/a2hlab/board/$S5/framework-2/device-report.json
#   --app-input              ~/a2hlab/app-inputs/<KEY>
#   --app                    <KEY>
#   --hdc                    /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh
#   --serial                 $S5
#   --out                    ~/a2hlab/board/$S5/<TAG>/<KEY>
#   --host-build             $W/out/signed-host
#   --webview-input          $W/out/webview-input-source
# NOTE: --source-webview-build was NOT needed/used (probe ran fine without it; it's optional).
# Concrete example (X), verbatim:
example() {
cd ~/a2hlab/manifest && python3 tools/probe_source_app.py \
  --workspace "$W" --westlake-source "$W/westlake" \
  --framework-report ~/a2hlab/board/$S5/framework-2/device-report.json \
  --app-input ~/a2hlab/app-inputs/x --app x \
  --hdc /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh --serial $S5 \
  --out ~/a2hlab/board/$S5/sweep/x \
  --host-build "$W/out/signed-host" --webview-input "$W/out/webview-input-source"
}
