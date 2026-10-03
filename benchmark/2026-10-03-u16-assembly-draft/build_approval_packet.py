import copy
import hashlib
import json
from pathlib import Path
import re


def validate_packet(root, packet):
    binding = json.loads((root / "native-pair-binding.json").read_text())
    assert packet["schema"] == "outer-gate-approval/v1"
    assert packet["signer"] is None and packet["signed_at"] is None
    assert packet["execution_enabled"] is False and packet["rollout_ready"] is False
    assert packet["gate_registry_applied"] is False
    assert packet["final_bundle_sha256"] is None
    assert packet["selected_artifacts"] == binding["changes"]
    for field in ["native_manifest_sha256", "native_inputs_sha256"]:
        assert packet[field] == binding[field]
    rows = packet["decisions"]
    expected = {"flutter-open": 4, "runtime-line-shift": 2, "runtime-call-set": 3, "strings": 8}
    assert {kind: sum(row["category"] == kind for row in rows) for kind in expected} == expected
    assert len(rows) == 17 and len({row["id"] for row in rows}) == 17
    for row in rows:
        assert row["decision"] == "pending" and row["approved_by"] is None
        assert row["recommendation"]["label"] in ["批", "不批"]
        assert row["recommendation"]["reason"] and row["basis"]
        for evidence in row["basis"]:
            relative = Path(evidence["path"])
            assert not relative.is_absolute() and ".." not in relative.parts
            data = (root / relative).read_bytes()
            assert hashlib.sha256(data).hexdigest() == evidence["sha256"], str(relative)
            if "line" in evidence:
                assert data.decode().splitlines()[evidence["line"] - 1].strip() == evidence["text"]
        def verify_excerpt(value):
            if isinstance(value, dict):
                if "excerpt" in value:
                    assert value["path"] in {item["path"] for item in row["basis"]}
                    lines = (root / value["path"]).read_text().splitlines()
                    index = value["line"] - 1
                    assert value["excerpt"] == lines[max(0, index - 4):index + 3]
                for item in value.values():
                    verify_excerpt(item)
            elif isinstance(value, list):
                for item in value:
                    verify_excerpt(item)
        verify_excerpt(row.get("disassembly"))
        if row["category"] == "flutter-open":
            assert row["open_site"]["flags"] == ["0x6=NOW|NOLOAD"]
            assert row["may_create_new_copy"] is False
            scan = json.loads((root / "evidence/u16-a3-flutter-u16-open.json").read_text())
            assert row["open_site"] in scan["binaries"][0]["sites"]
    assert packet["strings_summary"] == {"dropped": 0, "added": 8, "raw_exit_code": 1}
    return True


