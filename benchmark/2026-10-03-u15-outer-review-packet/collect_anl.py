import csv
import difflib
from pathlib import Path
import shutil
import sys

from collect import git_source
from common import HERE, MASTER, PRIOR, WS, capture, expand, load, save, sha
import generation_bundle as bundle
import generation_static_checks as static

COMMIT = "a559672a65b2e719a85eb7cc3760e875f9935fe5"
DONOR = "benchmark/2026-10-03-u15-jitsi-native-domain/"
OLD = "eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c"
NEW = "b96a8991ef5a2a6e800029aed968b2442f50786466ac2a1a19979959b56d8bbc"


def main():
    composition = load(PRIOR / "common/composition.json")
    package, baseline = expand(composition["package"]), expand(composition["transaction_base"])
    old_rows, new_rows = static.effective(baseline), static.effective(package)
    targets = sorted(target for target in new_rows if target.endswith("/libapp_native_loader.so"))
    if len(targets) != 2:
        raise ValueError("Exactly two ANL aliases required")
    aliases = []
    for target in targets:
        old, new = bundle.member(baseline, old_rows[target]), bundle.member(package, new_rows[target])
        if (sha(old), sha(new)) != (OLD, NEW):
            raise ValueError("Exact ANL pair changed")
        aliases.append(dict(target=target, old=old, new=new, old_sha256=OLD, new_sha256=NEW))
    sources = [git_source(DONOR + path, COMMIT) for path in [
        "src/anl/app_native_loader.c", "src/anl/flutter_domain.inc", "src/anl/app_native_loader-vs-n3.diff",
        "src/host-u15-vs-jitsi.diff", "recipe/build_u15j_host.py", "inputs/candidate-stock-host.c"]]
    release = WS / "westlake-inputs/generations/u15-jitsi-native-domain-v1"
    host_source = release / "u15jitsi-stock-host.c"
    host_snapshot = HERE / "inputs/source/u15jitsi-stock-host.c"
    shutil.copyfile(host_source, host_snapshot)
    host_delta = "".join(difflib.unified_diff((release / "u15base-stock-host.c").read_text().splitlines(keepends=True),
        host_source.read_text().splitlines(keepends=True)))
    added = [line for line in host_delta.splitlines() if line.startswith("+") and not line.startswith("+++")]
    if len(added) != 2 or not all("org.jitsi.meet" in line for line in added):
        raise ValueError("Host donor patch is not the two declared Jitsi lines")
    old, new = expand(aliases[0]["old"]), expand(aliases[0]["new"])
    records = [capture("anl-strings", [sys.executable, MASTER / "scripts/lab/deployed_strings_diff.py", new, "--deployed", old])]
    for label, elf in [("u14", old), ("u15", new)]:
        records.append(capture("anl-disassembly-" + label, ["llvm-objdump", "-d", "--no-show-raw-insn",
            "--disassemble-symbols=native_cluster_path,ANL_Dlopen", elf]))
        records.append(capture("anl-dynamic-" + label, ["llvm-readelf", "-d", elf]))
        records.append(capture("anl-open-" + label, [sys.executable, MASTER / "scripts/lab/open_site_scan.py", elf]))
    clusters = MASTER / "benchmark/2026-10-03-u16-wall-clusters/clusters.csv"
    cluster_rows = list(csv.DictReader(clusters.open()))
    matches = [row for row in cluster_rows if set(row["keys"].split()) & {"fd-meet", "meet"}]
    if matches:
        raise ValueError("Meet entered the current cluster matrix: recalibrate before reporting")
    cluster_snapshot = HERE / "evidence/u16-clusters.csv"
    shutil.copyfile(clusters, cluster_snapshot)
    coverage = []
    for window in range(1, 5):
        path = MASTER / f"benchmark/2026-10-03-u13-stage-a-plan/window{window}-signoff/outer-signoff.json"
        keys = load(path)["keys"]
        coverage.append(dict(path=path, sha256=sha(path), observed_keys=len(keys),
            fd_meet_present="fd-meet" in keys, meet_present="meet" in keys))
    if any(row["fd_meet_present"] or row["meet_present"] for row in coverage):
        raise ValueError("Meet observation exists; do not infer a verdict from absence")
    historical = MASTER / "benchmark/2026-10-02-u13-native-load-3/README.md"
    historical_snapshot = HERE / "evidence/meet-historical-first-fatal.md"
    historical_snapshot.write_text(historical.read_text().split("## 3. Meet:")[1].split("## Reproduction")[0])
    donor_replay = MASTER / (DONOR + "evidence/replay-fd-meet-native.txt")
    replay_snapshot = HERE / "evidence/meet-donor-native-replay.txt"
    shutil.copyfile(donor_replay, replay_snapshot)
    markers = []
    host_text = host_source.read_text().splitlines()
    host_elf = bundle.member(package, new_rows["/system/bin/appspawn-x"])
    if sha(host_elf) != "9e3ad72e1ff5de52435ce2ca91eacf5346f18aaadcdb96824b6713f3f849de09":
        raise ValueError("Required paired host changed")
    for marker in ["[N2-OWNER]", "[N3-OWNER]"]:
        if marker.encode() not in host_elf.read_bytes():
            raise ValueError("Marker absent in selected host")
        lines = [dict(line=index + 1, text=line) for index, line in enumerate(host_text) if marker in line]
        markers.append(dict(marker=marker, source=host_source, source_sha256=sha(host_source), lines=lines,
            host_sha256=sha(host_elf), emitted_by="host, not ANL", exact_anl_load_proof=False))
    save("anl-review.json", dict(aliases=aliases, source_commit=COMMIT, sources=sources,
        final_host_source=dict(path=host_source, snapshot=host_snapshot, sha256=sha(host_source)),
        paired_host_sha256=sha(host_elf), mechanical_relink=False,
        functional_delta="native_cluster_path plus org.jitsi.meet; ANL_Dlopen selects westlake_native. Disassembly changes 13-to-14 package loop bound, not just metadata.",
        required_pair="ANL b96a8991 and host 9e3ad72e must ship/rollback together; native_abi f8619ad5 already in westlake_native",
        u16=dict(source=clusters, sha256=sha(clusters), snapshot=cluster_snapshot, rows=len(cluster_rows),
            matching_rows=matches, matrix_covered_first_fatal_moves=0, absence_is_not_lit=True),
        signoff_coverage=coverage,
        prediction=dict(key="fd-meet", package="org.jitsi.meet", current_u16_first_fatal="unknown: not observed in selected signoffs/matrix",
            current_confirmed_moves=0, conditional_historical_moves=1,
            historical_terminal="SoLoader main_threw: fallback libc++_shared.so android_set_abort_message, preceded by public Hermes/React Native __register_atfork",
            historical_log_lines=[25374, 25376, 25507, 25527], historical_source=historical,
            historical_source_sha256=sha(historical), historical_excerpt=historical_snapshot,
            next_fatal="unknown: RN/Hermes/WebRTC initialization or existing owner/window walls", lit="unknown",
            donor_replay=dict(source=donor_replay, sha256=sha(donor_replay), snapshot=replay_snapshot,
                interpretation="historical static replay: 12/13 no missing imports; libjsctooling requires absent libjsc, not a new screenshot or owner oracle")),
        markers=markers, anl_new_route_marker=None,
        observation="Use fd-meet as a separately requested observation, not a U16 A-cluster mover. Check exact loaded ANL b96a identity, org.jitsi.meet native search paths and N2 global-ABI/N3 runtime logs together; markers alone do not prove ANL loaded or relocation succeeded. Retain signed copy ceilings and public/fallback first_fatal checks.",
        records=records, device_access=False, vm_used=False, approved=False, execution_enabled=False))


if __name__ == "__main__":
    main()
