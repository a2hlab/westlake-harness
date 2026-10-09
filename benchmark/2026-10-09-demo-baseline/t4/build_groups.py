import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
WORKSPACES = Path(os.environ.get("WORKSPACES", HERE.parents[3]))
MASTER = WORKSPACES / "westlake-harness"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    text = str(value)
    for root, token in ((WORKSPACES, "$WORKSPACES"), (Path.home(), "$HOME")):
        if text.startswith(str(root) + "/"):
            return token + text[len(str(root)):]
    return text


def expand(value):
    return Path(value.replace("$WORKSPACES/", str(WORKSPACES) + "/").replace("$HOME/", str(Path.home()) + "/"))


def load(path):
    return json.loads(Path(path).read_text())


def history_sources():
    return [(version.upper(), window, MASTER / f"benchmark/2026-10-03-{version}-stage-a-plan/window{window}-signoff/outer-signoff.json")
            for version, windows in (("u13", range(1, 5)), ("u14", range(1, 6))) for window in windows]


def counts(judgment):
    if "runs" in judgment:
        total, lit = judgment["runs"], judgment["lit_runs"]
    elif "verdict" in judgment:
        total, lit = 1, int(judgment["verdict"] == "lit")
    else:
        raise ValueError("signed history has no measured run count")
    if type(total) is not int or type(lit) is not int or not 0 <= lit <= total:
        raise ValueError("invalid signed run counts")
    return total, lit


def assignment(app, observations):
    reasons = []
    if app.get("historical_content_status") == "minimal" or app.get("needs_first_tap"):
        reasons.append("empty-first-screen-interaction")
    if app.get("is_game"):
        reasons.append("game")
    if app.get("historical_content_status") == "errors":
        reasons.append("error-first-screen")
    measured = sum(row["runs"] for row in observations if row["selected_apk_identity"])
    lit = sum(row["lit_runs"] for row in observations if row["selected_apk_identity"])
    boards = sorted({row["board"] for row in observations if row["selected_apk_identity"] and row["lit_runs"] > 0})
    white = any(row["white_observed"] for row in observations)
    adverse = any(row["runs"] > row["lit_runs"] for row in observations if row["selected_apk_identity"])
    if measured < 2 or lit < 2:
        reasons.append("fewer-than-two-confirmed-lit-runs")
    if len(boards) < 2:
        reasons.append("fewer-than-two-lit-boards")
    if white:
        reasons.append("signed-history-white")
    if adverse:
        reasons.append("signed-history-nonlit")
    group = "edge" if reasons else "stable"
    return {"key": app["key"], "package": app["package"], "apk_sha256": app["apk_sha256"],
            "name_zh": app["name_zh"], "group": group, "screenshot_seconds": 10 if group == "stable" else 20,
            "reasons": reasons, "historical_content_status": app.get("historical_content_status"),
            "history": {"measured_runs": measured, "lit_runs": lit, "lit_boards": boards,
                        "white_observed": white, "observations": observations},
            "demo_board_rounds": [1, 3], "spare_board_prescreen": "edge-only-not-demo-acceptance" if group == "edge" else "not-required"}


