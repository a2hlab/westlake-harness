#!/usr/bin/env python3
"""
Parse Fn01-Fn03 ATOM_VALIDATION.md + IMPLEMENTATION.yaml and generate
D600 verification runbook, manifest templates, agent script template, and report.
"""
import json
import os
import re
import yaml
from pathlib import Path
from collections import OrderedDict

WORKSPACE = Path("/opt/Bridge")
SPEC_ROOT = WORKSPACE / "docs/spec/atoms"
SRC_ROOT = WORKSPACE / "src/atoms"
EVIDENCE_ATOMS = WORKSPACE / "var/evidence/atoms"
RUNS_DIR = WORKSPACE / "var/evidence/runs"
READINESS = RUNS_DIR / "fn01-fn03-unit-verification-checkpoint-20260725T074537Z/ACTION_READINESS.yaml"

DOMAINS = {
    "Fn01": [f"A{a:02d}" for a in range(1, 14)],
    "Fn02": [f"A{a:02d}" for a in range(1, 19)],
    "Fn03": [f"A{a:02d}" for a in range(1, 11)],
}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_frontmatter(text: str) -> dict:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                return yaml.safe_load(parts[1]) or {}
            except Exception:
                return {}
    return {}


def extract_tables(text: str):
    """Extract markdown tables as list of (caption_or_first_header, rows)."""
    tables = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "|" in line and "---" in line and "|" in lines[i - 1] if i > 0 else False:
            header_line = lines[i - 1].strip()
            headers = [h.strip() for h in header_line.split("|") if h.strip()]
            rows = []
            i += 1
            while i < len(lines):
                row_line = lines[i].strip()
                if not row_line.startswith("|"):
                    break
                cells = [c.strip() for c in row_line.split("|")]
                cells = [c for c in cells if c != ""]
                if len(cells) >= len(headers):
                    rows.append(OrderedDict(zip(headers, cells)))
                i += 1
            tables.append((headers, rows))
            continue
        i += 1
    return tables


def parse_validation(text: str, action_id: str) -> dict:
    fm = parse_frontmatter(text)
    tables = extract_tables(text)
    data = {
        "atom_id": fm.get("atom_id", action_id),
        "title": fm.get("title", ""),
        "alias": fm.get("alias", ""),
        "validation_kind": fm.get("validation_kind", ""),
        "stimuli": [],
        "observables": [],
        "oracles": [],
        "preconditions": [],
        "assertions": [],
        "evidence_outputs": [],
        "failure_semantics": [],
        "section_texts": {},
    }

    # Find section texts
    sections = re.split(r"^##+\s+", text, flags=re.MULTILINE)
    for sec in sections:
        first_line = sec.splitlines()[0] if sec else ""
        key = first_line.strip().split()[0] if first_line else ""
        data["section_texts"][key] = sec

    for headers, rows in tables:
        h0 = headers[0].lower() if headers else ""
        if "输入" in h0 or "stimuli" in h0 or "编号" in h0 and "输入" in " ".join(headers):
            for r in rows:
                num = r.get("编号", "")
                inp = r.get("输入", "")
                typ = r.get("类型", "")
                note = r.get("备注", "")
                if num or inp:
                    data["stimuli"].append({"id": num, "input": inp, "type": typ, "note": note})
        elif "输出" in h0 or "observables" in h0:
            for r in rows:
                num = r.get("编号", "")
                out = r.get("输出", "")
                judge = r.get("判定方式", "")
                note = r.get("备注", "")
                if num or out:
                    data["observables"].append({"id": num, "output": out, "judge": judge, "note": note})
        elif "场景" in h0 or "oracle" in h0 or "条件" in h0:
            for r in rows:
                scene = r.get("场景", "")
                cond = r.get("条件", "")
                verdict = r.get("verdict", "")
                if scene or cond:
                    data["oracles"].append({"scene": scene, "condition": cond, "verdict": verdict})
        elif "失败模式" in h0:
            for r in rows:
                mode = r.get("失败模式", "")
                expected = r.get("预期行为", "")
                diag = r.get("诊断信息", "")
                if mode:
                    data["failure_semantics"].append({"mode": mode, "expected": expected, "diagnostic": diag})
        elif "证据" in h0 or "文件名模式" in h0:
            for r in rows:
                name = r.get("证据", "")
                pattern = r.get("文件名模式", "")
                note = r.get("说明", "")
                if name or pattern:
                    data["evidence_outputs"].append({"name": name, "pattern": pattern, "note": note})

    # Parse preconditions from numbered list in section 四
    pre_match = re.search(r"##\s+四、前置条件(.*?)##", text, re.DOTALL)
    if pre_match:
        pre_text = pre_match.group(1)
        for line in pre_text.splitlines():
            m = re.match(r"^\s*\d+\.\s+(.*)$", line)
            if m:
                data["preconditions"].append(m.group(1).strip())

    # Parse assertions from checklist in section 六
    assert_match = re.search(r"##\s+六、.*?验收断言(.*?)##", text, re.DOTALL)
    if assert_match:
        for line in assert_match.group(1).splitlines():
            m = re.match(r"^\s*-\s+\[\s*\]\s+(.*)$", line)
            if m:
                data["assertions"].append(m.group(1).strip())

    return data


