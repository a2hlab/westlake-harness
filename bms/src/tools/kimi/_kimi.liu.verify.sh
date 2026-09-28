#!/bin/bash
# _kimi.liu.verify.sh
# Verify lane: prepare the 41 Action P/N/F runbook and evidence manifests.
# Run this in its own terminal window for isolation.
set -euo pipefail

WORKDIR="/opt/Bridge"
KIMI_BIN="/Users/alexyang/.kimi-code/bin/kimi"
LOG="${WORKDIR}/evidence/runs/_kimi.liu.verify.log"
REPORT="${WORKDIR}/evidence/runs/verify-runbook-lane-report.md"

mkdir -p "$(dirname "$LOG")"

cd "$WORKDIR"

exec > >(tee -a "$LOG") 2>&1

"${KIMI_BIN}" --auto -p "$(cat <<'PROMPT'
You are the Verify lane agent for the Bridge Fn01-Fn03 verification goal.

Objective: prepare an executable runbook and evidence manifest templates for all 41 stable Actions (Fn01.A01-A13, Fn02.A01-A18, Fn03.A01-A10) so that a final independent verifier can run them on D600 and record verdicts.

Inputs to read:
- /opt/Bridge/spec/atoms/Fn01/A01..A13/ATOM_VALIDATION.md
- /opt/Bridge/spec/atoms/Fn02/A01..A18/ATOM_VALIDATION.md
- /opt/Bridge/spec/atoms/Fn03/A01..A10/ATOM_VALIDATION.md
- /opt/Bridge/src/atoms/Fn01..Fn03/Ayy/IMPLEMENTATION.yaml
- /opt/Bridge/evidence/runs/fn01-fn03-unit-verification-checkpoint-20260725T074537Z/ACTION_READINESS.yaml
- /opt/Bridge/docs/atoms/UI_CONFIRMATION_PROTOCOL.md

Tasks:
1. For each Action, extract its title, positive/negative/failure case titles, and oracles from ATOM_VALIDATION.md and IMPLEMENTATION.yaml.
2. Generate /opt/Bridge/evidence/runs/fn01-fn03-verify-runbook.yaml containing an ordered list of Action-case entries. Each entry must include:
   - action_id, case_id (e.g., P1, N1, F1), case_type, title
   - stimulus: exact hdc/aa shell commands to execute
   - oracle: how to decide PASS/FAIL/BLOCK
   - expected_ui_summary: one-line text to show on the D600 confirmation screen
   - dependencies: prerequisite cases or installed packages
   - readiness flag: READY or SPEC_GAP with reason
3. For each Action generate /opt/Bridge/evidence/atoms/<Action>/runs/TEMPLATE_MANIFEST.json with fields: run_id, device_serial, action_id, case_id, verifier, timestamps, log_files, human_confirm_file, verdict.
4. Create /opt/Bridge/evidence/runs/run_fn01_fn03_on_d600.template.sh, a shell script template that:
   - Loops over the runbook entries
   - Executes the stimulus
   - Launches the UI confirmation Activity (aa start -a com.example.aonb.confirm.ConfirmActivity ...)
   - Polls /data/local/tmp/aonb_confirm/<run-id>/<action>/<case>.confirmed
   - Pulls hilog and relevant logs into var/evidence/atoms/<action>/runs/<run-id>/
   - Does NOT write verdicts to STATUS.yaml (only templates/comments)
5. Write a summary and any SPEC_GAP findings to /opt/Bridge/evidence/runs/verify-runbook-lane-report.md.

Constraints:
- Do not issue formal Action verdicts yet.
- Do not modify adapter source code.
- If a case cannot be defined, mark it SPEC_GAP and explain why.
PROMPT
)"
