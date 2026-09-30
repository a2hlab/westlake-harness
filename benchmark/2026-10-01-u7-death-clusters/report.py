"""Rank U7 terminal-root clusters; keep observations and repair evidence distinct."""

from collections import Counter
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re

from collect import HERE, ROOT, SCORES, select


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load():
    index = read(HERE / "evidence/index.json")
    for name, digest in index.items():
        path = HERE / name if name == "plan.json" else HERE / "evidence" / name
        if sha(path) != digest:
            raise ValueError("input evidence drift: " + name)
    intake = json.loads(gzip.decompress(base64.b64decode((HERE / "evidence/intake.json.gz.b64").read_bytes())))
    if intake["signed_scores_sha256"] != sha(SCORES / "formal-66/results.json") or intake["first_fatal_sha256"] != sha(ROOT / "scripts/lab/first_fatal.py"):
        raise ValueError("scoring or first_fatal changed")
    for quote in read(HERE / "evidence/outer-classification.json"):
        if hashlib.sha256(quote["text"].encode()).hexdigest() != quote["sha256"]:
            raise ValueError("outer quote changed")
    return intake, read(HERE / "plan.json"), read(HERE / "evidence/sources.json")


def reference(row, line, message, file="hilog.txt"):
    path = str(Path(row["record"]).with_name(file))
    return dict(file="westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/" + path, line=line, text=message)


def app_evidence(row, score):
    observed = row["evidence"]
    fatal = observed["termination"]
    terminal, root = fatal.get("terminal") or {}, fatal.get("root") or {}
    refs = []
    for event in [terminal.get("event"), root.get("event")]:
        if event:
            refs.append(reference(row, event["line"], event["message"]))
    if root.get("status") == "fault-thread-stack":
        frame = next(item for item in observed["native_frames"] if item["line"] == score["root_line"])
        reason = next(item for item in observed["witnesses"] if item["line"] == score["reason_line"])
        if root["report"]["source"] != "hilog.txt:DfxFaultLogger":
            raise ValueError("new fault source needs explicit file binding")
        refs += [reference(row, frame["line"], frame["message"]), reference(row, reason["line"], reason["message"])]
        callers = [event for event in row["causal_excerpt"] if "FlutterJNI.nativeRunBundleAndSnapshotFromLibrary" in event["message"]]
        if callers:
            refs.append(reference(row, callers[0]["line"], callers[0]["message"]))
    if not refs:
        if row["input_error"]:
            refs = [reference(row, item["line"], item["text"], "record.json") for item in row["record_error_lines"]]
        else:
            threads = row["threads"]
            refs = [reference(row, item["line"], item["message"]) for item in threads["last_main_execution"][-2:]]
            refs += [reference(row, line, "package/PID binding; no causal terminal recovered") for line in observed["binding_lines"]]
    if not refs:
        raise ValueError("row needs explicit source lines: " + row["key"])
    return dict(key=row["key"], visual=row["signed_visual"], target_pids=observed["target_pids"],
                terminal_status=fatal["status"], terminal=terminal, root_status=root.get("status", "unknown"),
                observed_wall=row["observed_wall"], evidence=refs, record_sha256=observed["record_sha256"], hilog_sha256=observed["hilog_sha256"],
                t20_sha256=observed["t20_sha256"], interval=observed["interval"],
                supplementary_hints=[reference(row, event["line"], event["message"]) for event in row["supplemental_not_root"] if any(word in event["message"] for word in ["__gnu_strerror_r", "android_dlopen_ext", "No virtual method set(Landroid/graphics/ColorMatrix;"])][-4:])