def parse_implementation(text: str, action_id: str) -> dict:
    try:
        data = yaml.safe_load(text) or {}
    except Exception:
        data = {}
    return {
        "action_id": data.get("action_id", action_id),
        "title": data.get("title", ""),
        "handoff_status": data.get("handoff_status", ""),
        "source_refs": data.get("source_refs", []),
        "build_artifacts": data.get("build_artifacts", {}),
        "test_fixtures": data.get("test_fixtures", []),
        "deploy_scripts": data.get("deploy_scripts", []),
        "verification_runner": data.get("verification_runner", {}),
        "blockers": data.get("blockers", []),
        "notes": data.get("notes", ""),
    }


def classify_case(scene: str) -> str:
    s = scene.lower()
    if "正常" in scene or "positive" in s or "p" in s:
        return "positive"
    elif "负控" in scene or "negative" in s or "n" in s:
        return "negative"
    elif "失败" in scene or "failure" in s or "f" in s:
        return "failure"
    return "unknown"


def case_type_letter(ct: str) -> str:
    return {"positive": "P", "negative": "N", "failure": "F"}.get(ct, "X")


def main():
    with open(READINESS, "r", encoding="utf-8") as f:
        readiness = yaml.safe_load(f)

    actions = readiness.get("actions", {})

    # Collect parsed data
    parsed = {}
    for domain, ids in DOMAINS.items():
        for aid in ids:
            action_id = f"{domain}.{aid}"
            spec_path = SPEC_ROOT / domain / aid / "ATOM_VALIDATION.md"
            impl_path = SRC_ROOT / domain / aid / "IMPLEMENTATION.yaml"
            spec_text = read_text(spec_path)
            impl_text = read_text(impl_path)
            parsed[action_id] = {
                "validation": parse_validation(spec_text, action_id),
                "implementation": parse_implementation(impl_text, action_id),
                "readiness": actions.get(action_id, {}),
            }

    # Generate runbook
    runbook = {
        "schema_version": "1.0",
        "kind": "D600_VERIFY_RUNBOOK",
        "runbook_id": "fn01-fn03-d600-verify-runbook-20260725-r1",
        "generated_at": "2026-07-25T11:35:20Z",
        "device_target": "D600",
        "scope": {
            "domains": ["Fn01", "Fn02", "Fn03"],
            "action_count": 41,
            "case_count": 0,
        },
        "notes": [
            "This is a PREPARATION artifact. No formal verdicts are written here.",
            "Each case must be executed by an independent verifier on D600.",
            "Cases marked SPEC_GAP lack a frozen canonical contract and cannot yield a formal verdict yet.",
        ],
        "cases": [],
    }

    spec_gaps = []

    for action_id in sorted(parsed.keys()):
        rec = parsed[action_id]
        val = rec["validation"]
        impl = rec["implementation"]
        rd = rec["readiness"]
        title = val.get("title") or impl.get("title") or rd.get("title", "")
        oracles = val.get("oracles", [])

        # Determine readiness per case type
        cases_state = rd.get("cases", {}) if isinstance(rd, dict) else {}
        pos_state = cases_state.get("positive", "MISSING")
        neg_state = cases_state.get("negative", "MISSING")
        fail_state = cases_state.get("failure", "MISSING")

        # If no oracles, everything is SPEC_GAP
        has_oracles = len(oracles) > 0 and any(o.get("scene") for o in oracles)

        # Build explicit P/N/F cases from oracles where possible
        case_entries = []
        if has_oracles:
            for o in oracles:
                scene = o.get("scene", "").strip()
                cond = o.get("condition", "").strip()
                verdict = o.get("verdict", "").strip()
                if not scene and not cond:
                    continue
                ct = classify_case(scene)
                if ct == "unknown":
                    continue
                prefix = case_type_letter(ct)
                # Extract case number if present, else assign sequential
                m = re.search(r"[PNF](\d+)", scene)
                cid_num = m.group(1) if m else str(len([c for c in case_entries if c["case_type"] == ct]) + 1)
                case_id = f"{prefix}{cid_num}"
                case_entries.append({
                    "case_id": case_id,
                    "case_type": ct,
                    "title": scene,
                    "oracle": cond,
                    "expected_verdict": verdict,
                })

        # If no usable oracle entries, fall back to generic P1/N1/F1 from readiness states
        if not case_entries:
            for ct, state in [("positive", pos_state), ("negative", neg_state), ("failure", fail_state)]:
                if state not in ("MISSING",):
                    case_id = f"{case_type_letter(ct)}1"
                    case_entries.append({
                        "case_id": case_id,
                        "case_type": ct,
                        "title": f"{ct.capitalize()} case (unfrozen candidate)",
                        "oracle": "Canonical oracle not frozen.",
                        "expected_verdict": "SPEC_GAP",
                    })

        # If still empty, emit one SPEC_GAP placeholder
        if not case_entries:
            case_entries.append({
                "case_id": "P1",
                "case_type": "positive",
                "title": "Canonical positive case not frozen",
                "oracle": "No canonical oracle defined.",
                "expected_verdict": "SPEC_GAP",
            })

        # Mark SPEC_GAP where appropriate
        overall_gap = rd.get("readiness_verdict", "SPEC_GAP") == "SPEC_GAP" or not has_oracles
        gap_reasons = []
        if overall_gap:
            gap_reasons.extend(rd.get("blockers", []))
            if not has_oracles:
                gap_reasons.append("ATOM_VALIDATION.md lacks frozen P/N/F oracles.")
            if impl.get("handoff_status", "") != "READY_FOR_VERIFY":
                gap_reasons.append(f"IMPLEMENTATION.yaml handoff_status={impl.get('handoff_status','')} != READY_FOR_VERIFY.")

        if overall_gap:
            spec_gaps.append({
                "action_id": action_id,
                "title": title,
                "reasons": list(OrderedDict.fromkeys(gap_reasons)),
            })

        # Stimulus command template
        runner = impl.get("verification_runner", {})
        runner_cmd = runner.get("command", "")
        if not runner_cmd:
            runner_cmd = "hdc -t <SERIAL> shell <action-specific probe>"

        # Build per-case runbook entries
        for idx, ce in enumerate(case_entries):
            is_gap = overall_gap or ce.get("expected_verdict") == "SPEC_GAP"
            stimulus = runner_cmd
            case_type = ce["case_type"]
            if case_type == "negative" and "bm install" in stimulus and "-p" in stimulus:
                stimulus = stimulus.replace("<APK_PATH>", "<MALFORMED_APK_PATH>")
            elif case_type == "failure" and "bm install" in stimulus and "-p" in stimulus:
                stimulus = stimulus.replace("<APK_PATH>", "<NONEXISTENT_APK_PATH>")

            expected_ui_summary = f"{action_id} {ce['case_id']}: {ce['title']}"
            if is_gap:
                expected_ui_summary = f"[SPEC_GAP] {expected_ui_summary}"

            runbook["cases"].append({
                "action_id": action_id,
                "action_title": title,
                "case_id": ce["case_id"],
                "case_type": ce["case_type"],
                "title": ce["title"],
                "stimulus": stimulus,
                "oracle": ce["oracle"],
                "expected_ui_summary": expected_ui_summary,
                "expected_verdict": "SPEC_GAP" if is_gap else ce.get("expected_verdict", "PASS"),
                "dependencies": val.get("preconditions", []),
                "human_button_confirm_required": True,
                "human_confirm_file": f"/data/local/tmp/aonb_confirm/<RUN_ID>/{action_id}/{ce['case_id']}.confirmed",
                "spec_gap": is_gap,
                "spec_gap_reasons": gap_reasons if is_gap else [],
                "evidence_outputs": [e.get("pattern") or e.get("name") for e in val.get("evidence_outputs", [])],
                "readiness_state": {
                    "positive": pos_state,
                    "negative": neg_state,
                    "failure": fail_state,
                    "handoff_status": impl.get("handoff_status", ""),
                },
            })

    runbook["scope"]["case_count"] = len(runbook["cases"])

    # Write runbook
    runbook_path = RUNS_DIR / "fn01-fn03-verify-runbook.yaml"
    with open(runbook_path, "w", encoding="utf-8") as f:
        yaml.dump(runbook, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    # Write per-Action manifest templates
    manifest_paths = []
    for action_id in sorted(parsed.keys()):
        rec = parsed[action_id]
        val = rec["validation"]
        runs_dir = EVIDENCE_ATOMS / action_id.replace(".", "/") / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        template = {
            "schema_version": "1.0",
            "kind": "ACTION_EVIDENCE_MANIFEST_TEMPLATE",
            "template_id": f"{action_id}-manifest-template",
            "action_id": action_id,
            "action_title": val.get("title") or rec["implementation"].get("title", ""),
            "run_id": "<RUN_ID>",
            "device_serial": "<DEVICE_SERIAL>",
            "verifier": "<VERIFIER>",
            "timestamps": {
                "run_started_utc": "<TIMESTAMP>",
                "run_completed_utc": "<TIMESTAMP>",
                "button_confirmed_utc": "<TIMESTAMP>",
            },
            "cases": [],
            "log_files": [
                {"role": "hilog", "path": f"var/evidence/atoms/{action_id}/runs/<RUN_ID>/hilog.txt", "sha256": "<SHA256>"},
                {"role": "process_samples", "path": f"var/evidence/atoms/{action_id}/runs/<RUN_ID>/process-samples.txt", "sha256": "<SHA256>"},
                {"role": "stimulus", "path": f"var/evidence/atoms/{action_id}/runs/<RUN_ID>/stimulus.json", "sha256": "<SHA256>"},
                {"role": "observable", "path": f"var/evidence/atoms/{action_id}/runs/<RUN_ID>/observable.json", "sha256": "<SHA256>"},
                {"role": "bm_dump", "path": f"var/evidence/atoms/{action_id}/runs/<RUN_ID>/bm-dump.txt", "sha256": "<SHA256>"},
                {"role": "verdict", "path": f"var/evidence/atoms/{action_id}/runs/<RUN_ID>/verdict.md", "sha256": "<SHA256>"},
            ],
            "human_confirm_file": f"var/evidence/atoms/{action_id}/runs/<RUN_ID>/human_confirm/<CASE_ID>.confirmed",
            "verdict": "<FORMAL_VERDICT_TO_BE_ISSUED_BY_INDEPENDENT_VERIFIER>",
            "verdict_note": "Do not fill verdict in this template. It is recorded in the immutable Action evidence run.",
        }
        for case in runbook["cases"]:
            if case["action_id"] != action_id:
                continue
            template["cases"].append({
                "case_id": case["case_id"],
                "case_type": case["case_type"],
                "title": case["title"],
                "stimulus": case["stimulus"],
                "oracle": case["oracle"],
                "human_confirm_file": f"var/evidence/atoms/{action_id}/runs/<RUN_ID>/human_confirm/{case['case_id']}.confirmed",
                "verdict": "<TO_BE_DETERMINED>",
            })
        manifest_path = runs_dir / "TEMPLATE_MANIFEST.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        manifest_paths.append(str(manifest_path))

    # Write agent script template
    script_path = RUNS_DIR / "run_fn01_fn03_on_d600.template.sh"
    script = r"""#!/bin/bash
# D600 Verification Agent Script Template
# Scope: Fn01-Fn03 (41 Actions) P/N/F cases with human button confirmation
# IMPORTANT: This is a TEMPLATE. Do not run verdict issuance automatically.
#
# Usage:
#   export SERIAL=5583f5be00000000000000000323012c
#   export RUN_ID=20260725T120000Z-d600-${SERIAL}-r1
#   export VERIFIER="independent-verifier"
#   bash run_fn01_fn03_on_d600.template.sh <runbook.yaml>

set -euo pipefail

RUNBOOK="${1:-/opt/Bridge/evidence/runs/fn01-fn03-verify-runbook.yaml}"
SERIAL="${SERIAL:-<DEVICE_SERIAL>}"
RUN_ID="${RUN_ID:-<RUN_ID>}"
VERIFIER="${VERIFIER:-<VERIFIER>}"
CONFIRM_PKG="com.example.aonb.confirm"
CONFIRM_ABILITY="ConfirmActivity"
CONFIRM_DIR="/data/local/tmp/aonb_confirm/${RUN_ID}"

if [[ "$SERIAL" == "<DEVICE_SERIAL>" ]]; then
  echo "ERROR: Set SERIAL to the D600 device serial." >&2
  exit 1
fi

# Helper: run a case stimulus
run_stimulus() {
  local cmd="$1"
  # Substitute placeholders
  cmd="${cmd//<SERIAL>/$SERIAL}"
  cmd="${cmd//<RUN_ID>/$RUN_ID}"
  # TODO: add other substitutions (APK_PATH, PACKAGE, etc.)
  echo "[STIMULUS] $cmd"
  eval "$cmd" || true  # Do not abort; failure may be expected in N/F cases
}

# Helper: launch confirmation activity and poll
confirm_case() {
  local action="$1"
  local case_id="$2"
  local summary="$3"
  local confirm_path="${CONFIRM_DIR}/${action}/${case_id}.confirmed"

  echo "[UI] Launching confirmation activity for ${action} ${case_id}"
  hdc -t "$SERIAL" shell aa start \
    -a "${CONFIRM_PKG}.${CONFIRM_ABILITY}" \
    -b "$CONFIRM_PKG" \
    --ez confirmed false \
    --es action "$action" \
    --es case "$case_id" \
    --es summary "$summary" \
    --es run_id "$RUN_ID"

  # Poll up to 5 minutes (60 * 5s)
  local confirmed=0
  for i in {1..60}; do
    if hdc -t "$SERIAL" shell "test -f ${confirm_path}"; then
      confirmed=1
      echo "[UI] Confirmed: ${action} ${case_id}"
      hdc -t "$SERIAL" shell "cat ${confirm_path}"
      break
    fi
    sleep 5
  done

  if [[ "$confirmed" -eq 0 ]]; then
    echo "[UI] TIMEOUT waiting for confirmation: ${action} ${case_id}" >&2
  fi
}

# Helper: pull logs to evidence directory
pull_logs() {
  local action="$1"
  local case_id="$2"
  local dest="/opt/Bridge/evidence/atoms/${action}/runs/${RUN_ID}"
  mkdir -p "$dest/human_confirm"

  # Pull full hilog
  hdc -t "$SERIAL" shell hilog > "${dest}/hilog-${case_id}.txt" || true

  # Pull confirmation file if present
  hdc -t "$SERIAL" file recv \
    "${CONFIRM_DIR}/${action}/${case_id}.confirmed" \
    "${dest}/human_confirm/${case_id}.confirmed" || true

  # Pull bm dump for package-related cases
  if [[ "$action" == Fn01.* ]]; then
    hdc -t "$SERIAL" shell "bm dump -n com.example.helloworld" > "${dest}/bm-dump-${case_id}.txt" || true
  fi

  echo "[EVIDENCE] Pulled logs to ${dest}"
}

# Helper: update STATUS.yaml (template only - do NOT write verdict here)
update_status_template() {
  local action="$1"
  local case_id="$2"
  local status_file="/opt/Bridge/evidence/atoms/${action}/runs/${RUN_ID}/STATUS.yaml"
  mkdir -p "$(dirname "$status_file")"
  cat >> "$status_file" <<EOF
# TEMPLATE NOTE: Formal verdict must be issued by independent verifier after raw evidence review.
# ${RUN_ID} ${action} ${case_id}
#   - stimulus_executed: true
#   - confirmation_polled: true
#   - human_button_confirmed: <true|false>
#   - proposed_verdict: <PASS|FAIL|BLOCK|SPEC_GAP>
#   - proposed_by: agent_automation
#   - formal_verdict: NOT_ISSUED
EOF
}

# Main loop over runbook cases
# NOTE: This uses yq or python to parse YAML. Install yq or ensure python+yaml is available.
if ! command -v yq >/dev/null 2>&1; then
  echo "WARNING: yq not found; falling back to Python yaml parsing." >&2
fi

# Extract case list using Python for portability
RUNBOOK_CASES=$(mktemp)
python3 - <<PYEOF > "$RUNBOOK_CASES"
import yaml, sys
with open("$RUNBOOK") as f:
    rb = yaml.safe_load(f)
for c in rb.get("cases", []):
    print("\t".join([
        c["action_id"], c["case_id"], c["case_type"], c["title"],
        c["stimulus"], c["oracle"], c["expected_ui_summary"],
        str(c.get("spec_gap", False))
    ]))
PYEOF

while IFS=$'\t' read -r action case_id case_type title stimulus oracle summary gap; do
  echo "======================================"
  echo "Action: ${action} | Case: ${case_id} | Type: ${case_type}"
  echo "Title: ${title}"

  if [[ "$gap" == "True" ]]; then
    echo "[SKIP] SPEC_GAP case; recording as gap without issuing verdict."
    update_status_template "$action" "$case_id"
    continue
  fi

  run_stimulus "$stimulus"
  confirm_case "$action" "$case_id" "$summary"
  pull_logs "$action" "$case_id"
  update_status_template "$action" "$case_id"
done < "$RUNBOOK_CASES"

rm -f "$RUNBOOK_CASES"

echo "[DONE] Run ${RUN_ID} completed. Review raw evidence before issuing formal verdicts."
"""
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)
    os.chmod(script_path, 0o755)

    # Write report
    ready_count = sum(1 for a in actions.values() if a.get("readiness_verdict") == "READY")
    spec_gap_count = sum(1 for a in actions.values() if a.get("readiness_verdict") == "SPEC_GAP")
    report = f"""# Verify Lane Report: Fn01-Fn03 D600 Runbook Preparation

**Report ID:** `verify-runbook-lane-report-20260725-r1`
**Generated:** 2026-07-25T11:35:20Z
**Scope:** Fn01 (13 Actions) + Fn02 (18 Actions) + Fn03 (10 Actions) = 41 Actions
**Device Target:** D600
**Lane:** Verify

## Summary

- **Runbook cases generated:** {len(runbook['cases'])}
- **Actions in scope:** 41
- **Actions marked READY:** {ready_count}
- **Actions marked SPEC_GAP:** {spec_gap_count}
- **Formal verdicts issued:** 0 (preparation stage)
- **Artifacts produced:**
  - `/opt/Bridge/evidence/runs/fn01-fn03-verify-runbook.yaml`
  - `/opt/Bridge/evidence/runs/run_fn01_fn03_on_d600.template.sh`
  - `/opt/Bridge/evidence/atoms/<Action>/runs/TEMPLATE_MANIFEST.json` (41 files)

## Method

1. Read `ACTION_READINESS.yaml` for current per-Action readiness state.
2. Read each `docs/spec/atoms/<Action>/ATOM_VALIDATION.md` to extract stimuli, observables, oracles, preconditions, and evidence outputs.
3. Read each `src/atoms/<Action>/IMPLEMENTATION.yaml` to extract runner commands, test fixtures, deploy scripts, and handoff status.
4. For each Action, generate P/N/F runbook entries where a canonical oracle exists; otherwise mark the case `SPEC_GAP`.
5. Generate a per-Action `TEMPLATE_MANIFEST.json` with placeholders for run_id, device_serial, verifier, timestamps, log files, and verdict.
6. Generate a D600 agent shell template that loops over the runbook, executes stimuli, launches the confirmation Activity, polls the confirmation file, pulls logs, and appends a verdict-free STATUS.yaml template note.

## SPEC_GAP Findings

All 41 Actions are currently in `SPEC_GAP` readiness state per `ACTION_READINESS.yaml`.

**Note on IMPLEMENTATION.yaml:** The readiness audit blockers state that `IMPLEMENTATION.yaml` is absent; however, draft `IMPLEMENTATION.yaml` files were found under `src/atoms/Fn01..Fn03/Ayy/` and were used to build this runbook. They are all marked `handoff_status: DRAFT_PENDING_BUILD_VERIFY` rather than `READY_FOR_VERIFY`, so the SPEC_GAP conclusion remains valid.

Reasons include:

"""
    for g in spec_gaps:
        report += f"\n### {g['action_id']} — {g['title']}\n\n"
        for r in g["reasons"]:
            report += f"- {r}\n"

    report += """
## Runbook Structure

The runbook contains one entry per Action × case with the following fields:

- `action_id`, `action_title`
- `case_id` (e.g., P1, N1, F1)
- `case_type` (positive / negative / failure)
- `title`, `stimulus`, `oracle`, `expected_ui_summary`
- `dependencies` (preconditions such as TRULY_COLD state or prior install)
- `human_button_confirm_required: true`
- `human_confirm_file` path on D600
- `spec_gap` boolean and `spec_gap_reasons`
- `readiness_state` snapshot

## Agent Script Behavior

`run_fn01_fn03_on_d600.template.sh` is a template. It:

1. Reads the runbook YAML.
2. For each case:
   - Executes the stimulus command (with placeholder substitution).
   - Launches `com.example.aonb.confirm.ConfirmActivity` with action/case/summary/run_id extras.
   - Polls `/data/local/tmp/aonb_confirm/<RUN_ID>/<action>/<case>.confirmed` for up to 5 minutes.
   - Pulls hilog, bm-dump, and the confirmation file into `var/evidence/atoms/<action>/runs/<RUN_ID>/`.
   - Appends a verdict-free template note to `STATUS.yaml`.
3. Skips cases marked `spec_gap: true` without issuing a verdict.

## Next Steps

1. Freeze canonical P/N/F oracles in `ATOM_VALIDATION.md` for each Action.
2. Obtain `READY_FOR_VERIFY` IMPLEMENTATION.yaml handoffs with hash-bound build artifacts.
3. Build and deploy the `com.example.aonb.confirm` HAP/APK to D600.
4. Assign an independent verifier and run the agent script on a real D600.
5. After raw evidence review, the independent verifier issues formal PASS/FAIL/BLOCK verdicts and updates `MANIFEST.yaml`/`verdict.md`.

## Constraints Observed

- No adapter source code was modified.
- No formal verdicts were written to `STATUS.yaml` in this preparation step.
- All `SPEC_GAP` cases are explicitly flagged with reasons.
"""

    report_path = RUNS_DIR / "verify-runbook-lane-report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Wrote runbook: {runbook_path}")
    print(f"Wrote script template: {script_path}")
    print(f"Wrote report: {report_path}")
    print(f"Wrote {len(manifest_paths)} manifest templates")
    print(f"Total runbook cases: {len(runbook['cases'])}")
    print(f"SPEC_GAP actions: {spec_gap_count}")


if __name__ == "__main__":
    main()
