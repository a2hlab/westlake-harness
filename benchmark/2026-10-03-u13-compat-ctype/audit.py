import ast
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from common import DEPLOYED, HERE, MASTER, OLD, REPO, WS, capture, expand, save, sha
from verify import defined

sys.path.insert(0, str(MASTER / "scripts/lab"))
import auto_approve_exceptions as auto
import generation_bundle as gb
import generation_static_checks as static


def main():
    package = HERE / ".artifacts/bundle-v2"
    native = package / "native"
    base = WS / "westlake-inputs/generations/u12-final-j0482c9b1-s615b8bbe-icu-media-zlib-v2/bundle"
    candidate = HERE / ".artifacts/candidate1.so"
    composition = json.loads((HERE / "composition.json").read_text())
    records, reports = [], {}
    registry = MASTER / "knowledge/gates/native-predeploy-exceptions.json"
    registry_sha = sha(registry)
    for name, root in [("u12", base / "native"), ("v2", native)]:
        records.append(capture("native-" + name, ["python3", MASTER / "scripts/lab/native_predeploy.py", "--package", root,
            "--inputs", root / "native-checks/native-gates.json", "--readelf", "llvm-readelf"], allowed=(0, 1, 3)))
        report = json.loads((HERE / ".artifacts/raw" / ("native-" + name + ".txt")).read_text())
        if report["errors"]:
            raise ValueError(report["errors"])
        reports[name] = report
        save("evidence/native-" + name + ".json", report)
    records.append(capture("auto-identical-preview", ["python3", MASTER / "scripts/lab/auto_approve_exceptions.py",
         "--candidate", HERE / "evidence/native-v2.json", "--baseline", HERE / "evidence/native-u12.json"], allowed=(0, 3)))
    matched, new = auto.classify(reports["v2"], [reports["u12"]], json.loads(registry.read_text())["exceptions"])
    evidence = ["benchmark/2026-10-03-u13-compat-ctype/evidence/native-" + name + ".json" for name in ["v2", "u12"]]
    rows = []
    for gate, finding, source in matched:
        rows.append(dict(gate=gate, package_manifest_sha256=reports["v2"]["package_manifest_sha256"],
            inputs_sha256=reports["v2"]["inputs_sha256"], issue_id=finding["issue_id"],
            reason="Unchanged approved U12 finding; new binding proposed only", removal_condition=source["removal_condition"],
            evidence=evidence, approved_by=None, approved_at=None,
            auto_from=dict(package_manifest_sha256=source["package_manifest_sha256"], issue_id=source["issue_id"])))
    save("registry-delta.draft.json", dict(exceptions=rows, applied=False, execution_enabled=False))
    save("outer-review.json", dict(package_manifest_sha256=reports["v2"]["package_manifest_sha256"],
         inputs_sha256=reports["v2"]["inputs_sha256"], new_findings=[dict(finding, gate=gate) for gate, finding, _ in new],
         approved_by=None, applied=False, execution_enabled=False))
    if sha(registry) != registry_sha:
        raise ValueError("registry changed during scan; rerun")
    save("namespace-gates.json", dict(records=records, baseline_status=reports["u12"]["status"],
         candidate_status=reports["v2"]["status"], identical=len(matched), new=len(new),
         findings={gate: {name: len(report["gates"][gate]["findings"]) for name, report in reports.items()} for gate in ["N1", "N2"]},
         registry_unchanged=True, exceptions_applied=False, execution_enabled=False))
    old_scan = json.loads((HERE / "evidence/open-b2.json").read_text())["binaries"][0]
    new_scan = json.loads((HERE / "evidence/open-candidate.json").read_text())["binaries"][0]
    deployed_scan = json.loads((HERE / "evidence/open-deployed.json").read_text())["binaries"][0]
    save("open-delta.json", dict(vs_b2=static.site_delta(old_scan["sites"], new_scan["sites"]),
         vs_deployed=static.site_delta(deployed_scan["sites"], new_scan["sites"]),
         old_edges=old_scan["namespace_edges"], new_edges=new_scan["namespace_edges"],
         interpretation="Two old opens retained; unresolved-clobber PC string moves again to3b98, raw signature still requires review",
         applied=False))
    old_effective, new_effective = static.effective(base), static.effective(package)
    save("static-checks.json", static.check(package, base, {}))
    consumer = REPO / "benchmark/2026-10-02-u13-single-native/.artifacts/consumers/librealmc.so"
    consumer_prior = json.loads((REPO / "benchmark/2026-10-02-u13-single-native/consumer.json").read_text())
    if sha(consumer) != consumer_prior["consumer_sha256"]:
        raise ValueError("realmc drift")
    records = [capture("realmc-dynamic-versions", ["llvm-readelf", "-d", "-V", consumer]),
               capture("realmc-undefined", ["llvm-nm", "-D", "--undefined-only", consumer])]
    raw = (HERE / ".artifacts/raw/realmc-undefined.txt").read_text()
    strong = {line.split()[-1] for line in raw.splitlines() if len(line.split()) == 2 and line.split()[0] == "U"}
    libc = WS / "westlake-inputs/oh61-link-inputs/system-lib64/ld-musl-aarch64.so.1"
    direct = [Path(expand(row["path"])) for row in consumer_prior["needed"]]
    if sha(libc) != "fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2":
        raise ValueError("factory libc changed")
    owners = {sha(path): path for path in direct + [candidate, libc]}
    inventory = {sha(gb.member(package, row)): gb.member(package, row)
                 for row in new_effective.values() if gb.member(package, row).read_bytes()[:4] == b"\x7fELF"}
    exports = {digest: defined(path) for digest, path in (inventory | owners).items()}
    closure = dict(owners)
    queue = list(direct)
    unresolved_dependencies = []
    while queue:
        source = queue.pop()
        needed = re.findall(r"\(NEEDED\).*\[([^\]]+)\]", subprocess.check_output(["llvm-readelf", "-d", source], text=True))
        for name in needed:
            if name in {"libc.so", "libm.so", "libdl.so", "libpthread.so"}:
                provider = libc
            elif name == "libshared_libz.z.so":
                provider = base / "native/payload/android/lib64/westlake_native" / name
            else:
                candidates = [native / "payload/android/lib64" / name,
                    WS / "westlake-inputs/oh61-link-inputs/system-lib64" / name,
                    WS / "westlake-inputs/oh61-link-inputs/system-lib64/platformsdk" / name,
                    WS / "westlake-inputs/oh61-link-inputs/system-lib64/chipset-sdk-sp" / name]
                provider = next((path for path in candidates if path.is_file()), None)
            if provider is None:
                unresolved_dependencies.append(dict(consumer=source, needed=name))
                continue
            digest = sha(provider)
            if digest not in closure:
                closure[digest] = provider
                exports.setdefault(digest, defined(provider))
                queue.append(provider)
    rows = []
    for versioned in sorted(strong):
        name = versioned.split("@")[0]
        rows.append(dict(symbol=name, import_name=versioned,
            direct_plus_compat_providers=[dict(path=path, sha256=digest) for digest, path in owners.items() if name in exports[digest]],
            needed_closure_plus_compat_providers=[dict(path=path, sha256=digest) for digest, path in closure.items() if name in exports[digest]],
            global_package_providers=[dict(path=path, sha256=digest) for digest, path in inventory.items() if name in exports[digest]],
            factory_libc=name in exports[sha(libc)]))
    missing_direct = [row["symbol"] for row in rows if not row["direct_plus_compat_providers"]]
    missing_inventory = [row["symbol"] for row in rows if not row["direct_plus_compat_providers"] and not row["global_package_providers"]]
    missing_closure = [row["symbol"] for row in rows if not row["needed_closure_plus_compat_providers"]]
    missing_factory_compat = sorted({row["symbol"] for row in rows} - exports[sha(libc)] - exports[sha(candidate)])
    save("realmc-consumer.json", dict(consumer_sha256=sha(consumer), needed=consumer_prior["needed"], strong_import_count=len(strong),
         rows=rows, missing_direct_plus_compat=missing_direct, missing_global_inventory=missing_inventory, records=records,
         missing_needed_closure_plus_compat=missing_closure, missing_factory_plus_compat=missing_factory_compat,
         closure_unresolved_dependencies=unresolved_dependencies, closure_providers=[dict(path=path, sha256=digest) for digest, path in closure.items()],
         interpretation="Version-normalized inventory only; LIBC import/provider acceptance and saved relocation scope must be confirmed by real linker. Existing bridge _ctype_ export did not prevent U12 failure."))
    table = bytes(json.loads((HERE / "table-oracle.json").read_text())["bytes"])
    strings = []
    for line in (HERE / "evidence/strings-b2.txt").read_text().splitlines():
        if line.startswith(("ADDED", "DROPPED")):
            value = ast.literal_eval(line[8:])
            projection = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in table[1:129]).lstrip()
            strings.append(dict(operation=line.split()[0], value=value, source="inputs/aosp/libc/upstream-openbsd/lib/libc/gen/ctype_.c:39",
                 exact_table_projection=value == projection, reason="readelf -p renders nonprintable table bytes as dots and regex strips leading spaces; full257-byte ELF/source equality proves it is not a path/policy string"))
    if len(strings) != 1 or strings[0]["operation"] != "ADDED" or not strings[0]["exact_table_projection"]:
        raise ValueError("unexpected strings delta")
    save("strings-review.json", dict(rows=strings, dropped=0, added=1, raw_exit_code=1, approved_by=None, execution_enabled=False))
    save("predictions.json", dict(rows=[dict(key="mcdonalds", first_wall="_ctype_ missing, hilog30959/30974/30988 PID31476",
         predicted_first_fatal_moves=1, qualification="conditional on unique resident compat entering this consumer relocation scope; no observed result yet",
         scope_qualification="U12 global bridge owner exports _ctype_ already, so another global export alone is not visibility proof",
         next_fatal="unknown; needed-closure inventory gaps are " + ",".join(missing_closure) if missing_closure else "unknown; no remaining strong-import inventory gap proves startup succeeds",
         predicted_t20="unknown", host_candidate_included=False)], proven_first_fatal_moves=0, conditional_first_fatal_moves=1,
         duplicate_counting="Only McDonald confirmed U12 _ctype_ first fatal counted, not all static importers", execution_enabled=False))
    for name, source in [("native-manifest.json", native / "package.json"), ("bundle-manifest.json", package / "bundle.json"),
                         ("native-inputs.json", native / "native-checks/native-gates.json"), ("scan-manifest.json", native / "native-checks/scan-manifest.json")]:
        target = HERE / "manifests" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    print("Native gate " + reports["v2"]["status"] + " identical=" + str(len(matched)) + " new=" + str(len(new)))
    print("realmc strongUND=" + str(len(strong)) + " direct-gap=" + str(missing_direct) + " global-gap=" + str(missing_inventory))


if __name__ == "__main__":
    main()
