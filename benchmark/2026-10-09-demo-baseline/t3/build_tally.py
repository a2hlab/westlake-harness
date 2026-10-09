import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
WORKSPACES = Path(os.environ.get("WORKSPACES", HERE.parents[3]))
sys.path.insert(0, str(HERE.parent / "t4"))
import summarize


def binding(path, content):
    path = path.resolve()
    value = str(path)
    if value.startswith(str(WORKSPACES) + "/"):
        value = "$WORKSPACES" + value[len(str(WORKSPACES)):]
    return {"path": value, "sha256": hashlib.sha256(content).hexdigest()}


def table(rows):
    lines = ["| Key | Package | Verdict | Batch |", "|---|---|---|---|"]
    for row in rows:
        lines.append(f"| `{row['key']}` | `{row['package']}` | {row['verdict']} | {row['batch'] or 'unsigned'} |")
    return "\n".join(lines)


def markdown(report):
    counts = report["summary"]
    content = counts["tiers"]["shown"]
    lines = ["# Demo t3 mechanical tier tally", "", "## Evidence first", "",
             f"Pinned outer signoff: **{counts['signed_packages']}/{counts['selected_packages']} canonical packages**; "
             f"**{counts['pending_packages']} pending**. This is not stability, reboot or interaction acceptance.", "",
             f"Historical content tier: **{content['signed_lit']}/{content['total']} signed lit/lit_splash**. "
             "Empty-state and error-screen tiers are kept separate even when signed lit.", ""]
    for label, evidence in report["inputs"].items():
        lines.append(f"- {label}: `{evidence['path']}`, SHA256 `{evidence['sha256']}`.")
    lines += ["", "## Tier totals", "", "| Manifest tier | Total | Signed lit/lit_splash | Verdict counts |",
              "|---|---:|---:|---|"]
    for tier in ("shown", "minimal", "errors"):
        values = counts["tiers"][tier]
        distribution = ", ".join(f"{verdict}={number}" for verdict, number in values["verdict_counts"].items() if number)
        lines.append(f"| {tier} | {values['total']} | {values['signed_lit']} | {distribution} |")
    lines += ["", "## Content-tier signed-lit keys", ""]
    lines += [f"- `{key}`" for key in report["first_content"]["signed_lit_keys"]]
    lines += ["", "## Content-tier exceptions", "",
              table([row for row in report["first_content"]["rows"] if not row["signed_lit"]]),
              "", "## All empty-state keys", "", table(report["empty_state"]),
              "", "## Required games", "",
              "These verdicts do not certify gameplay interaction; no interaction evidence was supplied.", "",
              table(report["required_games"]), "", "## Error-screen tier (not in 94/32)", "",
              table(report["error_screen"]), "", "## Unsigned / pending", "",
              "Missing verdict stays pending even if a capture-05 facts row or screenshot already exists.", "",
              table(report["pending"]), "", "## Reproduce", "",
              "```sh", "python3 benchmark/2026-10-09-demo-baseline/t3/build_tally.py", "```", "",
              "The default signoff is read fresh from master. Inputs are pinned and the exact signoff bytes "
              "are saved as outer-signoff-input.json. No timestamps are generated; unchanged inputs give identical bytes.", "",
              "The t4 summarizer's separate t3-tier adapter handles the v1 outer table mechanically; "
              "it does not convert legacy lit into own-content or weaken its stricter stability-v2 checks.", "",
              "## Verification scope", "",
              "Six t3-tally known answers pass. An optional older stability-suite run has nine "
              "preexisting fixture path errors (cycle-1/cycle-1/stable/record.json); the control with "
              "only the new tally adapter omitted has the same nine errors. See evidence/stability-control.json. "
              "No stability PASS is claimed and those unrelated fixtures are not changed.", ""]
    return "\n".join(lines)


def build(manifest_path, signoff_path):
    manifest_bytes = manifest_path.read_bytes()
    signoff_bytes = signoff_path.read_bytes()
    report = summarize.tally_signoff(json.loads(manifest_bytes), json.loads(signoff_bytes))
    report["inputs"] = {"manifest": binding(manifest_path, manifest_bytes),
                       "outer_signoff": binding(signoff_path, signoff_bytes)}
    return report, signoff_bytes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=HERE.parent / "demo-manifest.json")
    parser.add_argument("--signoff", type=Path,
                        default=WORKSPACES / "westlake-harness/benchmark/2026-10-09-demo-baseline/t3-outer-signoff.json")
    parser.add_argument("--out", type=Path, default=HERE)
    args = parser.parse_args()
    report, signoff_bytes = build(args.manifest, args.signoff)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "tally.json").write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    (args.out / "tally.md").write_text(markdown(report))
    (args.out / "outer-signoff-input.json").write_bytes(signoff_bytes)
    print(json.dumps(report["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