def generate(manifest_path, sources=None):
    manifest = load(manifest_path)
    selected = [row for row in manifest["apps"] if row["install"]]
    aliases = {key: row for row in selected for key in row["signed_keys"]}
    observed = {row["key"]: [] for row in selected}
    pins = []
    excluded = []
    seen_records = set()
    for version, window, path in sources or history_sources():
        signed = load(path)
        if signed["signer"] != "outer(claude)":
            raise ValueError("unsigned history: " + portable(path))
        source_id = f"{version}-window{window}"
        pin = {"id": source_id, "path": portable(path), "sha256": digest(path), "pair_sheets": []}
        pairs = []
        for sheet_path in sorted(path.parent.glob("pair-sheet*.json")):
            pin["pair_sheets"].append({"path": portable(sheet_path), "sha256": digest(sheet_path)})
            pairs.extend(load(sheet_path)["pairs"])
        pins.append(pin)
        for key, judgment in sorted(signed["keys"].items()):
            if key not in aliases:
                continue
            app = aliases[key]
            total, lit = counts(judgment)
            board = judgment["board"]
            if board not in {"5ea", "5cd", "61b"}:
                raise ValueError("ambiguous signed candidate board: " + key)
            candidates = [pair for pair in pairs if pair["key"] == key and pair["board"] == board and pair.get("window_t20")]
            records = []
            unmeasured = judgment.get("unmeasured", [])
            for pair in candidates:
                screenshot = expand(pair["window_t20"])
                if any("/" + sample["run"] + "/" in str(screenshot) for sample in unmeasured):
                    continue
                record_path = screenshot.parent / "record.json"
                record = load(record_path)
                if record.get("key") != key or record.get("package") != app["package"]:
                    raise ValueError("history record key/package mismatch: " + key)
                canonical = record_path.resolve()
                if canonical in seen_records:
                    raise ValueError("history repeats a candidate record: " + portable(record_path))
                seen_records.add(canonical)
                records.append({"path": portable(record_path), "sha256": digest(record_path),
                                "apk_sha256": record["apk_sha256"], "screenshot": portable(screenshot)})
            matched = len(records) == total and all(row["apk_sha256"] == app["apk_sha256"] for row in records)
            if not matched:
                excluded.append({"source": source_id, "key": key, "signed_runs": total,
                                 "candidate_records": len(records), "reason": "selected-APK-or-measured-run-binding-incomplete"})
            verdicts = judgment.get("verdicts", []) + ([judgment["verdict"]] if "verdict" in judgment else [])
            white = any("white" in verdict.lower() for verdict in verdicts)
            observed[app["key"]].append({"source": source_id, "pointer": "/keys/" + key,
                                         "history_key": key, "board": board, "runs": total, "lit_runs": lit,
                                         "selected_apk_identity": matched, "white_observed": white,
                                         "signed_verdicts": verdicts, "records": records})
    rows = [assignment(app, sorted(observed[app["key"]], key=lambda row: (row["source"], row["history_key"])))
            for app in sorted(selected, key=lambda row: row["key"])]
    if len({row["package"] for row in rows}) != len(rows):
        raise ValueError("duplicate selected package")
    stable = [row["key"] for row in rows if row["group"] == "stable"]
    edge = [row["key"] for row in rows if row["group"] == "edge"]
    return {"schema": "demo-baseline-groups/v1", "execution_enabled": False,
            "contract": "ef5412f82c (2026-10-09 accelerated/spare-prescreen policy)",
            "manifest": {"path": portable(manifest_path), "sha256": digest(manifest_path)},
            "sources": pins, "summary": {"selected_packages": len(rows), "stable": len(stable), "edge": len(edge),
                                         "special_edge_slots": 2, "history_sources": len(pins), "incomplete_identity_bindings": len(excluded)},
            "stable_keys": stable, "edge_keys": edge, "apps": rows,
            "special_slots": [{"key": row["key"], "package": row.get("package"), "group": "edge", "screenshot_seconds": 20,
                               "status": row["status"], "reasons": ["special-interactive-demo"], "demo_board_rounds": [1, 3]}
                              for row in manifest["special_apps"]],
            "excluded_history_bindings": excluded,
            "notes": ["Only actual candidate board counts; reference_board is not a second run.",
                      "Different Noice APK versions do not supply positive evidence for the selected version.",
                      "Legacy lit is history only, not fresh own-content proof. Empty/error/game overrides remain edge.",
                      "Spare-board k/n never replaces acceptance on 61b; latest policy uses t3 plus post-reboot on 61b.",
                      "Confirmed historical nonlit is conservatively edge, even when it was not white.",
                      "U14 window6 board-white/unresolved OrganicMaps is already edge from signed window5; no unsigned run is counted."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MASTER / "benchmark/2026-10-09-demo-baseline/demo-manifest.json")
    parser.add_argument("--out", type=Path, default=HERE / "groups.json")
    args = parser.parse_args()
    try:
        result = generate(args.manifest)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("REJECT: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
