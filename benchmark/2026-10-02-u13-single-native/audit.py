import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from build import HERE, HOST_SHA, MASTER, POLICY_SHA, REPO, SIGNED, U12, WS, portable, run, save, sha


def main():
    records = []
    for name in ["libnativeloader.so", "appspawn-x", "libz.so", "liboh_android_runtime.so"]:
        records.append(run("whois-" + name, ["python3", MASTER / "scripts/lab/deployed_whois.py", name,
            "--generation", SIGNED]))
    candidates = {
        "policy": HERE / ".artifacts/policy/candidate1/libnativeloader-candidate.so",
        "host": HERE / ".artifacts/host/candidate1/appspawn-x-candidate1"}
    relative = {"policy": "payload/android/lib64/libnativeloader.so", "host": "payload/runtime/appspawn-x"}
    for role, candidate in candidates.items():
        old = U12 / "native" / relative[role]
        if sha(old) != {"policy": POLICY_SHA, "host": HOST_SHA}[role]:
            raise ValueError("actual U12 base drift")
        for label, path in [("u12", old), ("candidate", candidate), ("signed", SIGNED / "native" / relative[role])]:
            records.append(run("open-" + role + "-" + label, ["python3", MASTER / "scripts/lab/open_site_scan.py", path,
                "--json", HERE / "evidence" / ("open-" + role + "-" + label + ".json")]))
            report = HERE / "evidence" / ("open-" + role + "-" + label + ".json")
            save(report.relative_to(HERE), json.loads(report.read_text()))
        for label, base in [("u12", old), ("signed", SIGNED / "native" / relative[role])]:
            records.append(run("strings-" + role + "-" + label, ["python3", MASTER / "scripts/lab/deployed_strings_diff.py",
                candidate, "--deployed", base], allowed=(0, 1)))
        argv = ["python3", MASTER / "scripts/lab/abi_diff.py", "--old", old, "--new", candidate, "--calls",
                "--json", HERE / "evidence" / ("abi-" + role + ".json")]
        if role == "policy":
            argv += ["--consumer", U12 / "native/payload/android/lib64/libopenjdk.so"]
        else:
            argv += ["--consumer", U12 / "native/payload/runtime/libwestlake_android_child.z.so"]
        records.append(run("abi-" + role, argv))
    reference = MASTER / "benchmark/2026-10-02-u10-1-t8-sweep/u10-1-t8-reference/sources.json"
    signed = json.loads(reference.read_text())["keys"]["mcdonalds"]
    run_dir = Path(signed["t20"].replace("$WORKSPACES", str(WS))).parent
    actual = json.loads((run_dir / "record.json").read_text())
    package = WS / "westlake-inputs/apks/apkpure/com.mcdonalds.app@26.31.1@arm64-v8a/config.arm64_v8a.apk"
    root = HERE / ".artifacts/consumers"
    root.mkdir(exist_ok=True)
    expected = {row["name"]: row["sha256"] for row in actual["native_sidecars"]}
    with zipfile.ZipFile(package) as archive:
        for name in archive.namelist():
            if name.startswith("lib/arm64-v8a/") and name.endswith(".so"):
                path = root / Path(name).name
                path.write_bytes(archive.read(name))
                if sha(path) != expected[path.name]:
                    raise ValueError("signed McDonald sidecar SHA mismatch")
    consumer = root / "librealmc.so"
    records.append(run("realmc-dynamic", ["llvm-readelf", "-d", "-V", consumer]))
    records.append(run("realmc-symbols", ["llvm-readelf", "--dyn-syms", "--wide", consumer]))
    export_cache = {}
    def exports(path):
        if path in export_cache:
            return export_cache[path]
        output = subprocess.check_output(["llvm-nm", "-D", "--defined-only", "--format=just-symbols", path], text=True)
        export_cache[path] = {name.split("@")[0] for name in output.splitlines()}
        return export_cache[path]
    output = subprocess.check_output(["llvm-nm", "-D", "--undefined-only", consumer], text=True)
    required = {row.split()[-1].split("@")[0] for row in output.splitlines() if len(row.split()) == 2 and row.split()[0] == "U"}
    private = U12 / "native/payload/android/lib64/westlake_native"
    zlib = private / "libshared_libz.z.so"
    z_names = {name for name in required if re.match(r"^(deflate|inflate|compress|uncompress|crc32|adler32|zlib|zError)", name)}
    if not z_names or z_names - exports(zlib):
        raise ValueError("librealmc zlib imports are not covered")
    libc = WS / "westlake-inputs/oh61-link-inputs/system-lib64/ld-musl-aarch64.so.1"
    owners = [libc] + sorted((U12 / "native/payload/android/lib64").glob("*.so")) + sorted(private.glob("*.so"))
    current_exports = set().union(*(exports(path) for path in owners))
    compat = REPO / "benchmark/2026-10-02-u12-vlc-bionic-residue/.artifacts/candidate1.so"
    proposed_exports = current_exports | exports(compat)
    binders = {name: [dict(path=portable(path), sha256=sha(path)) for path in owners + [compat] if name in exports(path)]
               for name in sorted(required - exports(libc))}
    needed = re.findall(r"\(NEEDED\).*\[([^\]]+)\]", subprocess.check_output(["llvm-readelf", "-d", consumer], text=True))
    provider_paths = {
        "liblog.so": U12 / "native/payload/android/lib64/liblog.so",
        "libandroid.so": private / "libandroid.so",
        "libz.so": private / "libz.so",
        "libm.so": libc, "libdl.so": libc, "libc.so": libc}
    need_rows = []
    for name in needed:
        path = provider_paths[name]
        records.append(run("realmc-needed-" + name, ["llvm-readelf", "-d", path]))
        need_rows.append(dict(soname=name, path=portable(path), sha256=sha(path),
            qualification="exact candidate/private or factory context; inherited owner availability requires live verification"))
    save("consumer.json", dict(consumer_sha256=sha(consumer), signed_record_sha256=sha(run_dir / "record.json"),
        apk_split=dict(path=portable(package), sha256=sha(package)), required=sorted(required),
        zlib_required=sorted(z_names), zlib_missing=[], exact_sidecars={name: sha(root / name) for name in expected},
        needed=need_rows, unresolved_u12_inventory=sorted(required - current_exports),
        unresolved_with_u13_vlc_compat=sorted(required - proposed_exports), non_factory_providers=binders,
        limitation="Inventory/export coverage is an upper bound, not proof that all owners enter app relocation scope. No library is loaded on a board."))
    lines = (run_dir / "hilog.txt").read_text(errors="replace").splitlines()
    (HERE / "evidence/mcdonalds-first-wall.txt").write_text(portable("\n".join(str(number) + ": " + lines[number - 1]
        for number in [30948, 30968, 31141]) + "\n"))
    save("audit-commands.json", dict(commands=records, execution_enabled=False))


if __name__ == "__main__":
    main()