def build(intake=None, plan=None, sources=None):
    defaults = load()
    intake, plan, sources = [candidate if candidate is not None else fallback for candidate, fallback in zip([intake, plan, sources], defaults)]
    scores = {row["key"]: row for row in select(read(SCORES / "formal-66/results.json"))}
    rows = {row["key"]: row for row in intake["rows"]}
    members = [key for cluster in plan["clusters"] for key in cluster["apps"]]
    if len(intake["rows"]) != 32 or len(rows) != 32 or set(rows) != set(scores) or len(members) != 32 or len(set(members)) != 32 or set(members) != set(rows):
        raise ValueError("clusters must partition exactly the signed unlit 32")
    clusters = []
    for entry in plan["clusters"]:
        if entry["layer"] not in {"JAR", "native", "installer", "input", "window/first-frame"}:
            raise ValueError("invalid layer")
        donors = []
        for identifier in entry["source_ids"]:
            source = sources["sources"][identifier]
            if not re.fullmatch("[0-9a-f]{40}", source["commit"]) or not re.fullmatch("[0-9a-f]{64}", source["sha256"]) or not source["path"] or not source["excerpt"]:
                raise ValueError("donor needs path commit hash and excerpt")
            donors.append(dict(id=identifier, **source))
        apps = [app_evidence(rows[key], scores[key]) for key in sorted(entry["apps"])]
        clusters.append(dict(entry, count=len(apps), apps=apps, source_candidates=donors or "none",
                             n8_in_flight_keys=sorted(set(entry["apps"]) & set(plan["n8_target_keys"])),
                             layer_is_routing_not_proven_cause=entry["id"] in {"browser-disappeared", "system-exit-unknown", "bitmap-color-space", "white-B", "black-content"}))
    clusters.sort(key=lambda entry: (-entry["count"], entry["id"]))
    groups = {entry["id"]: {app["key"] for app in entry["apps"]} for entry in clusters}
    if groups["white-A"] != {"wikipedia", "fd-AppManager"} or groups["white-B"] != {"fd-app", "fd-shatteredpixeldungeon", "termux"}:
        raise ValueError("outer A/B membership changed")
    return dict(schema_version=1, status="offline-U7-unlit-cause-clusters-not-U8-unlock-promise", signed_score_sha256=intake["signed_scores_sha256"],
                population=dict(total=66, signed_own_ui=34, unlit_or_not_installed=32, clusters=len(clusters)),
                terminal_counts=dict(Counter(row["evidence"]["termination"]["status"] if not row["input_error"] else "not-launched-install-failure" for row in rows.values())),
                layer_counts=dict(Counter(entry["layer"] for entry in clusters for _ in entry["apps"])),
                n8=dict(status=plan["n8_status"], package_sha256=plan["n8_package_sha256"], target_keys=plan["n8_target_keys"],
                        caveat="11 existing candidate memberships are not 11 proven first-root repairs or guaranteed lights; BurgerKing private/root visibility remains separate"),
                main_thread_observations={key: dict(hilog=rows[key]["hilog"], **rows[key]["threads"]) for key in ["fd-app", "fd-shatteredpixeldungeon", "termux"]},
                classifications=read(HERE / "evidence/outer-classification.json"), sources_index_sha256=sha(HERE / "evidence/sources.json"),
                evidence_index_sha256=sha(HERE / "evidence/index.json"), clusters=clusters,
                limitations=["Counts describe blocked U7 samples, not independently additive repair unlocks.", "No app thread stack was sampled at t20; final logged actions cannot establish current thread state.", "Source bytes and commit checks do not establish same-wall board repair, binary provenance or safe copyability.", "No terminal means no observed terminal, not a synthetic fatal signature.", "Native Layer routing for unexplained exits and bitmap initialization is provisional, not proven low-level attribution."])


