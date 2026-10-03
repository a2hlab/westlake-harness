from common import ASSEMBLY, HERE, MASTER, PRIOR, REPO, load, save, sha

LAYOUT = "| **`benchmark/2026-10-03-u15-outer-review-packet/`** | **NSD8/trampoline5 exact DEX/source contracts, strict 204-row rebind (198 equal and six source-line shifts), guarded outer G2 commands and calibrated Jitsi ANL observers; no gate writes.** |"
DIGEST = "- U15 strict rebind (2026-10-03,cx-bms): auto-identical drops evidence line/sequence; exact 204-row comparison retains them and yields 198 equal + six N1 source-line shifts, zero new findings. ANL b96a is Jitsi routing, not mechanical relink; fd-meet is absent from U16 matrix and selected U13 signoffs, which proves no current coverage, not lit. See benchmark/2026-10-03-u15-outer-review-packet/."


def replay_commands():
    wrapper = MASTER / "scripts/lab/oatdump_remote.sh"
    replay = ASSEMBLY / "replay-production.sh"
    commands, variants = [], {}
    lines = ["# Outer-owned G2 / production replay", "", "Not executed by this packet. No lock, install, apply or promotion.",
        "The entry refuses without `U15_PRODUCTION_REPLAY=outer-approved`. Outer must finish exact-add and registry review first.",
        "These BASEs are candidate U14 content, not promotion attestations. After U14 promotion, rebind with its actual per-board armed BASE and regenerate commands; do not replace a BASE argument without rebinding the U15 package.", "",
        "VM entry sets `.vm-tools` PATH, shared TMPDIR and MAC_HOME. The remote oatdump wrapper is outer-owned; no historical G2 result is borrowed.", ""]
    lines += ["```sh", ': "${WORKSPACES:?set the shared workspace root before invoking these commands}"', "```", ""]
    for variant in ["common", "61b"]:
        composition = load(PRIOR / variant / "composition.json")
        variants[variant] = {key: composition[key] for key in ["package", "bundle_sha256", "transaction_base", "transaction_base_sha256"]}
        for surface in ["mac", "vm"]:
            argv = ["bash", str(replay), surface, composition["transaction_base"], composition["transaction_base_sha256"], composition["package"], str(wrapper)]
            if surface == "vm":
                argv = ["orb", "-m", "a2hlab", "env", "U15_PRODUCTION_REPLAY=outer-approved"] + argv
            else:
                argv = ["env", "U15_PRODUCTION_REPLAY=outer-approved"] + argv
            from common import portable
            argv = portable(argv)
            command = " ".join('"' + arg + '"' if "$" in arg else arg for arg in argv)
            commands.append(dict(variant=variant, surface=surface, argv=argv, command=command, executed=False))
            lines += ["## " + variant + " / " + surface, "", "```sh", command, "```", ""]
    (HERE / "g2-replay-commands.md").write_text("\n".join(lines))
    save("g2-replay-commands.json", dict(commands=commands, variants=variants,
        entry=dict(path=replay, sha256=sha(replay)), oatdump=dict(path=wrapper, sha256=sha(wrapper)),
        executed=False, authority="outer only; exact-add/registry approvals pending and U14 actual promotion BASE not attested", execution_enabled=False))


