"""Replay U7 provisional scores; never promote an analyst image review to outer signoff."""

import argparse
from collections import Counter
import copy
from pathlib import Path

import intake


HERE = Path(__file__).resolve().parent
u6 = intake.u6


def validate_review(row, review):
    if review["observation_sha256"] != u6.seal(row) or review["t20_sha256"] != row["t20_sha256"]:
        raise ValueError("review evidence changed: " + row["key"])
    if review["visual"] not in {"own-ui", "white", "desktop", "unknown"}:
        raise ValueError("invalid visual classification")
    wall = review["wall_id"]
    fatal = row["termination"]
    if wall == "none":
        if review["visual"] != "own-ui" or fatal["status"] != "no-observed-termination" or not row["log_complete"] or not row["target_pids"] or not row["binding_lines"]:
            raise ValueError("no-wall needs bound execution, complete log and own UI")
    elif wall != "unknown":
        if fatal["status"] != "termination-found" or not fatal.get("root"):
            raise ValueError("wall needs a termination and causal root")
        if review["terminal_line"] != fatal["terminal"]["event"]["line"] or review["root_line"] != fatal["root"]["event"]["line"]:
            raise ValueError("review substituted another warning or root")
    signoff = review.get("outer_signoff")
    if signoff is not None and (signoff.get("reviewer") != "outer" or not signoff.get("source") or signoff.get("t20_sha256") != row["t20_sha256"] or signoff.get("visual") != review["visual"]):
        raise ValueError("outer signoff does not bind this screenshot and verdict")


def score_row(row, review):
    validate_review(row, review)
    observation = dict(identity_verified=row["identity_verified"] and not row["issues"],
                       first_attempt=row["first_attempt"], first_wall_id=review["wall_id"],
                       first_wall_confirmed=review["wall_id"] != "unknown",
                       positive_crossings=[], old_wall_reproduced=[],
                       t20_reviewed=review.get("outer_signoff") is not None,
                       own_ui=None if review["visual"] == "unknown" else review["visual"] == "own-ui")
    preview = copy.deepcopy(observation)
    preview["t20_reviewed"] = review["visual"] != "unknown"
    return dict(key=row["key"], record=row["record"], target_pids=row["target_pids"],
                expected_wall=row["prediction"]["wall_id"], observed_wall=review["wall_id"],
                expected_t20=row["prediction"]["t20_prediction"], visual=review["visual"],
                terminal_status=row["termination"]["status"],
                terminal_line=review.get("terminal_line"), root_line=review.get("root_line"),
                scores=u6.forecast.score_reviewed(row["prediction"], observation),
                analyst_t20_preview=u6.forecast.score_reviewed(row["prediction"], preview)["t20"],
                checkpoint_note="No positive operation receipt reviewed; install success/source hash is not installed-APK readback." if row["prediction"]["fix_ids"] else "No checkpoint predicted.",
                description=review["description"], t20_sha256=row["t20_sha256"],
                outer_signoff=review.get("outer_signoff"))


def build(prepared, reviews, formal=False):
    intake.verify_freeze()
    if prepared["prediction_sha256"] != intake.CSV_SHA or reviews["prepared_sha256"] != u6.seal(prepared):
        raise ValueError("prepared evidence or freeze identity changed")
    actual = {row["key"] for row in prepared["rows"]}
    predictions = {row["key"]: row for row in u6.read(intake.FROZEN / "PREDICTIONS.json")["rows"]}
    if len(actual) != len(prepared["rows"]) or actual != set(reviews["rows"]) or not actual <= set(predictions):
        raise ValueError("duplicate, missing or unknown key")
    if prepared["missing_keys"] != sorted(set(predictions) - actual):
        raise ValueError("missing-key accounting changed")
    if formal and (actual != set(predictions) or any(not review.get("outer_signoff") for review in reviews["rows"].values())):
        raise ValueError("formal score requires all 66 keys and outer screenshot signoff")
    rows = []
    for row in prepared["rows"]:
        if row["prediction"] != predictions[row["key"]]:
            raise ValueError("prediction changed")
        rows.append(score_row(row, reviews["rows"][row["key"]]))
    return dict(status="formal" if formal else "preliminary-not-full-U7", prediction_sha256=intake.CSV_SHA,
                prepared_sha256=u6.seal(prepared), reviews_sha256=u6.seal(reviews),
                selected_keys=len(rows), missing_keys=prepared["missing_keys"],
                axes={axis: dict(Counter(row["scores"][axis] for row in rows)) for axis in ["first_wall", "checkpoints", "t20"]},
                analyst_t20_preview=dict(Counter(row["analyst_t20_preview"] for row in rows)),
                visual_counts=dict(Counter(row["visual"] for row in rows)), rows=rows)


def markdown(report):
    lines = ["# U7 5ea preliminary scoring", "", "Not the full 66-key result. Analyst image review is not outer signoff.", "",
             "Frozen CSV: `" + report["prediction_sha256"] + "`.", "",
             "| Axis | Scores |", "|---|---|"]
    for axis, counts in report["axes"].items():
        lines.append("| " + axis + " | " + ", ".join(f"{name}={count}" for name, count in sorted(counts.items())) + " |")
    lines += ["", "Analyst-only t20 preview: " + str(report["analyst_t20_preview"]) + ". Not an accepted t20 score.", "",
              "| Key | First wall | Checkpoint | t20 | Visual draft | Terminal/root hilog lines |", "|---|---|---|---|---|---|"]
    for row in report["rows"]:
        lines.append(f"| {row['key']} | {row['scores']['first_wall']} ({row['observed_wall']}) | {row['scores']['checkpoints']} | {row['scores']['t20']} | {row['visual']} | {row['terminal_line'] or '-'} / {row['root_line'] or '-'} |")
    lines += ["", "Missing/unselected keys (not scored): " + ", ".join(report["missing_keys"]), "",
              "Burger King INPUT-merged checkpoint stays unknown: zero external sidecars skips installed APK readback in the retained runner. Native libz failure does not establish that input checkpoint either way.",
              "Fennec has process-disappearance evidence without a recovered fatal root. White AppManager/app rows remain unknown first wall; no SceneBoard/root-cause inference is made.",
              "Antennapod is visibly lit in this attempt but its frozen flaky flag keeps t20 unknown.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal", action="store_true")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = build(u6.read(HERE / "evidence/5ea-prepared.json"), u6.read(HERE / "evidence/5ea-review.json"), args.formal)
    if args.verify:
        if report != u6.read(HERE / "results.json") or markdown(report) != (HERE / "PRELIMINARY.md").read_text():
            raise ValueError("report replay differs")
        print("PASS U7 provisional replay; not outer acceptance")
    else:
        print(markdown(report) if args.markdown else u6.encoded(report), end="")


if __name__ == "__main__":
    main()
