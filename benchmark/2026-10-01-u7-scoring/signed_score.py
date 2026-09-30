"""Replay outer-signed 5ea and 5cd scores without changing the preliminary snapshot."""

from collections import Counter
from pathlib import Path
import hashlib
import re

import intake


u6 = intake.u6
HERE = Path(__file__).resolve().parent
SIGNED = HERE / "signed-44"


def score_row(row, review, signoffs):
    if review["observation_sha256"] != u6.seal(row) or review["t20_sha256"] != row["t20_sha256"]:
        raise ValueError("review evidence drift")
    signoff = signoffs[review["authority"]]
    if hashlib.sha256(signoff["text"].encode()).hexdigest() != signoff["sha256"] or review["authority_sha256"] != signoff["sha256"]:
        raise ValueError("signoff text drift")
    if not any(re.search(r"(?<![A-Za-z0-9_-])" + re.escape(key) + r"(?![A-Za-z0-9_-])", signoff["text"]) for key in [row["key"], row["key"].removeprefix("fd-")]):
        raise ValueError("key not in signed shard")
    visual, wall = review["visual"], review["wall_id"]
    if visual not in {"own-ui", "white", "black", "desktop", "no-capture"}:
        raise ValueError("invalid visual")
    if (visual == "no-capture") != (row["t20_sha256"] is None):
        raise ValueError("missing capture cannot be lit/unlit")
    fatal = row["termination"]
    if wall == "none" and (visual != "own-ui" or fatal["status"] != "no-observed-termination" or not row["log_complete"] or not row["binding_lines"]):
        raise ValueError("no-wall evidence insufficient")
    if wall not in {"none", "unknown"}:
        if fatal["status"] != "termination-found" or review["terminal_line"] != fatal["terminal"]["event"]["line"]:
            raise ValueError("must cite selected terminal")
        root = fatal.get("root") or {}
        if root.get("status") == "fault-thread-stack":
            frames = {frame["line"]: frame for frame in row["native_frames"]}
            reason = next((event for event in row["witnesses"] if event["line"] == review.get("reason_line")), None)
            terminal = fatal["terminal"]["event"]
            frame_token, reason_token = ("FatalError", "libmediandk.so") if wall == "unity-mediandk-load" else ("GetLongField", "fid == null")
            if review["root_line"] not in frames or frame_token not in frames[review["root_line"]]["message"] or not reason or reason_token not in reason["message"]:
                raise ValueError("native wall needs fault-thread stack and abort reason")
            if (reason["pid"], reason["tid"]) != (terminal["pid"], terminal["tid"]) or not 0 <= u6.first_fatal.seconds(terminal["timestamp"]) - u6.first_fatal.seconds(reason["timestamp"]) <= 2:
                raise ValueError("abort reason not adjacent on terminal thread")
        elif review["root_line"] != (root.get("event") or {}).get("line"):
            raise ValueError("causal root substitution")
    observed = dict(identity_verified=row["identity_verified"] and not row["issues"], first_attempt=row["first_attempt"],
                    first_wall_confirmed=wall != "unknown", first_wall_id=wall,
                    positive_crossings=[], old_wall_reproduced=[],
                    t20_reviewed=visual != "no-capture", own_ui=visual == "own-ui")
    return dict(key=row["key"], expected_wall=row["prediction"]["wall_id"], observed_wall=wall,
                expected_t20=row["prediction"]["t20_prediction"], visual=visual,
                scores=u6.forecast.score_reviewed(row["prediction"], observed),
                terminal_line=review.get("terminal_line"), root_line=review.get("root_line"), reason_line=review.get("reason_line"),
                fixes=row["prediction"]["fix_ids"], checkpoint_note="unknown: no positive named-operation receipt; UI and class linkage are insufficient" if row["prediction"]["fix_ids"] else "not applicable",
                issues=row["issues"], record=row["record"], t20_sha256=row["t20_sha256"], authority=review["authority"])


