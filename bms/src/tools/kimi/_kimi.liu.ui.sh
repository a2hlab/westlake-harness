#!/bin/bash
# _kimi.liu.ui.sh
# UI lane: build the D600 manual button-confirmation HAP.
# Run this in its own terminal window for isolation.
set -euo pipefail

WORKDIR="/opt/Bridge"
KIMI_BIN="/Users/alexyang/.kimi-code/bin/kimi"
LOG="${WORKDIR}/evidence/runs/_kimi.liu.ui.log"
REPORT="${WORKDIR}/evidence/runs/ui-confirm-hap-lane-report.md"

mkdir -p "$(dirname "$LOG")"

cd "$WORKDIR"

exec > >(tee -a "$LOG") 2>&1

"${KIMI_BIN}" --auto -p "$(cat <<'PROMPT'
You are the UI lane agent for the Bridge Fn01-Fn03 verification goal.

Objective: create a minimal OpenHarmony HAP named `com.example.aonb.confirm` that shows a full-screen button on D600 for manual test confirmation.

Protocol document: /opt/Bridge/docs/atoms/UI_CONFIRMATION_PROTOCOL.md

Requirements:
- Bundle name: com.example.aonb.confirm
- Ability/Activity: ConfirmActivity (or ConfirmAbility on OH)
- Launch command: aa start -a com.example.aonb.confirm.ConfirmActivity -b com.example.aonb.confirm --es action Fn01.A01 --es case P1 --es runId <run-id> --es summary "..."
- UI must display: Action ID, case type (P/N/F), summary, and a single "确认收到" button.
- On button press, create directory /data/local/tmp/aonb_confirm/<run-id>/<action>/ and write file <case>.confirmed with YAML content:
    confirmed_at_utc: <ISO-8601 UTC>
    action_id: <action>
    case_id: <case>
    device_serial: <serial>
    run_id: <run-id>
    confirmed_by: human_button_press
  Device serial can be obtained from environment/system properties or passed as an extra.

Tasks:
1. Find the closest existing HelloWorld HAP template in /opt/Bridge/src/adapter/app/, /opt/Bridge/APKS/, or /opt/Bridge/src/AlexBridge/app/.
2. Create a new minimal project under /opt/Bridge/src/adapter/app/aonb_confirm/ (or a location that does not pollute existing apps). Include source files, module.json5, and build scripts if applicable.
3. Build the HAP. Prefer building on AlexPC (ssh AlexPC) using the OH SDK/Deveco tool chain; if the local Mac can build it, explain the tool chain used.
4. Output the HAP path, install command, and a sample launch command.
5. Record design, build steps, and any blockers in /opt/Bridge/evidence/runs/ui-confirm-hap-lane-report.md.

Constraints:
- Do not modify existing HelloWorld, adapter core, or verification code.
- Keep the HAP minimal and single-purpose.
- If you cannot complete, clearly state the blocker and the next step a human must take.
PROMPT
)"
