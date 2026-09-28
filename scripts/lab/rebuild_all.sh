#!/bin/bash
# Full board-free rebuild against the westlake checkout in the workspace; every stage is resumable.
set -u
T=/Users/zhaoyue/orca/workspaces/westlake-inputs/tools; O=/home/dspfac/a2hlab/source-closure/verify/out; L=$HOME/a2hlab/logs/build
for s in build_runtime build_phase2a build_phase2b build_phase3a build_phase3b build_phase3c build_phase3d; do
  echo "=== $s $(date +%T)"; bash $T/$s.sh 2>&1 | grep -E "^(OK|FAIL|START)"
done
echo "=== extras $(date +%T)"
[ -e $L/runtime-extras.ok ] || { bash $T/build_extras.sh > $L/runtime-extras.log 2>&1 && touch $L/runtime-extras.ok && echo "OK    runtime-extras" || echo "FAIL  runtime-extras"; }
echo "=== webview $(date +%T)"
if [ ! -e $L/webview-shims-source.ok ]; then
  WESTLAKE_GIT=/home/dspfac/a2hlab/source-closure/verify/westlake WESTLAKE_REV=HEAD bash $T/scratch/build_webview_shims.sh $O/webview-shims-source source > $L/webview-shims-source.log 2>&1 \
   && touch $L/webview-shims-source.ok && echo "OK    webview-shims-source" || echo "FAIL  webview-shims-source"
fi
[ -e $L/webview-shims-source.ok ] && [ ! -e $O/webview-input-source ] && bash $T/assemble_webview_input.sh $O/webview-shims-source $O/webview-input-source > $L/webview-input.log 2>&1 && echo "OK    webview-input-source"
echo "=== ALL_DONE $(date +%T)"
