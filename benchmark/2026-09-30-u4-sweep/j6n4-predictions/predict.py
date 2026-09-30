#!/usr/bin/env python3
"""Prospective J6/N4 cohort forecast; no device access or future score fabrication."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
SWEEP = HERE.parent
ROOT = SWEEP.parents[1]
BASE = "801119764"
SOURCES = {
    "score": (BASE, "benchmark/2026-09-30-u4-sweep/SCORING.json"),
    "observations": (BASE, "benchmark/2026-09-30-u4-sweep/scoring-evidence/observations.json"),
    "context": (BASE, "benchmark/2026-09-30-u4-sweep/scoring-inputs/predictions-context.json"),
    "next-batch": (BASE, "benchmark/2026-09-30-u4-sweep/NEXT-BATCH.json"),
    "native-drafts": (BASE, "benchmark/2026-09-30-u4-sweep/N4-DRAFTS.md"),
    "namespace": ("9b586b482", "benchmark/2026-09-30-u4-sweep/NAMESPACE-WALL.md"),
    "metadata": ("bca15bdc", "bms/src/adapter/framework/activity/java/SelfApplicationMetaData.java"),
    "service-query": ("44542036", "bms/src/adapter/framework/activity/java/SelfServiceFallback.java"),
    "alarm-split": ("dca1ec13", "bms/src/adapter/framework/activity/java/AlarmFetcher.java"),
}
FROZEN_FILES = ["J6N4-PREDICTIONS.csv", "J6N4-PREDICTIONS.md",
                "j6n4-predictions/criteria.json", "j6n4-predictions/predict.py"]
CHECKS = {
    "N4-owner": dict(
        fail="Flutter default-owner namespace configuration failed: [nonzero] OR [N3-OWNER] resident runtime unavailable",
        positive="Same target PID: [N3-OWNER] resident runtime published + [N2-OWNER] ABI global ready, then configuration returned 0 or an actual app dlopen attempt after configuration; no duplicate runtime construction",
        limit="Publication alone is not completion proof; a later consumer relocation can fail after this configuration checkpoint passed"),
    "N4-egl": dict(
        fail="JNI fid == null with GetLongField and EGLImpl.eglInitialize in the same PID/TID abort context",
        positive="Executed eglInitialize on a real EGLDisplayImpl: non-null field access completed and real EGL initialization reached (EGL_TRUE or a recorded EGL error), or actual later eglChooseConfig/context execution; not OH_RegHook registration",
        limit="EGL_FALSE after verified field access is a field-contract hit plus a separate later EGL wall, not a light; missing execution evidence stays unknown"),
    "N4-megazord": dict(
        fail="libmegazord.so: __get_h_errno: symbol not found",
        positive="Actual libmegazord load/relocation or a specific later relocation/init error in that same consumer after resolving __get_h_errno@LIBC",
        limit="__sF/JNA registration success and absence of the old string alone do not prove this checkpoint"),
    "N4-opensles": dict(
        fail="libarc.so: slCreateEngine: symbol not found",
        positive="Actual libarc relocation completed with slCreateEngine bound to real platform OpenSLES, or specific later libarc relocation; retain provider path/SHA/namespace witness",
        limit="A provider-handle dlsym alone is insufficient; engine/PCM behavior and IID identity are separate later checks"),
    "J6-metadata": dict(
        fail="DSN is required. Use empty string or set enabled to false in SentryOptions to disable SDK.",
        positive="[B8-PM] projected getApplicationInfo metaData=... for im.vector.app plus self GET_META_DATA showing io.sentry.auto-init=false and execution beyond the formerly failing initialization",
        limit="A metadata count alone does not prove the false value; score independently of N4-owner"),
    "J6-service-query": dict(
        fail="Failed to resolve SessionToken for ComponentInfo{org.fossify.musicplayer/org.fossify.musicplayer.playback.PlaybackService}",
        positive="[B8-PM] projected queryIntentServices androidx.media3.session.MediaSessionService -> positive self service count, correct PlaybackService in the returned slice, and successful SessionToken resolution",
        limit="The bitmap color-space fatal already followed the old query error in U4; seeing bitmap again alone is NOT query-pass proof"),
    "J6-alarm-recheck": dict(
        fail="AlarmFetcher split absent or alarm behavior regresses; missing marker with incomplete logs remains unknown",
        positive="[B8-FETCH] alarm fetcher replaced in the target process (outer-requested split recheck)",
        limit="Revalidates frozen alarm behavior for fd-k9/fd-android; no new-light or vibrator-manager repair claim"),
}
UNTOUCHED = {
    "fd-api": "AppCompat theme requirement",
    "fd-breezyweather": "Object.getClass null producer",
    "fd-catima": "Object.getClass null producer on resume",
    "fd-client": "WestlakeSSLContext has no SSLEngine; later accountManager null",
    "fd-feeder": "NetworkRequest.getNetworkSpecifier missing (T7 held)",
    "fd-gallery": "MediaStore.Images.Media.EXTERNAL_CONTENT_URI missing (T7 held)",
    "fd-libretube": "TagSoup Parser.setProperty missing (T7 held)",
    "fd-meet": "Collection.iterator null producer / restrictions investigation",
    "fd-plus": "NetworkInfo.getState missing; later OsmandMap null (T7 held)",
    "fd-reader": "Null reference used for synchronization / haptics producer",
    "fd-tutanota": "WebView provider path UnsupportedOperationException; real provider still held",
    "fd-wifianalyzer": "Object.getClass null producer",
    "opencamera": "Intent.getIntExtra on null Intent",
    "vlc": "Onboarding inflater/theme/context failure; resource fix held",
    "wikipedia": "TagSoup Parser.setProperty missing (T7 held)",
    "x": "NetworkCapabilities bandwidth method missing; later app graph undefined (T7 held)",
}
UI_RULE = "Outer reviews this key's APK-matched t20 screenshot: own app content vs white/black/launcher/crash/dialog. Alive/READY/no fatal is not UI proof. Retain path+SHA+review citation."


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(commit, path):
    return subprocess.check_output(["git", "show", commit + ":" + path], cwd=ROOT)


def payload(text):
    return re.sub(r"^\S+ \S+\s+\d+\s+\d+\s+[A-Z]\s+[^:]+: ?(?:\[stderr\] )?", "", text)


def build():
    raw = {name: blob(*pin) for name, pin in SOURCES.items()}
    score = {row["key"]: row for row in json.loads(raw["score"])["rows"]}
    observations = {row["key"]: row for row in json.loads(raw["observations"])}
    context = {row["key"]: row for row in json.loads(raw["context"])["rows"]}
    batch = {row["id"]: row for row in json.loads(raw["next-batch"])["rows"]}
    if not len(score) == len(observations) == len(context) == 66 or set(score) != set(observations) or set(score) != set(context):
        raise ValueError("cohort mismatch")
    rows = []
    for key in sorted(score):
        observed = observations[key]
        prior = score[key]
        checkpoint_ids = [ident for ident in ("N4-owner", "N4-egl", "N4-megazord", "N4-opensles", "J6-metadata", "J6-service-query") if key in batch[ident]["apps"]]
        control = prior["outer_lit"] or key in ("antennapod", "fd-notes")
        fatal = observed["signals"].get("fatal", {}).get("evidence", [])
        candidates = observed["prior_matches"].get("first_blocker", {}).get("evidence", []) + [wall["evidence"] for wall in observed["walls"]]
        first = min(candidates, key=lambda item: item["line"]) if candidates else (fatal[0] if fatal else None)
        first_kind = "attributable-error-not-necessarily-fatal" if first else "no-confirmed-causal-wall"
        wall = payload(first["text"]) if first else "No explicit causal fatal; observation-only unlit outcome"
        remaining = "Later walls and UI remain unknown; no guaranteed new light"
        if observed["input_error"]:
            prediction = "unknown"
            wall = "HOST INPUT: " + observed["input_error"]
            first_kind = "host-input-not-run"
            remaining = "Separate input-recovery revision required; never credit J6/N4. Preserve this row even if APK is replaced."
        elif checkpoint_ids:
            prediction = "过墙"
        elif control:
            prediction = "不变"
            if key in ("antennapod", "fd-notes"):
                wall = "U4 first-run RenderThread SIGSEGV; outer 23:01 reports 3/3 zero-variable UI recovery"
                remaining = "Intermittent protection control; first scheduled attempt scored before separately reporting repeats"
            else:
                wall = "No first-page blocking wall in outer-reviewed U4 own UI"
                first_kind = "reviewed-ui-control"
                remaining = "Preserve existing capability, not an additional light; background/function errors may remain"
        elif key in UNTOUCHED:
            prediction = "不变"
            wall = UNTOUCHED[key]
            remaining = "No approved J6/N4 fix for this wall; exact old witness or proven crossing required for scoring"
        else:
            prediction = "unknown"
            remaining = "Unknown producer or unobserved first fatal; unlit alone cannot identify a wall"
        if key == "fd-im-vector-app":
            wall = "Sentry DSN precursor at40970; owner configuration fatal at55229"
            remaining = "Both metadata and owner checkpoints must pass for aggregate hit; realm/app-init or other later walls can still block UI"
        if key == "fd-musicplayer":
            wall = "SessionToken self-service query at34313; bitmap color-space fatal at52303"
            remaining = "Bitmap color-space remains OUTSIDE final N4 scope; predict query advance, NOT a light"
        if key == "fd-noice":
            wall = "Repeatable U4 white UI without causal fatal; ANL interaction experiment unresolved at forecast cutoff"
            remaining = "Mandatory restoration gate but prediction unknown: no accepted source repair yet. Restore ceiling1, not a new light; SSLSockets is not a proved white-screen cause."
        if key == "noice":
            wall = "Other Noice APK: no causal fatal, white/no-content despite media_router installation"
            remaining = "Same package as fd-noice, different APK SHA; no second restoration credit and no new media-router benefit claimed"
        rechecks = ["J6-alarm-recheck"] if key in ("fd-k9", "fd-android") else []
        if key in ("fd-immich", "fd-libre", "fd-saber"):
            remaining += "; prior property/engine ABI checkpoints were masked by owner failure and must be observed, not assumed fixed"
        if key in ("fd-organicmaps", "mcdonalds", "ppsspp"):
            remaining += "; owner error was caught/downstream, not necessarily the first fatal; do not use process survival as a pass"
        if checkpoint_ids:
            log_pass = " || ".join(ident + ": " + CHECKS[ident]["positive"] for ident in checkpoint_ids)
            log_fail = " || ".join(ident + ": " + CHECKS[ident]["fail"] for ident in checkpoint_ids)
        elif control:
            log_pass = "Target bindApplication identity and complete t20 capture; logs annotate regressions but outer own-UI verdict decides preservation"
            log_fail = "A complete outer-reviewed first scheduled t20 without own UI fails preservation; a missing frame/review is unknown"
        elif prediction == "不变":
            log_pass = "Exact normalized old wall reproduced in target PID: " + (payload(first["text"]) if first else wall)
            log_fail = "Proven execution beyond this exact old wall with positive witness; absence alone is unknown"
        else:
            log_pass = "Collect target bindApplication, full hilog, actual first error and t20; no prospective hit can be claimed for unknown"
            log_fail = "Not a promised repair; record observed result and new signatures separately, not an automatic false positive"
        if rechecks:
            log_pass += " || alarm recheck: " + CHECKS["J6-alarm-recheck"]["positive"]
        t20 = "Own UI preserved" if control else ("Unlit likely: unchanged known wall; still review actual frame" if prediction == "不变" else "Own UI unknown; checkpoint advance is not a lighting promise")
        if key == "fd-musicplayer":
            t20 = "Unlit likely while bitmap wall remains; successful query alone is not a light"
        if key == "fd-noice":
            t20 = "Unknown forecast; outer must require welcome UI restored before promotion"
        if observed["input_error"]:
            t20 = "No t20 expected without separately approved input recovery; do not count capture absence as runtime failure"
        rows.append(dict(key=key, package=observed["package"], apk_sha256=observed["apk_sha256"],
            current_first_wall=wall, first_wall_kind=first_kind,
            source_log=observed["log"], source_log_sha256=observed.get("sha256"),
            record=observed["record"], record_sha256=observed["record_sha256"],
            current_wall_line=first["line"] if first else None,
            current_wall_evidence=first["text"] if first else "No causal log witness; see identity/input/UI evidence",
            first_fatal_line=fatal[0]["line"] if fatal else None,
            first_fatal_evidence=fatal[0]["text"] if fatal else "No explicit target fatal witness",
            binding_evidence=observed["bindings"], baseline_screenshots=observed["screenshots"],
            u4_first_sweep_lit=prior["outer_lit"], preservation_control=control,
            fix_ids=checkpoint_ids, recheck_ids=rechecks, prediction=prediction,
            log_pass_rule=log_pass, log_fail_rule=log_fail, expected_t20=t20, t20_rule=UI_RULE,
            known_remaining=remaining, predicted_new_light=None,
            condition="Same frozen APK/sidecars, approved combined J6+N4 manifest and boot identity; clean install, target PID, complete logs and first scheduled t20. Earlier gate masking stays unknown."))
    pins = {name: dict(commit=subprocess.check_output(["git", "rev-parse", pin[0]], cwd=ROOT, text=True).strip(), path=pin[1], sha256=sha(raw[name])) for name, pin in SOURCES.items()}
    return dict(schema=1, source_pins=pins, rows=rows, checkpoints=CHECKS,
        scope="Outer ACK(90) 2026-09-30 23:36:46 + 23:49:19 + 23:55:12: J5b base + alarm split + metadata + service-query; N4 owner/EGL/megazord/OpenSLES; Noice gate unresolved",
        baseline_note="U4 first sweep stays 22 UI; AntennaPod/Notes repeat recovery is a separately attributed control fact. Unified state remains U3; this is not a U3-to-U4 rescore.",
        counts=dict(predictions=dict(Counter(row["prediction"] for row in rows)),
                    primary_checkpoints=dict(Counter(ident for row in rows for ident in row["fix_ids"])),
                    rechecks=dict(Counter(ident for row in rows for ident in row["recheck_ids"]))),
        candidate_binding=dict(status="pending-pre-run-receipt", jar_sha256=None, native_manifest_sha256=None,
                               runtime_fingerprint_sha256=None, bootimage_fingerprint_sha256=None),
        deployment_authorized=False, batch_measurements_read=0)


def csv_bytes(report):
    fields = ["key", "package", "apk_sha256", "current_first_wall", "first_wall_kind", "source_log", "source_log_sha256", "record_sha256", "current_wall_line", "current_wall_evidence", "first_fatal_line", "first_fatal_evidence", "fix_ids", "recheck_ids", "prediction", "log_pass_rule", "log_fail_rule", "expected_t20", "t20_rule", "known_remaining", "preservation_control", "u4_first_sweep_lit", "condition"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in report["rows"]:
        writer.writerow({name: ";".join(value) if isinstance(value, list) else value for name, value in row.items() if name in fields})
    return stream.getvalue().encode()


def render(report):
    lines = ["# Frozen J6 + N4 predictions (66 keys)", "",
        "The earlier mistake was equating shipped symbols or missing error text with a passed wall, and a passed wall with a new light. This prospective sheet freezes checkpoint predictions and separate t20 expectations **before the combined batch**, not after reading its outcomes.", "",
        "## Scope and forecast", "", report["scope"], "", report["baseline_note"], "",
        "- Predictions: " + json.dumps(report["counts"]["predictions"], ensure_ascii=False) + ".",
        "- Primary checkpoint instances: " + json.dumps(report["counts"]["primary_checkpoints"]) + ". Metadata overlaps one owner key; do not add checkpoint counts as distinct apps or lights.",
        "- Alarm split rechecks: fd-k9 and fd-android. These remain UI preservation controls.",
        "- No unconditional new-light forecasts. `过墙` is the stated operational checkpoint, `不变` is exact-wall persistence or reviewed UI preservation, `unknown` is explicitly unforecastable. `点亮` is reserved for a genuine own-UI forecast; none is justified here.",
        "- fd-noice is an unresolved mandatory restoration gate, not an invented N4 fix; noice is another APK of the same package. Unknown prediction does not waive the restoration release gate.",
        "- Bitmap, boot APIs/TagSoup, theme/resource and real WebView-provider work are NOT included. Musicplayer query can improve while bitmap still fails.", "",
        "## Freeze and pre-run binding", "",
        "CSV, this Markdown, criteria.json and predict.py are SHA-frozen in `scoring-inputs/J6N4-predictions-reference.json`; `J6N4-PREDICTIONS.sha256` is the portable check list. The board ACK repeats the CSV SHA and actual freeze time. Historical SCORING files are untouched.", "",
        "Final J6/N4 artifacts are not yet bound by this forecast. Before the first combined-batch run, cx-t0/outer must add a separate dated receipt binding this reference/CSV SHA to final JAR SHA, native generation manifest SHA, exact changed-unit/patch coverage, APK+sidecar cohort manifest, both RUNTIME/BOOTIMAGE fingerprint files and the frozen-gate receipt. Missing approved fixes or changed input identities are a different candidate, not a free prediction edit. Do not overwrite this frozen reference to fill in artifact hashes. A revised prediction requires a new named version, separate SHA and pre-run ACK. No retrospective revision is prospective.", "",
        "## Log checkpoints", "",
        "All witnesses must belong to the APK/package-bound target PID and relevant execution episode. Reject OH_RegHook registration text as a call-level witness, unrelated processes, truncated logs and absent-only success. These are criteria, not claims that every requested trace already exists; absent required instrumentation means unknown, not success.", ""]
    for ident, check in report["checkpoints"].items():
        lines += ["### " + ident, "", "- Positive: " + check["positive"], "- Failure: " + check["fail"], "- Limit: " + check["limit"], ""]
    lines += ["## Per-key frozen table", "",
        "`L` is the original U4 hilog line, not a proposed future line number. The CSV and criteria.json carry full paths, SHA, original text, separate first-fatal witnesses and each row's log/t20 rules. First wall means the first supported causal/precursor wall among archived signatures, not a claim to have discovered every earlier warning. Caught precursors and the first fatal must not be conflated.", "",
        "| Key | Current first wall / evidence | Fix or recheck | Forecast | Log criterion | t20 expectation |",
        "|---|---|---|---|---|---|"]
    for row in report["rows"]:
        fix = ", ".join(row["fix_ids"] + row["recheck_ids"]) or "None for current wall"
        evidence = "L" + str(row["current_wall_line"]) if row["current_wall_line"] else row["first_wall_kind"]
        log = "+".join(row["fix_ids"] + row["recheck_ids"]) or ("UI-PRESERVE + target bind/log capture" if row["preservation_control"] else "EXACT-OLD-WALL" if row["prediction"] == "不变" else "OBSERVE-ONLY / no automatic hit")
        lines.append(f"| {row['key']} | {row['current_first_wall']} ({evidence}) | {fix} | {row['prediction']} | {log} | {row['expected_t20']} |")
    lines += ["", "## Post-run scoring protocol (not yet executed)", "",
        "1. Verify the frozen SHA list and the separate pre-run candidate binding. Preserve all 66 rows, including the three original host-input failures; replaced APKs/sidecars or mixed generations remain unknown for this cohort.",
        "2. Freeze the selected FIRST scheduled attempt per key before reviewing outcomes; retain record/log/t20 hashes. Interrupted attempts may have explicitly indexed continuations, not cherry-picked better repeats. Scope logs by bindApplication package/PID as SCORING does; retain raw line numbers and normalize only timestamps/addresses as appropriate.",
        "3. Score each named checkpoint independently: actual old error on an exercised path = false_positive for a promised advance; positive execution witness past the checkpoint = hit; earlier masking, missing identity/logs, absence-only evidence = unknown. A later wall can coexist with a hit and is separately a missed-wall/false-negative feedback item. Preserve narrower field-contract/ABI advances separately when the operational checkpoint still fails.",
        "4. Aggregate a multi-checkpoint key (Element) as hit only when ALL primary checks pass; any evidenced failed primary promise makes it false_positive, otherwise unknown. Keep per-wall outcomes so metadata and owner never mask each other. Alarm rechecks are separate auxiliary verdicts, not extra lights or a change to the preservation forecast.",
        "5. For unchanged-wall rows, exact old wall reproduced = hit; positive proof of crossing it = false_positive of the unchanged prediction; absence/unlit alone = unknown. For preservation controls, a complete outer-reviewed first t20 decides hit/false_positive; missing screenshot or review = unknown. `unknown` forecasts stay outside the evaluable prediction denominator even if their actual outcome is recorded.",
        "6. Outer reviews APK-matched t20 content. Record actual UI for every key independently from checkpoint score; classify new light, restored old light or protection by baseline identity, never by process survival. AntennaPod/Notes repeats and the unresolved Noice gate are reported separately from first-attempt counts. Both Noice APKs must never become two restoration credits.",
        "7. Write a NEW scoring report (e.g. J6N4-SCORING.md/json), per-key and per-wall hit/false_positive/unknown, plus newly observed missed signatures. Keep denominator counts explicit; do not reinterpret checkpoint accuracy as lighting accuracy. `score_reviewed` supplies a unit-tested decision function for audited summaries, not an automatic raw-log or screenshot judge.", "",
        "## Reproduce", "", "```sh",
        "python3 benchmark/2026-09-30-u4-sweep/j6n4-predictions/predict.py --out /tmp/j6n4-predictions-new",
        "python3 benchmark/2026-09-30-u4-sweep/j6n4-predictions/predict.py --verify",
        "python3 benchmark/2026-09-30-u4-sweep/j6n4-predictions/test_predictions.py -v", "```", "",
        "Pinned source commits/paths/SHA are listed in `j6n4-predictions/criteria.json`. No future batch measurements were read; no device commands were executed."]
    return "\n".join(lines) + "\n"


def score_reviewed(row, observed):
    if not observed.get("identity_and_capture_valid") or row["prediction"] == "unknown":
        return "unknown"
    if row["prediction"] == "过墙":
        checks = [observed.get("checkpoints", {}).get(ident, {}) for ident in row["fix_ids"]]
        if any(check.get("state") == "old-wall" and check.get("evidence") for check in checks):
            return "false_positive"
        return "hit" if checks and all(check.get("state") == "crossed" and check.get("evidence") for check in checks) else "unknown"
    if row["preservation_control"] or row["prediction"] == "点亮":
        if not observed.get("t20_sha256") or not observed.get("outer_review") or not isinstance(observed.get("own_ui"), bool):
            return "unknown"
        return "hit" if observed["own_ui"] else "false_positive"
    if observed.get("old_wall_evidence"):
        return "hit"
    return "false_positive" if observed.get("crossing_evidence") else "unknown"


def verify_freeze(base, reference):
    if reference.get("cohort") != 66 or set(reference.get("files", {})) != set(FROZEN_FILES):
        raise ValueError("incomplete frozen reference")
    for name, expected in reference["files"].items():
        if sha((base / name).read_bytes()) != expected:
            raise ValueError("frozen SHA mismatch: " + name)


def freeze(base, reference_path):
    if reference_path.exists() or (base / "J6N4-PREDICTIONS.sha256").exists():
        raise ValueError("freeze already exists")
    reference = dict(schema=1, frozen_at=datetime.now(timezone.utc).isoformat(),
        status="forecast-content-frozen; candidate-binding-pending", cohort=66,
        files={name: sha((base / name).read_bytes()) for name in FROZEN_FILES},
        candidate_binding="Separate dated receipt required before first combined-batch run; do not mutate this reference",
        scoring_status="not-run; no J6N4 measurements available")
    reference_path.write_text(json.dumps(reference, indent=2) + "\n")
    (base / "J6N4-PREDICTIONS.sha256").write_text("".join(value + "  " + name + "\n" for name, value in reference["files"].items()))
    return reference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--out", type=Path)
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    reference_path = SWEEP / "scoring-inputs/J6N4-predictions-reference.json"
    if args.verify:
        verify_freeze(SWEEP, json.loads(reference_path.read_text()))
        print("PASS frozen forecast bytes")
        return
    if args.freeze:
        report = build()
        if (SWEEP / "J6N4-PREDICTIONS.csv").read_bytes() != csv_bytes(report) or (SWEEP / "J6N4-PREDICTIONS.md").read_text() != render(report) or json.loads((HERE / "criteria.json").read_text()) != report:
            raise ValueError("published forecast differs from generator")
        print(json.dumps(freeze(SWEEP, reference_path)))
        return
    if args.out.exists():
        parser.error("choose a new output directory")
    report = build()
    args.out.mkdir(parents=True)
    (args.out / "J6N4-PREDICTIONS.csv").write_bytes(csv_bytes(report))
    (args.out / "J6N4-PREDICTIONS.md").write_text(render(report))
    (args.out / "criteria.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