def markdown(result):
    lines = ["# U7 unlit death clusters for U8 selection", "", "## Corrected assumptions", "",
             "**32 = 66 signed samples minus 34 own-UI samples**, not 32 fatal crashes. The set includes **23 explicit terminations, two unexplained process disappearances, six alive white/black cases without an observed terminal, and one pre-launch installer failure**. First-fatal means target-PID termination then causal chain/stack, not the first warning. Existing implementations are not automatically consumer-visible or verified fixes.", "",
             "Sources: accepted `formal-66/results.json` SHA `" + result["signed_score_sha256"] + "`; all 32 original records/hilog re-read through `first_fatal.py`. Wider target-PID session analysis has the same terminal and root as the frozen click-to-t20 analysis; context counts can differ. No frozen score is changed. Noise trims context only. `clusters.json` is authoritative for machine consumption.", "",
             "## Ranked clusters", "", "Layer is work routing; rows explicitly flag unproven causal layers. N8 labels mean already in flight, not accepted U8 unlocks.", "",
             "| Wall | Count / keys | Layer | Terminal/root evidence | Reusable implementation / verification | N8 |", "|---|---|---|---|---|---|"]
    for cluster in result["clusters"]:
        evidence = "; ".join(app["key"] + ": " + ", ".join("`" + item["file"] + ":" + str(item["line"]) + "`" for item in app["evidence"][:4]) for app in cluster["apps"])
        donors = "; ".join("`" + donor["repository"] + "/" + donor["path"] + ":" + str(donor["excerpt"][0]["line"]) + "` @ `" + donor["commit"][:12] + "`" for donor in cluster["source_candidates"]) if cluster["source_candidates"] != "none" else "none"
        lines.append("| " + cluster["wall"] + " | **" + str(cluster["count"]) + "** " + ", ".join(app["key"] for app in cluster["apps"]) + " | " + cluster["layer"] + " | " + evidence + " | " + donors + "; same-wall repair: " + cluster["verified_fix"] + " | " + (", ".join(cluster["n8_in_flight_keys"]) or "not this N8 delta") + " |")
    lines += ["", "## Selection notes", "",
              "- **Native first: six Flutter keys across two walls**, already covered by N8 bundle owner/visibility work. Four field-ID aborts originate in **FlutterJNI.nativeRunBundleAndSnapshotFromLibrary / libflutter**, not a proven EGLImpl field; do not claim an EGL-only causal fix. N8 alone ran with J6; U8 must retain U7 J7b/T7d rather than install the old JAR carried in the native package. Samples can move to later API or blank-window walls, not necessarily own UI.",
              "- **libz blocks two distinct consumers**: Element Realm and BurgerKing MMKV. The private N8 alias targets Realm; it is not proof of visibility to BurgerKing. Root alias restoration is not an acceptable shortcut: N8 deliberately removed it after the ZigZag regression suspicion. McDonalds is a separate DI-null first root, not silently merged into this cluster.",
              "- **JAR candidates require diagnosis**: fd-plus has a real `ColorMatrix.set(ColorMatrix)` donor (array copy, not no-op), but its terminal root remains MapInfoLayer null. Existing account binder/theme/WebView service are reusable boundaries, not demonstrated cures for Nextcloud/AppCompat/Tutanota. App-side obfuscated nulls have `none` for verified fixes.",
              "- **Known symbol supply differs from visibility**: Jitsi cannot see `android_set_abort_message` although implementations already exist. Mindustry requires a real reachable `slCreateEngine`, not an IID-only facade. Unity's mediandk presence donor exports no media API; validate exact UND requirements first.",
              "- **Do not force unexplained exits into attractive candidates**: browsers have prior `__gnu_strerror_r` errors; PPSSPP has `android_dlopen_ext`; all are N8 targets, but neither prior errors nor later VLC theme failure replace their unknown first-terminal cause. Seal never ran; payload restoration is a separate input operation, not a proven bm fix.", "",
              "## B-class main thread at t20", "",
              "The dedicated ActivityThread binding (`CM-BIGSTACK`) identifies the Java main **TID, not PID**. Some binding lines precede the runner's clicked timestamp, so identification reads the full PID-bound session; execution tails still obey the screenshot cutoff. No t20 stack sample exists: every current thread state stays **unknown**. Last logs occur about 13.8 seconds before capture.", ""]
    for key, observation in result["main_thread_observations"].items():
        lines += ["### " + key, "", "Main threads: `" + str(observation["main_threads"]) + "`; last-log gap: **" + str(observation["silence_before_capture_seconds"]) + " s**.", ""]
        for event in observation["last_main_execution"][-3:]:
            message = event["message"]
            if len(message) > 450:
                message = message[:180] + " … " + message[-240:]
            lines.append("- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/" + observation["hilog"] + ":" + str(event["line"]) + "` — " + message)
        lines.append("")
    lines += ["Unciv/SPD end on T=8000ms decor/display-list diagnostics (`hasDL=true`, layout 1200x1920); that is not a present receipt. Termux reports **mFinished=true, mWindowAdded=false, decorClass=null**. These are different observations inside the requested B symptom parent; they do not establish a shared root or a main-thread deadlock.", "",
              "**Outer ACK(80) 07:33:49 refines B using later U7 diagnostic traces, not new frozen-sweep evidence:** B1 = Unciv/SPD: attached AdapterSurfaceView, zero frames, no successful GLThread EGL window creation; B2 = Termux: no app surface, Activity finished before adding a window. `white-B.subclusters` records the 2+1 split while retaining the requested three-key symptom parent. Why GL startup stalls or Termux finishes remains unknown. Global trace AddChild/AcquireBuffer counts are rejected as app evidence. Do not select a single repair for all three.", "",
              "**Refinement cutoff: ACK(80) 07:42:35.** Raw later-run PID-bound lines show the GLThread did call `EGLImpl._eglCreateWindowSurface` and received the valid-Surface `IllegalArgumentException`; missing hijack-layer logs do not imply no upstream call. Both B1 apps have this exception. `subclusters[].raw_followup_evidence` pins gzip/uncompressed SHA and numbered excerpts. Termux has successful TerminateAbility/finishActivity before window addition; why remains unknown. Its IFACE-BITS method listing is not itself a dynamic invocation receipt. These later-run diagnostics do not manufacture a fatal event in the original sweep.", "",
              "## A/B authority and implementation provenance", "",
              "Outer ACK(80) **07:09:08** assigns Wikipedia/AppManager to A, Unciv/SPD/Termux to B and Mobile to black/black. **07:10:15** validates Wikipedia build-order/frame-parent correlation, but rejects attributing the 846 bridge to an unrelated newer source tree. Latest **07:32:08** withdraws the lifecycle-gate theory: two Activity RS surfaces exist but only one gets an EGL surface; a process-global current-window shim remains an unproven hypothesis. A belongs to #80; the old `oh61-v7-b2133b5b` source is only a reference, no verified drop-in race repair. Invalid x/BurgerKing follow-up captures are not used to modify U7 first-attempt results.", "",
              "`evidence/sources.json`: three local source repositories plus harness candidate snapshots; each donor has repository/path, exact commit, last-change commit, SHA256, numbered excerpt and scope limitation. Tracked historical source absent from the current checkout is explicitly labeled `worktree_file_exists=false` and recovered with git show, not described as an active file. The audit records 36 tracked-code keyword searches; none means no verified reusable same-wall fix found in this scope, not proof of universal absence.", "",
              "## Offline replay", "", "```sh", "python3 benchmark/2026-10-01-u7-death-clusters/collect.py > /tmp/u7-deaths-raw.json", "python3 benchmark/2026-10-01-u7-death-clusters/source_audit.py > /tmp/u7-deaths-sources.json", "python3 benchmark/2026-10-01-u7-death-clusters/report.py > /tmp/u7-deaths.json", "cmp /tmp/u7-deaths.json benchmark/2026-10-01-u7-death-clusters/clusters.json", "python3 benchmark/2026-10-01-u7-death-clusters/test_clusters.py", "```", "",
              "Original logs remain under the named sibling worktree run root; record/log/image/process hashes are retained in the compressed JSON intake. The source collector is read-only. See `landing-paths.txt`, `documentation.json` and `validation.json` for exact scoped delivery and isolated-master gates. No runtime/source patch, device command, frozen-CSV edit or push.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    result = build()
    print(markdown(result) if "--markdown" in sys.argv else json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2), end="" if "--markdown" in sys.argv else "\n")