def main():
    classes = load(HERE / "classes.json")
    registry = load(HERE / "registry-comparison.json")
    anl = load(HERE / "anl-review.json")
    replay_commands()
    lines = ["# Thirteen exact-add class contracts", "", "U14 comparison: 0 identical classes in this added set, 13 absent-to-added, 0 unexpected additions/drops/reshapes. Source git blobs: 13/13 exact matches.",
        "", "NSD8 jointly serves fd-immich (cluster K), not eight independent moves. NSD alone leaves its later ATrace failure. Full U15 also supplies Flutter ATrace; one conditional shared first-fatal move, next raster wall/unknown.",
        "Trampoline5 serves all 36 measured start/finish keys in `evidence/trampoline-keys.txt`; cluster M x is a timing/content target, zero predicted first-fatal moves. The fd-api theme patch is a separate existing-class repair, not credit for these five additions.", ""]
    for row in classes["classes"]:
        source = row["source"]
        lines += ["## `" + row["descriptor"] + "`", "", "- Parent: `" + row["superclass"] + "`; interfaces: " + (", ".join("`" + item + "`" for item in row["interfaces"]) or "none") + ".",
            "- Source: `" + source["path"] + "` @ `" + source["commit"] + "`; SHA256 `" + source["sha256"] + "`.",
            "- Raw DEX contract: `" + row["raw_dexdump"] + "`; exact U14 absent→U15 diff: `" + row["per_class_diff"] + "`.",
            "- Served keys: " + ", ".join(row["prediction"]["served_keys"]) + ".", "", "| Method | Access |", "|---|---|"]
        lines += ["| `" + method["signature"] + "` | " + method.get("access", "not present") + " |" for method in row["methods"]]
        if not row["methods"]:
            lines.append("| none (annotation contract) | no methods in DEX |")
        lines += ["", row["prediction"]["after"], ""]
    lines += ["## Donor boundary", "", "NsdServiceInfo is the AOSP Connectivity android-14.0.0_r1 donor (bd692130a596b4e9bc1ea6778db72c423bb8ab6f). NsdManager keeps compatibility contracts; its five service methods still throw UnsupportedOperationException and registration is empty. This is link coverage, not working DNS discovery.", ""]
    (HERE / "class-review.md").write_text("\n".join(lines))
    lines = ["# Strict finding rebinding", "", "204 mapped rows: **198 strictly equal / 6 different / 0 new / 0 unmapped**.",
        "N1: 93 equal, 6 source-line shifts. N2: 105 equal, 0 differences.",
        "Only issue_id/disposition/exception envelopes are removed. Manifest/input identities are compared separately. All actual finding fields, trace entries, line numbers and sequence remain in the comparison; issue IDs are independently recomputed.",
        "", "The previous auto-identical helper drops numeric `line` and `sequence` recursively. That result does not satisfy this task's strict field equality. Six rows require explicit outer review; no exception row is applied here.",
        "", "| Old ID | New ID | Actual changed fields |", "|---|---|---|"]
    for row in registry["rows"]:
        if not row["strict_equal"]:
            delta = "; ".join(item["path"] + ": " + str(item["old"]) + "→" + str(item["new"]) for item in row["differences"])
            lines.append("| `" + row["old_issue_id"] + "` | `" + row["new_issue_id"] + "` | " + delta + " |")
    lines += ["", "Host main/plugin_handle: frozen n4-host.c line660→665. Five EGL cache findings: frozen egl.cpp evidence lines103/105/109/113/117→111/113/117/121/125; their registration trace549→557 and nativeClassInit133→141. Every old/new cited line was read from its SHA-checked scan-manifest source and matched exact text (`evidence_source_proofs`). Text, namespace, library, reason, source identity and sequence are unchanged; line differences remain differences.",
        "", "`registry-comparison.json` retains all 204 complete old/new findings and named-field proofs. Missing N2 function/evidence fields are explicitly absent, not invented as source proof. `registry-mapping.csv` is the complete ID mapping. `changed-findings.json` isolates all six rows and every changed trace line.", ""]
    (HERE / "registry-review.md").write_text("\n".join(lines))
    lines = ["# ANL dual-alias observer calibration", "", "**Not a mechanical relink.** U14 eebd62f2→U15 b96a8991 adds `org.jitsi.meet` to native_cluster_path; ANL_Dlopen uses this result to select westlake_native. Fresh strings: exactly one ADDED, no dropped. Fresh disassembly: package-bound comparisons x28/x24 #0xc→#0xd (13→14); the callback-indirect scanner's zero opens is not proof of zero loader behavior.",
        "", "- Actual artifact: `libapp_native_loader.so`, root and route aliases, both b96a8991ef5a2a6e800029aed968b2442f50786466ac2a1a19979959b56d8bbc.",
        "- Source/patch commit: a559672a65b2e719a85eb7cc3760e875f9935fe5; `src/anl/app_native_loader.c:66`, `src/anl/app_native_loader-vs-n3.diff`, and paired `src/host-u15-vs-jitsi.diff` in u15-jitsi-native-domain. All committed source snapshots match git blobs.",
        "- Host final source is the recipe-produced persistent u15jitsi-stock-host.c, not its unpatched input. Host9e3ad72e adds the same package and needs_runtime publication; **both host and ANL ship/rollback together**. westlake_native ABI f8619ad5 supplies the missing LIBC imports.",
        "", "## First-fatal calibration", "", "Current `u16-wall-clusters/clusters.csv`: 19 clusters, **0 rows / 0 keys covering fd-meet or meet**. Neither key appears in the four selected U13 outer signoffs. Absence does not prove lit: current first-fatal is unknown, current matrix-covered moves=0 and measured moves=0. Do not borrow cluster A's four Flutter movers to observe a Jitsi-only change.",
        "", "Historical fd-meet eligibility is **1 conditional move**, not a current U16 measured mover: window5 public Hermes/React Native atfork failures at hilog25374/25376, fallback libc++ abort import25507, main terminal25527. Paired route+global ABI is expected to clear both public and fallback relocations. Next RN/Hermes/WebRTC/owner wall unknown; no lit prediction. Donor replay has 12/13 zero missing imports; libjsctooling requires missing libjsc and is not startup Hermes evidence.",
        "", "## Existing现场 markers", "", "There is **no new ANL-specific route marker**. Paired host emits:", ""]
    for marker in anl["markers"]:
        lines += ["- `" + marker["marker"] + "` in final source SHA `" + marker["source_sha256"] + "`: " + "; ".join(str(item["line"]) + " `" + item["text"].strip() + "`" for item in marker["lines"]) + "."]
    lines += ["", "N2's namespace label is not necessarily the package literal: require search/permitted paths containing /org.jitsi.meet/ and westlake_native plus the matching ABI global-ready event. N3 unavailable is failure, not success; published means the host publication succeeded, not that ANL b96a was loaded. Pair logs with exact loaded-ANL identity and selected ABI owner/consumer relocation evidence, then compare public/fallback first_fatal. Respect signed copy ceilings; do not substitute the upstream one-runtime wish for the accepted baseline bounds.",
        "", "Recommended outer observation request: **fd-meet/org.jitsi.meet** with these conditions and historical first-fatal reference. This packet does not change a window key list, grant approval, claim a new terminal result or add a log candidate.", ""]
    (HERE / "anl-review.md").write_text("\n".join(lines))
    records = load(HERE / "collection-runs.json")["records"] + anl["records"]
    if (HERE / "validation-runs.json").exists():
        records += load(HERE / "validation-runs.json")["records"]
    if (HERE / "preflight.json").exists():
        records += load(HERE / "preflight.json")["records"]
    save("results.json", dict(class_comparison=classes["comparison"], source_matches=13,
        registry=dict(count=204, strictly_equal=198, different=6, new_findings=0, applied=False),
        anl=dict(mechanical_relink=False, u16_covered_moves=0, measured_moves=0, conditional_historical_moves=1,
            key="fd-meet", current_first_fatal="unknown: outside selected matrix/signoffs", own_new_marker=False, paired_host_required=True),
        commands=records, production_gates_passed=False, execution_enabled=False, window_authorized=False,
        active_tables_written=False, device_access=False, vm_used=False,
        pending="Outer 13 exact-add review, six strict line-shift reviews and 204 rebindings; actual per-board U14 promotion BASE plus outer Mac/VM/oatdump replay"))
    (HERE / "gate-exits.md").write_text("# Fresh command exits (not production PASS)\n\n| Evidence | Exit |\n|---|---:|\n" +
        "\n".join("| `" + row["evidence"].split("/")[-1] + "` | " + str(row["exit_code"]) + " |" for row in records) + "\n")
    save("documentation.json", {"README.md": [LAYOUT], ".octos/KNOWLEDGE-DIGEST.md": [DIGEST]})
    paths = sorted(str(path.relative_to(REPO)) for path in HERE.rglob("*") if path.is_file()
        and ".artifacts" not in path.parts and "__pycache__" not in path.parts and not path.name.startswith(".")
        and path.name not in ["landing-paths.txt", "listing-receipt.json"])
    paths += [str(path.relative_to(REPO)) for path in (REPO / "specs/u15-outer-review-packet").glob("*.spec.md")]
    paths += ["tools/spec-checks/tests/u15_outer_review_packet.rs", str((HERE / "listing-receipt.json").relative_to(REPO))]
    paths = sorted(set(paths))
    (HERE / "landing-paths.txt").write_text("\n".join(paths) + "\n")
    save("listing-receipt.json", dict(paths=len(paths), sha256=sha(HERE / "landing-paths.txt"), execution_enabled=False))
    print("classes source=13/13 added=13 equal=0 unexpected=0; registry equal=198 changed=6 new=0; landing=" + str(len(paths)))


if __name__ == "__main__":
    main()
