"""Replay pinned APK evidence and intersect static candidates with signed U7."""

from collections import Counter
import base64
import gzip
import hashlib
import json
from pathlib import Path

import rules


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HISTORICAL = {"wikipedia", "fd-noice", "noice", "fd-AppManager", "fd-app", "fd-shatteredpixeldungeon", "termux", "fd-mobile"}
FIRST_SCREEN = {"fd-organicmaps", "fd-reader"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def read_evidence(key):
    path = HERE / "evidence" / (key + ".json.gz.b64")
    return json.loads(gzip.decompress(base64.b64decode(path.read_bytes())))


def verify_row(row):
    if hashlib.sha256(row["manifest_text"].encode()).hexdigest() != row["manifest_sha256"]:
        raise ValueError("manifest hash drift")
    if rules.manifest(row["manifest_text"]) != row["manifest"]:
        raise ValueError("manifest extraction drift")
    inventory = {item["name"]: item["sha256"] for item in row["dex"]}
    for method in row["retained_methods"].values():
        if inventory[method["dex"]] != method["dex_sha256"]:
            raise ValueError("DEX evidence drift")
    expected_launchers = [item for item in row["manifest"]["launchers"] if item["enabled"]]
    if [item["launcher"] for item in row["launchers"]] != expected_launchers:
        raise ValueError("launcher inventory drift")
    for item in row["launchers"]:
        actual = rules.inspect_activity(item["launcher"]["target"], row["class_hierarchy"], row["retained_methods"])
        if actual != item["analysis"]:
            raise ValueError("lifecycle replay drift: " + row["key"])
    if row["runner_override"]:
        actual = rules.inspect_activity(row["runner_activity"], row["class_hierarchy"], row["retained_methods"])
        if actual != row["runner_override"]:
            raise ValueError("runner override drift")


def build():
    index = read(HERE / "evidence/index.json")
    focused_path = HERE / "evidence/focused-bytecode.json"
    if sha(focused_path) != index["focused_bytecode_sha256"]:
        raise ValueError("focused bytecode drift")
    focused = {(item["key"], item["dex"]): item for item in read(focused_path)}
    frozen = ROOT / "benchmark/2026-10-01-u7-prospective/v1/inputs.json"
    signed = ROOT / "benchmark/2026-10-01-u7-scoring/formal-66/results.json"
    if sha(frozen) != index["frozen_inputs_sha256"] or sha(signed) != index["signed_scores_sha256"]:
        raise ValueError("frozen/signed source drift")
    inputs = {item["key"]: item for item in read(frozen)["apps"]}
    scores = {item["key"]: item for shard in read(signed)["shards"].values() for item in shard["rows"]}
    rows = []
    for key, digest in sorted(index["evidence_sha256"].items()):
        path = HERE / "evidence" / (key + ".json.gz.b64")
        if sha(path) != digest:
            raise ValueError("evidence hash drift: " + key)
        evidence = read_evidence(key)
        if evidence["key"] != key or evidence["apk_sha256"] != inputs[key]["apk_sha256"]:
            raise ValueError("APK identity drift")
        verify_row(evidence)
        analyses = [item["analysis"] for item in evidence["launchers"]]
        starts = list({(item["method"], item["dex"], item["instruction"]["offset"]): item for analysis in analyses for item in analysis["starts"]}.values())
        routed, permissions = [], []
        for site in starts:
            if site["kind"] == "activity-result-launch":
                context = focused[(key, site["dex"])]
                bound = next(item for item in context["lines"] if item["line"] == site["instruction"]["line"])
                if context["apk_sha256"] != evidence["apk_sha256"] or context["dex_sha256"] != site["dex_sha256"] or not bound["text"].endswith(site["instruction"]["instruction"]):
                    raise ValueError("modern input context not bound to call")
                site = dict(site, input_classification=rules.modern_input(site, context["lines"]))
            (permissions if site.get("input_classification", {}).get("kind") == "permission-string-input" else routed).append(site)
        starts = routed
        finishes = list({(item["method"], item["dex"], item["instruction"]["offset"]): item for analysis in analyses for item in analysis["finishes"]}.values())
        limits = sorted({item for analysis in analyses for item in analysis["limits"]})
        status = "possible-lifecycle-trampoline" if starts else "unknown-bounded-analysis" if limits or not analyses else "no-lifecycle-start-found"
        rows.append(dict(key=key, package=evidence["package"], apk_sha256=evidence["apk_sha256"], evidence_sha256=digest,
                         declared_activities=len(evidence["manifest"]["activities"]), launchers=[item["launcher"] for item in evidence["launchers"]],
                         status=status, starts=starts, finishes=finishes, limits=limits, permission_requests=permissions,
                         literal_start_sites=sum(item["kind"] == "literal-startActivity" for item in starts),
                         activity_result_sites=sum(item["kind"] == "activity-result-launch" for item in starts),
                         runner_activity=evidence["runner_activity"], runner_override=evidence["runner_override"],
                         other_start_sites=evidence["unrelated_or_callback_start_sites"], signed_t20=scores[key]["visual"],
                         historical_white_black_cohort=key in HISTORICAL, first_screen_cohort=key in FIRST_SCREEN,
                         current_u7_white_black=scores[key]["visual"] in {"white", "black"}))
    if len(rows) != 66 or {item["key"] for item in rows} != set(inputs):
        raise ValueError("exactly 66 frozen APK keys required")
    controls = [item for item in rows if item["key"] in {"ooniprobe", "fd-stk"}]
    if len(controls) != 2 or any(item["declared_activities"] != 1 or item["signed_t20"] != "own-ui" or item["starts"] for item in controls):
        raise ValueError("single-Activity lit control predicate violated")
    extra = next(item for item in rows if item["key"] == "fd-fitness")
    if extra["declared_activities"] <= 1 or extra["signed_t20"] != "own-ui" or extra["status"] != "no-lifecycle-start-found":
        raise ValueError("additional bounded Java negative violated")
    return dict(schema_version=1, status="offline-static-prediction-not-window-defect-diagnosis", evidence_index_sha256=sha(HERE / "evidence/index.json"),
                counts=dict(Counter(item["status"] for item in rows)),
                candidate_keys=[item["key"] for item in rows if item["starts"]],
                literal_candidate_keys=[item["key"] for item in rows if item["literal_start_sites"]],
                modern_only_candidate_keys=[item["key"] for item in rows if item["activity_result_sites"] and not item["literal_start_sites"]],
                permission_only_keys=[item["key"] for item in rows if item["permission_requests"] and not item["starts"]],
                intersections={name: [dict(key=item["key"], status=item["status"], signed_t20=item["signed_t20"], literal_start_sites=item["literal_start_sites"], activity_result_sites=item["activity_result_sites"]) for item in rows if item[field]] for name, field in [("historical_white_black", "historical_white_black_cohort"), ("current_u7_white_black", "current_u7_white_black"), ("first_screen", "first_screen_cohort")]},
                controls=[dict(key=item["key"], declared_activities=1, signed_t20=item["signed_t20"], status=item["status"], limits=item["limits"], false_positive=False) for item in controls],
                additional_java_negative=dict(key=extra["key"], declared_activities=extra["declared_activities"], signed_t20=extra["signed_t20"], status=extra["status"], scope="complete within bounded Java lifecycle graph, not all Java or callbacks"),
                limitations=["No-start-found means no match in the bounded Java lifecycle scope, not proof that no activity ever launches.",
                             "fd-stk invokes native lifecycle helpers: second non-alert control remains unknown, not a complete negative.",
                             "Class constants are destination candidates without Intent register dataflow proof.",
                             "finish anywhere in the lifecycle graph does not prove a start/finish pair on the same path.",
                             "ActivityResultLauncher.launch may request permissions or return a synchronous result: this separate candidate is not proof of Activity creation.",
                             "Conditional bytecode calls and same-hierarchy helpers are possible paths, not guaranteed immediate execution; callbacks/cross-class/reflection/native code are outside scope.",
                             "Raw DEX disassembly uses dexdump owner.method:descriptor notation, equivalent invoke evidence to smali owner->method(descriptor)."], rows=rows)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", help="decode one pinned evidence bundle")
    args = parser.parse_args()
    print(json.dumps(read_evidence(args.key) if args.key else build(), ensure_ascii=False, sort_keys=True, indent=2))
