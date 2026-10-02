import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from collect import BASE, HERE, MASTER, REPO, WS, portable, run, save, sha


def main():
    receipt = json.loads((HERE / "build-receipt.json").read_text())
    reports = {name: json.loads((HERE / "evidence" / ("open-" + name + ".json")).read_text()) for name in ["deployed", "candidate"]}
    before = (HERE / "inputs/baseline-stock-host.c").read_text()
    after = (HERE / "inputs/candidate-stock-host.c").read_text()
    inherit = lambda text: re.findall(r"dlns_inherit\s*\([^;]+;", text)
    if inherit(before) != inherit(after):
        raise ValueError("reviewed patch changed namespace inherit calls")
    pairs = []
    for left, right in zip(reports["deployed"]["binaries"][0]["namespace_edges"], reports["candidate"]["binaries"][0]["namespace_edges"]):
        if left["callee"] != right["callee"]:
            raise ValueError("namespace edge sequence changed")
        if left["callee"] == "dlns_inherit":
            pairs.append(dict(before=left, after=right, source_call_unchanged=True,
                              note="stack slots / unresolved expression formatting may differ; raw scan is retained, not identity-guessed"))
    save("namespace-delta.json", dict(before_sites=len(reports["deployed"]["binaries"][0]["sites"]),
         after_sites=len(reports["candidate"]["binaries"][0]["sites"]), before_edges=17, after_edges=17,
         inherit_pairs=pairs, new_inherit_calls=0,
         inherit_repeat={name: sum(row["kind"] == "INHERIT-REPEAT" for row in report["findings"]) for name, report in reports.items()},
         inherit_after_open={name: [row for row in report["findings"] if row["kind"] == "INHERIT-AFTER-OPEN"] for name, report in reports.items()},
         source_keeps_original_private_branch="strncmp(u11_original_search" in after))
    provider = Path(receipt["provider"]["path"].replace("$WORKSPACES", str(WS)))
    alias = Path(receipt["alias"]["path"].replace("$WORKSPACES", str(WS)))
    consumer = REPO / "benchmark/2026-10-02-u12-disappeared/.artifacts/burgerking-libmmkv.so"
    consumer_sha = "d19d1957775da5ad1669cf43ed66a57d207586622fe440d749003f27ae74cc07"
    if sha(consumer) != consumer_sha:
        raise ValueError("actual mmkv consumer drift")
    exported = set(subprocess.check_output(["llvm-nm", "-D", "--defined-only", "--format=just-symbols", provider], text=True).splitlines())
    imports = set(subprocess.check_output(["llvm-nm", "-D", "--undefined-only", "--format=just-symbols", consumer], text=True).splitlines())
    zlib_required = sorted(name for name in imports if re.match(r"^(adler32|crc32|inflate|deflate|compress|uncompress|zlibVersion|zError)", name))
    if set(zlib_required) - exported or not zlib_required:
        raise ValueError("actual required zlib API not provided")
    run("mmkv-dynamic", ["llvm-readelf", "-d", "-V", consumer])
    save("consumer.json", dict(path=portable(consumer), sha256=consumer_sha, needed="libz.so",
         required=zlib_required, missing=[], provider_sha256=sha(provider),
         limitation="only the zlib imports/NEEDED are proven; not a full libNitroMmkv relocation or JNI_OnLoad success proof"))
    donor_root = WS / "01.OH61AOSP16/real-work"
    script = "src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/build_route_a_generation_in_container.sh"
    source = subprocess.check_output(["git", "-C", donor_root, "show", "be16148da9ae7bb89c62e81e144ed0bceb5c4669:" + script], text=True)
    lines = source.splitlines()
    (HERE / "evidence/r109c-alias-recipe.txt").write_text("\n".join(str(number) + ": " + line for number, line in enumerate(lines, 1) if 581 <= number <= 597) + "\n")
    save("sources.json", dict(lookup="local reviewed source and existing deployed/donor bytes found; no remote fallback required",
         reviewed_route=dict(benchmark="benchmark/2026-10-02-u11-native-batch/", source_sha256=receipt["reviewed_source_sha256"]),
         alias_recipe=dict(repository=portable(donor_root), commit="be16148da9ae7bb89c62e81e144ed0bceb5c4669", path=script,
                           sha256=hashlib.sha256(source.encode()).hexdigest(), first_line=581),
         provider=dict(path=portable(provider), sha256=sha(provider), unchanged_deployed_donor=True,
                       provenance_limit="Do not label ROUTE_A_INPUTS provider-v12 dependency d88df as this deployed ab082 ELF; no provider rebuild performed.")))
    sys.path.insert(0, str(MASTER / "scripts/lab"))
    from native_needed_gate import ElfReader, scan_domains
    libc = WS / "westlake-inputs/oh61-link-inputs/system-lib64/ld-musl-aarch64.so.1"
    virtual = {"/system/android/lib64/westlake_native/libz.so": dict(path=alias, sha256=sha(alias), package_path="private/libz.so"),
               "/system/android/lib64/westlake_native/libshared_libz.z.so": dict(path=provider, sha256=sha(provider), package_path="private/libshared_libz.z.so"),
               "/system/lib64/libc.so": dict(path=libc, sha256=sha(libc), package_path="factory/libc.so")}
    directories = ["/system/android/lib64/westlake_native", "/system/lib64"]
    domains = [dict(name=name, library_dirs=[directory], search_paths=[directory], permitted_paths=[directory])
               for name, directory in zip(["private-fixed-no-inherit", "factory-context"], directories)]
    n2_findings, n2_report = scan_domains(virtual, domains, ElfReader("llvm-readelf"))
    save("focused-n2.json", dict(findings=n2_findings, report=n2_report,
         scope="original fixed private paths, no inherit; runtime app paths/owner resolution not proven",
         exception_approved=False, note="alias resolves exact private provider; provider libc requires existing owner inheritance; do not add a private libc copy"))
    if len(n2_findings) != 1 or n2_findings[0].get("needed") != "libc.so":
        raise ValueError("unexpected focused private closure")
    targets = {"payload/runtime/appspawn-x": dict(candidate=receipt["artifacts"]["candidate1"]["path"], sha256=receipt["artifacts"]["candidate1"]["sha256"],
               before=receipt["deployed_sha256"], rollback="restore exact r3 65cc3535 bytes"),
               "payload/android/lib64/westlake_native/libz.so": dict(candidate=receipt["alias"]["path"], sha256=sha(alias), before=None, rollback="remove only this newly added private alias"),
               "payload/android/lib64/westlake_native/libshared_libz.z.so": dict(candidate=receipt["provider"]["path"], sha256=sha(provider), before=None, rollback="remove only this newly added private provider copy; keep existing root provider")}
    for name, row in targets.items():
        if row["before"] is None and (BASE / name).exists():
            raise ValueError("rollback assumption wrong: " + name)
    save("payload-edit.json", dict(execution_enabled=False, targets=targets, rebuilt_runtime_files=1,
         unmodified_existing_donor_files_copied=2, forbidden_root_alias="payload/android/lib64/libz.so",
         policy_shared_sonames_changed=False, final_package_sidecars_and_exception_rebind_required=True))
    prior = json.loads((REPO / "benchmark/2026-10-02-u12-disappeared/observations.json").read_text())
    row = next(row for row in prior["rows"] if row["key"] == "burgerking")
    save("results.json", dict(key="burgerking", predicted_first_fatal_moved=1,
         current_wall="libmmkv NEEDED libz missing in westlake.anl.app.570.3 -> NitroMmkv ULE -> exit1",
         evidence=dict(path=row["run"] + "/hilog.txt", lines=[19583, 19584, 19585, 19587, 19919]),
         candidate_sha256=receipt["artifacts"]["candidate1"]["sha256"], next_first_fatal="unknown", t20="unknown",
         also_targeted_but_not_counted=["fd-im-vector-app"], no_source_rewrite=True, two_builds_identical=True,
         namespace_delta="8 sites/17 edges unchanged; four inherit calls unchanged, zero repeats; four existing may-paths remain",
         consumer_coverage="actual libmmkv zlib imports present; remaining NitroMmkv/JNI/private-owner behavior unverified",
         execution_enabled=False,
         expect=dict(confirm="U11-ZLIB-ROUTE matches BurgerKing app namespace and libz->private exact provider resolves; old libz-missing root absent",
                     refute="same PID libz still missing/wrong provider, or new private libandroid/surface owner failure; stop and score separately")))
    print("BurgerKing conditional first-wall movement=1; host variable only; alias/provider copied unchanged; rollback bound; next fatal/t20 unknown")


if __name__ == "__main__":
    main()