def build(full=False):
    intake.verify_freeze()
    directory = HERE / "formal-66" if full else SIGNED
    signoffs = u6.read(directory / "outer-signoffs.json")
    reviews = u6.read(directory / "reviews.json")
    shards = {}
    sources = [("5ea", HERE / "evidence/5ea-prepared.json"), ("5cd", SIGNED / "5cd-prepared.json")]
    if full:
        sources.append(("61b", directory / "61b-prepared.json"))
    for shard, source in sources:
        prepared = u6.read(source)
        if reviews["prepared_sha256"][shard] != u6.seal(prepared):
            raise ValueError("prepared shard changed")
        rows = [score_row(row, reviews["rows"][row["key"]], signoffs) for row in prepared["rows"]]
        shards[shard] = dict(keys=len(rows), axes={axis: dict(Counter(row["scores"][axis] for row in rows)) for axis in ["first_wall", "checkpoints", "t20"]}, rows=rows)
    rows = [row for shard in shards.values() for row in shard["rows"]]
    count = 66 if full else 44
    if len(rows) != count or len({row["key"] for row in rows}) != count or {row["key"] for row in rows} != set(reviews["rows"]):
        raise ValueError("signed cohort must contain exactly " + str(count) + " unique keys")
    result = dict(status="outer-signed-66-key-U7" if full else "outer-signed-44-key-partial-not-full-U7", prediction_sha256=intake.CSV_SHA,
                review_sha256=u6.seal(reviews), signoffs_sha256=u6.seal(signoffs), shards=shards,
                axes={axis: dict(Counter(row["scores"][axis] for row in rows)) for axis in ["first_wall", "checkpoints", "t20"]})
    if full:
        predictions = u6.read(intake.FROZEN / "PREDICTIONS.json")["rows"]
        if {row["key"] for row in predictions} != {row["key"] for row in rows}:
            raise ValueError("full frozen key set differs")
        counts = dict(Counter(row["t20_prediction"] for row in predictions))
        if counts != {"own-ui": 28, "unlit": 32, "unknown": 6}:
            raise ValueError("frozen t20 distribution changed")
        result.update(forecast_counts=counts, visual_counts=dict(Counter(row["visual"] for row in rows)),
                      rates={axis: dict(hits=totals.get("hit", 0), scored=totals.get("hit", 0) + totals.get("false_positive", 0),
                                        hit_fraction_on_scored=totals.get("hit", 0) / (totals.get("hit", 0) + totals.get("false_positive", 0)) if totals.get("hit", 0) + totals.get("false_positive", 0) else None,
                                        hit_fraction_all_keys=totals.get("hit", 0) / 66) for axis, totals in result["axes"].items()},
                      confirmed_unpredicted_fatal_walls=[row for row in rows if row["observed_wall"] not in {"none", "unknown"} and row["expected_wall"] not in {row["observed_wall"], "unknown"}],
                      unknown_first_wall_keys=[row["key"] for row in rows if row["scores"]["first_wall"] == "unknown"])
    return result


def markdown(report):
    full = report["status"] == "outer-signed-66-key-U7"
    lines = ["# U7 signed " + ("66-key formal score" if full else "44-key partial score"), "", "Frozen fa92c5b9 unchanged. Original 5ea preliminary and signed-44 snapshots remain intact.", "",
             "5ea t20 authority: outer ACK(95) **06:33:44**, not the nonexistent 06:0x reference. 5cd: **06:25:18**.", "",
             "| Shard | First wall | Checkpoints | t20 |", "|---|---|---|---|"]
    for shard, data in report["shards"].items():
        lines.append(f"| {shard} | {data['axes']['first_wall']} | {data['axes']['checkpoints']} | {data['axes']['t20']} |")
    if full:
        lines += ["", "61b authority: outer ACK(95) **06:39:59**.", "", "All axes: " + str(report["axes"]), "",
                  "Frozen t20 predictions: 28 own UI / 32 unlit / 6 unknown. Signed screenshots: " + str(report["visual_counts"]),
                  "Rates (unknown/NA excluded from scored denominator, also show all 66): " + str(report["rates"]), "",
                  "Confirmed unpredicted fatal walls: " + str(len(report["confirmed_unpredicted_fatal_walls"])) + ". Unknown first-wall keys are coverage gaps, not a zero-miss claim over all apps."]
    lines += ["", "| Key | First wall | Checkpoint | t20 | Visual | Terminal/root |", "|---|---|---|---|---|---|"]
    for shard in report["shards"].values():
        for row in shard["rows"]:
            lines.append(f"| {row['key']} | {row['scores']['first_wall']} ({row['observed_wall']}) | {row['scores']['checkpoints']} | {row['scores']['t20']} | {row['visual']} | {row['terminal_line'] or '-'} / {row['root_line'] or '-'} |")
    lines += ["", "Unknown is not a hit or a miss. Seal never installed/launched and has no screenshot: all three runtime axes unknown. Frozen flaky keys remain unknown t20 despite signed light.",
              "Applicable checkpoint rows remain unknown: exact positive operation receipts are absent; UI/absence-of-error/class linkage cannot replace frozen criteria.",
              "fd-plus has an earlier ColorMatrix.set warning at L50986, but its terminal root is the later MapInfoLayer null (L60342 -> L60357). Do not substitute an earlier caught exception for first_fatal.",
              "fd-organicmaps is the only scored t20 false-positive (predicted unlit, signed own splash). fd-reader's unknown forecast stays unknown, not a retrospectively claimed hit. See GAINS.md for separate causal analysis.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    report = build("--full" in sys.argv)
    print(markdown(report) if "--markdown" in sys.argv else u6.encoded(report), end="")