def main():
    import platform
    import sys
    from native_pair import FLUTTER, PAIR
    from native_stage import MEMBER
    from native_static import capture
    from prepare import HERE, MASTER, WS, save, sha

    if platform.system() != "Darwin":
        raise ValueError("Mac-only read-only review; no VM or build")
    load = lambda name: json.loads((HERE / name).read_text())
    binding = load("native-pair-binding.json")
    gates = load("native-pair-gates.json")
    review = load("native-pair-review.pending.json")
    old_review = load("native-review.pending.json")
    base = WS / binding["base"].removeprefix("$WORKSPACES/")
    registry = MASTER / "knowledge/gates/native-predeploy-exceptions.json"
    registry_before = sha(registry)
    if registry_before != gates["active_registry_sha256"]:
        raise ValueError("Active registry drift since selected raw native reports")
    for member, change in binding["changes"].items():
        if sha(base / "native" / member) != change["old"] or sha(PAIR / member) != change["new"]:
            raise ValueError("Selected artifact identity changed")

    def evidence(name, line=None):
        item = dict(path=name, sha256=sha(HERE / name))
        if line is not None:
            item.update(line=line, text=(HERE / name).read_text().splitlines()[line - 1].strip())
        return item

    records, dumps = [], {}
    symbols = [("bbq", "_ZN7android12_GLOBAL__N_116BBQ_nativeUpdateEP7_JNIEnvP7_jclasslllli"),
        ("sc", "_ZN7android12_GLOBAL__N_122sc_to_oh_native_windowEl"),
        ("get-window", "_ZN7android12_GLOBAL__N_123oh_wm_get_native_windowEi"),
        ("resolve-window", "_ZN7android12_GLOBAL__N_119resolve_oh_wm_funcsEv"),
        ("create-surface", "eglCreateWindowSurface"),
        ("split-entry", "_ZN7android34m1_native_window_from_other_copiesEPFPviEi")]
    for tag, symbol in symbols:
        versions = [("u16", PAIR / MEMBER)] if tag == "split-entry" else [("u15", base / "native" / MEMBER), ("u16", PAIR / MEMBER)]
        for version, artifact in versions:
            record = capture("approval-runtime-" + version + "-" + tag,
                ["llvm-objdump", "-d", "--no-show-raw-insn", "--disassemble-symbols=" + symbol, artifact])
            if record["exit_code"] != 0 or "<" + symbol + ">:" not in (HERE / record["evidence"]).read_text():
                raise ValueError("Requested runtime disassembly missing")
            records.append(record)
            dumps[(version, tag)] = record["evidence"]
    for tag, symbol in [("egl", "eglGetProcAddress"), ("log", "_ZL6gl_logPKc")]:
        record = capture("approval-flutter-" + tag,
            ["llvm-objdump", "-d", "--no-show-raw-insn", "--disassemble-symbols=" + symbol, PAIR / FLUTTER])
        if record["exit_code"] != 0 or "<" + symbol + ">:" not in (HERE / record["evidence"]).read_text():
            raise ValueError("Requested Flutter disassembly missing")
        records.append(record)
        dumps[("flutter", tag)] = record["evidence"]

    def call_excerpt(name, pc=None, symbol=None):
        lines = (HERE / name).read_text().splitlines()
        pattern = re.compile(r"^\s*" + pc.removeprefix("0x") + r":") if pc else None
        hits = [index for index, line in enumerate(lines) if (pattern and pattern.search(line)) or
            (symbol and "<" + symbol in line and re.search(r"\b(?:bl|b)\s", line))]
        if not hits:
            raise ValueError("Call PC or target missing from disassembly: " + name)
        return [{"path": name, "line": index + 1, "excerpt": lines[max(0, index - 4):index + 3]} for index in hits]

    flutter_source = "inputs/flutter-source-a3/src/flutter_egl_getprocaddress.cpp"
    new_source = "inputs/native-source/u13-m1-compat-shim.cpp"
    old_source = "inputs/native-source/u15-m1-compat-shim.cpp"
    split_source = "inputs/native-source/u16-m1-copy.cpp"
    flutter_scan = load("evidence/u16-a3-flutter-u16-open.json")["binaries"][0]["sites"]
    rows = []
    purposes = {38: "A2 residual GLES logging: reuse loaded runtime only to resolve HiLogPrint, matching flutter_egl n6_log ownership; miss disables logging.",
        57: "A2 glDepthRange/glClearDepth double-to-float shims and extension lookup: reuse loaded GLES2 driver; missing handle is not a loader fallback.",
        58: "A2 GLES3 fallback for the same float shims and extension lookup; no fresh library load on miss.",
        96: "A2 real platform eglGetProcAddress delegation retained after A3's four same-DSO flutter_egl EGL-name hooks; miss proceeds to existing residual resolver, not a fresh open."}
    for finding in review["added_n1"]:
        detail = finding["detail"]
        line = detail["evidence"]["line"]
        site = next(site for site in flutter_scan if site["path"] == [detail["library"]] and site["callee"] == "dlopen" and
            (site["function"] == "_ZL6gl_logPKc" if line == 38 else site["function"] == "eglGetProcAddress"))
        dump = dumps[("flutter", "log" if line == 38 else "egl")]
        rows.append(dict(id="flutter-noload-" + str(line), category="flutter-open", object=detail["library"] + " at source:" + str(line),
            decision="pending", approved_by=None, issue_id=finding["issue_id"], finding=finding,
            open_site=site, source_function=detail["function"], compiled_function=site["function"],
            origin="A2 glDepthRange interposer (b1c9); A3 only adds four EGL-name returns pointing to existing flutter_egl hooks",
            may_create_new_copy=False, no_copy_basis="Immediate w1=6 NOW|NOLOAD; resident lookup only. This does not prove handle visibility or a successful renderer. Existing older NOW-only sites are outside these four rows.",
            disassembly=call_excerpt(dump, pc=site["pc"]),
            basis=[evidence(flutter_source, line), evidence(dump), evidence("evidence/u16-a3-flutter-u16-open.json")],
            recommendation={"decision": "approve", "label": "批", "reason": purposes[line]},
            scope="Only this N1 issue and the exact four-added/no-removed/no-namespace-delta static allowance; no API/rendering success or owner visibility approval"))

    old_scan = load("evidence/u16-a3-runtime-u15-open.json")["binaries"][0]["sites"]
    new_scan = load("evidence/u16-a3-runtime-u16-open.json")["binaries"][0]["sites"]
    for index, shift in enumerate(old_review["n1_line_shifts"]):
        before, after = shift["before"], shift["after"]
        target = after["detail"]["library"]
        function = after["detail"]["function"]
        old_site = next(site for site in old_scan if site["path"] == [target] and function in site["function"])
        new_site = next(site for site in new_scan if site["path"] == [target] and function in site["function"])
        tag = "resolve-window" if index == 0 else "create-surface"
        semantic = copy.deepcopy(before)
        semantic["detail"]["evidence"]["line"] = after["detail"]["evidence"]["line"]
        if semantic != after or old_site["flags"] != new_site["flags"] or old_site["path"] != new_site["path"]:
            raise ValueError("Line-only finding or open behavior changed")
        current = next(item for item in review["shifted_n1"] if item["detail"]["function"] == function)
        rows.append(dict(id="runtime-line-" + str(index + 1), category="runtime-line-shift", object=function,
            decision="pending", approved_by=None, finding=current, issue_id=current["issue_id"],
            old_source_line=before["detail"]["evidence"]["line"], new_source_line=after["detail"]["evidence"]["line"],
            before=before, after=after, old_open_site=old_site, new_open_site=new_site,
            disassembly={version: call_excerpt(dumps[(version, tag)], pc=site["pc"]) for version, site in [("u15", old_site), ("u16", new_site)]},
            basis=[evidence(old_source, before["detail"]["evidence"]["line"]), evidence(new_source, after["detail"]["evidence"]["line"]),
                evidence(dumps[("u15", tag)]), evidence(dumps[("u16", tag)])],
            recommendation={"decision": "approve", "label": "批", "reason": "Same source statement and finding fields except source line; the split moved/deleted surrounding helper code. Both ELF calls still pass NOW|NOLOAD to the same library, with no new opening path."},
            scope="Exact line-only approval transfer to the selected partial manifest/inputs; no identity-only auto approval of other semantic changes"))

    descriptions = [
        ("bbq", [587, 597], [513, 523], "BBQ wrapper calls become direct calls to the split entry after the primary window query is inlined. SurfaceView child lookup and main-window fallback selection remain in the shim."),
        ("sc", [177], [183], "The small oh_wm wrapper is now inlined: explicit resolve_oh_wm_funcs and conditional primary query precede the split entry. The extra resolver is the old wrapper's resolver, not a new loading policy."),
        ("get-window", [525, 528], [451, 454], "HiLogPrint and dl_iterate_phdr disappear only from this wrapper's direct call set: they move to the split entry. Resolved bridge fn and sessionId are passed explicitly; scan occurs only after the primary query returns null.")]
    abi = load("evidence/u16-a3-runtime-abi.json")
    if abi["call_diffs"] != review["callset_review"]:
        raise ValueError("Raw ABI call-set list changed")
    for change, (tag, old_lines, new_lines, reason) in zip(abi["call_diffs"], descriptions):
        symbol = "_ZN7android34m1_native_window_from_other_copiesEPFPviEi"
        rows.append(dict(id="runtime-call-" + tag, category="runtime-call-set", object=change["demangled"],
            decision="pending", approved_by=None, raw_call_set_diff=change,
            disassembly={"old": dumps[("u15", tag)], "new": dumps[("u16", tag)],
                "old_removed_calls": {callee: call_excerpt(dumps[("u15", tag)], symbol=callee) for callee in change["removed_callees"]},
                "new_added_calls": {callee: call_excerpt(dumps[("u16", tag)], symbol=callee) for callee in change["added_callees"]},
                "new_split_calls": call_excerpt(dumps[("u16", tag)], symbol=symbol), "split_entry": dumps[("u16", "split-entry")],
                "moved_iterate_calls": call_excerpt(dumps[("u16", "split-entry")], symbol="dl_iterate_phdr"),
                "moved_log_call": call_excerpt(dumps[("u16", "split-entry")], symbol="HiLogPrint")},
            basis=[*[evidence(old_source, line) for line in old_lines], *[evidence(new_source, line) for line in new_lines],
                evidence(split_source, 84), evidence(split_source, 88), evidence(split_source, 90), evidence(split_source, 94),
                evidence(dumps[("u15", tag)]), evidence(dumps[("u16", tag)]), evidence(dumps[("u16", "split-entry")]),
                evidence("inputs/native-source/donor-t4/evidence/a-prime-insns.txt"), evidence("evidence/u16-a3-runtime-abi.json")],
            recommendation={"decision": "approve", "label": "批", "reason": reason},
            scope="Accept the actual nonzero three-call-set split delta; do not label it callsets0 or guarantee full function instruction equivalence. Require future three-app M1 replay before FZ-009 registration."))

    string_reasons = {"FLUTTER-GLSTUB": (42, "Log tag for once-per-name residual diagnostics; allowing the tag is not approval of successful residual GL rendering."),
        "eglGetProcAddress": (97, "Exact platform provider lookup; four existing flutter_egl hooks are returned before delegation."),
        "glClearDepth": (107, "Match desktop-double procedure name to the GLES float conversion shim."),
        "glClearDepthf": (65, "Resolve the actual GLES float backend consumed by the conversion shim."),
        "glDepthRange": (106, "Match desktop-double procedure name to the GLES float conversion shim."),
        "glDepthRangef": (60, "Resolve the actual GLES float backend consumed by the conversion shim."),
        "libGLESv2.so": (57, "Resident GLES2 owner lookup, no new DT_NEEDED or fresh open."),
        "libGLESv3.so": (58, "Resident GLES3 alternate owner lookup, no new DT_NEEDED or fresh open.")}
    string_raw = (HERE / review["strings_evidence"]).read_text().splitlines()
    if any(line.startswith("DROPPED ") for line in string_raw) or len(review["strings_raw_rows"]) != 8:
        raise ValueError("Actual strings no longer zero-drop/eight-add")
    for raw_row in review["strings_raw_rows"]:
        value = re.fullmatch(r"ADDED\s+'([^']+)'", raw_row).group(1)
        line, reason = string_reasons[value]
        rows.append(dict(id="string-" + value, category="strings", object=value, raw=raw_row,
            decision="pending", approved_by=None, operation="ADDED",
            basis=[evidence(flutter_source, line), evidence(review["strings_evidence"], string_raw.index(raw_row) + 1)],
            recommendation={"decision": "approve", "label": "批", "reason": reason},
            scope="Only this exact readonly string allowance for U15 9b82 -> selected eb90; runtime strings remain zero-drop/zero-add"))

    if sha(registry) != registry_before:
        raise ValueError("Active registry changed during review; retain logs and rebind later")
    packet = dict(schema="outer-gate-approval/v1", signer=None, signed_at=None, requested_signer="outer(claude)",
        status="pending-outer-review", review_package="benchmark/2026-10-03-u16-assembly-draft/",
        format_reference="benchmark/2026-10-03-u15-review/outer-approval-packet.json",
        native_manifest_sha256=binding["native_manifest_sha256"], native_inputs_sha256=binding["native_inputs_sha256"],
        selected_artifacts=binding["changes"], final_bundle_sha256=None, execution_enabled=False, rollout_ready=False,
        gate_registry_applied=False, active_registry_sha256=registry_before, decisions=rows,
        counts={"flutter-open": 4, "runtime-line-shift": 2, "runtime-call-set": 3, "strings": 8, "manual_rows": 17},
        strings_summary=dict(dropped=0, added=8, raw_exit_code=1),
        static_allowance_draft=dict(baseline_sha256=gates["members"]["flutter"]["baseline_sha256"],
            candidate_sha256=gates["members"]["flutter"]["candidate_sha256"], delta=review["flutter_open_delta"],
            delta_sha256=review["flutter_open_delta_sha256"], approved_by=None),
        binding_transfer="Partial native draft only. After full27 bake, recompute final manifest/inputs and issue IDs. Transfer only when all semantic/source-line/text/open-delta fields and artifact bytes remain exact; unexpected changes stop for outer review.",
        apply_when="Outer only, once all three boards are UNLOCK; registry is part of every native dispatch binding.",
        bake_status="NOT_RUN; no authorization here. Wait for window2 5ea/5cd rollback+UNLOCK and vmgr RSS<3GiB, announce on board first, reserve VM for 61b recovery when it reconnects.",
        not_approved_here="Live owner visibility, GL no-op correctness, rendering/lighting, FZ-009 registration, gate application, image baking, window or promotion authority")
    validate_packet(HERE, packet)
    save("outer-approval-packet.json", packet)
    save("outer-packet-runs.json", dict(records=records, packet_sha256=sha(HERE / "outer-approval-packet.json"),
        active_registry_before=registry_before, active_registry_after=sha(registry), execution_enabled=False,
        board_access=False, vm_access=False, native_rebuilt=False, image_bake_executed=False))
    print("OUTER PACKET:17 unsigned recommendations,0 deletions/8 additions;13 fresh disassembly commands exit0; no gate writes")


if __name__ == "__main__":
    main()
