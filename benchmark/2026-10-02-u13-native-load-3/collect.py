import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORKSPACES = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WORKSPACES / "westlake-harness"
BASE = WORKSPACES / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle"
U12 = WORKSPACES / "westlake-inputs/generations/u12-final-j0482c9b1-s615b8bbe-icu-media-zlib-v2/bundle"
FACTORY = WORKSPACES / "westlake-inputs/oh61-link-inputs/system-lib64"
OH_AUDIO = WORKSPACES / "westlake-inputs/oh-system-libs/opensles-5ea-u9/oh-system-lib64-libOpenSLES.so"
KEYS = {"fd-im-vector-app": ["librealm-jni.so"], "mindustry": ["libarc.so"],
        "fd-meet": ["libc++_shared.so", "libhermes.so", "libreactnative.so"]}
RAW = HERE / ".artifacts"
TOOLS = []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        for root, token in [(WORKSPACES, "$WORKSPACES"), (Path.home(), "$HOME")]:
            if value == str(root):
                return token
            value = value.replace(str(root) + "/", token + "/")
        return value
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, dict):
        return {name: portable(item) for name, item in value.items()}
    return value


def save(path, value):
    path = HERE / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value), indent=2) + "\n")


def run(label, command, allowed_codes=(0,)):
    result = subprocess.run([str(item) for item in command], capture_output=True, text=True)
    text = result.stdout + result.stderr
    raw = RAW / (label + ".txt")
    raw.write_text(text)
    published = HERE / "evidence" / (label + ".txt")
    published.parent.mkdir(parents=True, exist_ok=True)
    public = portable(text)
    if len(public.encode()) > 800000:
        public = "Full output is in the SHA-pinned private raw evidence.\n" + "\n".join(public.splitlines()[:50]) + "\n"
    published.write_text(public)
    TOOLS.append(dict(label=label, command=command, exit_code=result.returncode,
                      raw_path=raw, raw_sha256=sha(raw), evidence=str(published.relative_to(HERE)),
                      evidence_sha256=sha(published), excerpt=public != portable(text)))
    if result.returncode not in allowed_codes:
        raise RuntimeError(label + " failed: " + str(result.returncode))
    return text


def parse_symbols(text):
    rows = []
    for line in text.splitlines():
        match = re.match(r"\s*\d+:\s+\S+\s+\d+\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", line)
        if match:
            kind, binding, visibility, section, name = match.groups()
            rows.append(dict(name=name.split("@")[0], version=name.split("@")[-1] if "@" in name else None,
                             spelling=name, kind=kind, binding=binding, visibility=visibility, section=section))
    return rows


def elf(path, label=None):
    command = ["llvm-readelf", "--dyn-syms", path]
    symbols = run(label + "-symbols", command) if label else subprocess.check_output(command, text=True)
    command = ["llvm-readelf", "-d", path]
    dynamic = run(label + "-dynamic", command) if label else subprocess.check_output(command, text=True)
    if label:
        run(label + "-versions", ["llvm-readelf", "-V", path])
    rows = parse_symbols(symbols)
    return dict(path=path, sha256=sha(path), needed=re.findall(r"\(NEEDED\).*\[(.*?)\]", dynamic),
                soname=re.findall(r"\(SONAME\).*\[(.*?)\]", dynamic),
                exports=[row for row in rows if row["section"] != "UND" and row["binding"] in ["GLOBAL", "WEAK"]
                         and row["visibility"] in ["DEFAULT", "PROTECTED"]],
                strong_undefined=[row for row in rows if row["section"] == "UND" and row["binding"] == "GLOBAL"],
                weak_undefined=[row for row in rows if row["section"] == "UND" and row["binding"] == "WEAK"])


def app_context(lines):
    terminal = next((num, line) for num, line in enumerate(lines, 1) if "J_invokeStaticMain_main_threw:" in line)
    pid = int(re.match(r"\S+\s+\S+\s+(\d+)\s+", terminal[1]).group(1))
    tokens = ["MUSL-LDSO", "dlopen_ns", "namespace", "U10-COMPAT", "SoLoader", "UnpackingSoSource", "SysUtil", "J_invokeStaticMain_main_threw"]
    rows = []
    for num, line in enumerate(lines, 1):
        match = re.match(r"\S+\s+\S+\s+(\d+)\s+(\d+)\s+", line)
        if match and int(match.group(1)) == pid and any(token in line for token in tokens):
            rows.append(dict(line=num, pid=pid, tid=int(match.group(2)), text=line,
                             phase="pre-terminal" if num < terminal[0] else "terminal-or-following-context"))
    return dict(pid=pid, terminal=dict(line=terminal[0], text=terminal[1]), rows=rows)


def matches_required(expected, actual):
    return expected == actual


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    source_path = MASTER / "benchmark/2026-10-02-candidate-first-fatal-clusters/sources.json"
    sources = json.loads(source_path.read_text())
    payload = BASE / "native/payload"
    paths = sorted({path for path in payload.rglob("*.so") if path.is_file()} |
                   {path for path in FACTORY.glob("*") if path.is_file() and ".so" in path.name} | {OH_AUDIO})
    providers = {}
    metadata = []
    by_hash = {}
    for path in paths:
        if path.read_bytes()[:4] != b"\x7fELF":
            continue
        digest = sha(path)
        facts = by_hash.setdefault(digest, None)
        if facts is None:
            facts = elf(path)
            by_hash[digest] = facts
        index = len(metadata)
        metadata.append(dict(path=path, sha256=digest, needed=facts["needed"], soname=facts["soname"],
                             scope="T8 payload inventory" if path.is_relative_to(payload) else "OH system inventory; not relocation scope proof"))
        for symbol in facts["exports"]:
            providers.setdefault(symbol["name"], []).append(dict(provider_index=index, version=symbol["version"]))
    save("provider-inventory.json", dict(providers=metadata, union_scope="inventory upper bound only", unique_elf_sha_count=len(by_hash)))
    contexts = {}
    consumers = []
    for key, members in KEYS.items():
        root = Path(sources[key].replace("$WORKSPACES", str(WORKSPACES)))
        context = app_context((root / "hilog.txt").read_text(errors="replace").splitlines())
        context.update(source=root / "hilog.txt", source_sha256=sha(root / "hilog.txt"),
                       assembly_sha256=sha(root / "native-assembly.json"), record_sha256=sha(root / "record.json"))
        contexts[key] = context
        save("evidence/" + key + "-context.json", context)
        record = json.loads((root / "native-assembly.json").read_text())
        all_app_exports = {}
        for member in record["files"]:
            path = Path(member["path"])
            if not matches_required(member["sha256"], sha(path)):
                raise ValueError("consumer SHA drift: " + key + "/" + member["name"])
            facts = elf(path)
            all_app_exports[member["name"]] = set(row["name"] for row in facts["exports"])
        for member in record["files"]:
            if member["name"] not in members:
                continue
            facts = elf(Path(member["path"]), key + "-" + member["name"])
            facts.update(key=key, installed_path=member["installed_path"], native_assembly_sha_verified=True)
            facts["needed_inventory"] = [dict(soname=name, app_member=name in all_app_exports,
                provider_indices=[index for index, row in enumerate(metadata) if Path(row["path"]).name == name or name in row["soname"]],
                runtime_resolution="unknown unless explicitly observed in window5") for name in facts["needed"]]
            facts["undefined_inventory"] = [dict(symbol=row, app_providers=[name for name, exports in all_app_exports.items() if row["name"] in exports],
                deployed_provider_candidates=providers.get(row["name"], [])) for row in facts["strong_undefined"] + facts["weak_undefined"]]
            facts["inventory_absent_strong_symbols"] = [row["symbol"]["spelling"] for row in facts["undefined_inventory"]
                if row["symbol"]["binding"] == "GLOBAL" and not row["app_providers"] and not row["deployed_provider_candidates"]]
            facts.pop("exports")
            consumers.append(facts)
    save("consumer-comparison.json", dict(consumers=consumers, limitation="All NEEDED and strong UND entries compared; provider inventory does not prove lazy namespace resolution or ABI compatibility"))
    save("log-index.json", contexts)
    for name in ["libz.so", "libshared_libz.z.so", "libOpenSLES.so", "libbionic_compat.so", "libwestlake_native_abi.so", "libapp_native_loader.so", "appspawn-x"]:
        run("whois-" + name, ["python3", MASTER / "scripts/lab/deployed_whois.py", name, "--generation", BASE])
    roles = {"compat": payload / "android/lib64/libbionic_compat.so", "facade": payload / "android/lib64/libOpenSLES.so",
             "private-abi": payload / "android/lib64/westlake_native/libwestlake_native_abi.so",
             "pthread-bridge": payload / "android/lib64/libwestlake_bionic_pthread_bridge.so",
             "libc-facade": payload / "android/lib64/libc.so", "factory-libc": FACTORY / "ld-musl-aarch64.so.1",
             "oh-audio": WORKSPACES / "westlake-inputs/oh-system-libs/opensles-5ea-u9/oh-system-lib64-libOpenSLES.so",
             "u12-zlib-alias": U12 / "native/payload/android/lib64/westlake_native/libz.so",
             "u12-zlib-provider": U12 / "native/payload/android/lib64/westlake_native/libshared_libz.z.so"}
    provider_facts = {role: elf(path, role) for role, path in roles.items()}
    save("selected-provider-facts.json", provider_facts)
    for role, path in [("host-r3", payload / "runtime/appspawn-x"), ("anl", payload / "android/lib64/libapp_native_loader.so")]:
        scan_json = RAW / ("open-" + role + ".json")
        run("open-" + role, ["python3", MASTER / "scripts/lab/open_site_scan.py", path, "--json", scan_json])
        save("evidence/open-" + role + ".json", json.loads(scan_json.read_text()))
        run("disassembly-" + role, ["llvm-objdump", "-d", "--no-show-raw-insn", path])
    run("strings-private-zlib-provider", ["python3", MASTER / "scripts/lab/deployed_strings_diff.py",
        roles["u12-zlib-provider"], "--deployed", payload / "android/lib64/libshared_libz.z.so"])
    run("strings-u12-compat", ["python3", MASTER / "scripts/lab/deployed_strings_diff.py",
        U12 / "native/payload/android/lib64/libbionic_compat.so", "--deployed", roles["compat"]])
    run("strings-u12-host", ["python3", MASTER / "scripts/lab/deployed_strings_diff.py",
        U12 / "native/payload/runtime/appspawn-x", "--deployed", payload / "runtime/appspawn-x"], (0, 1))
    identity_paths = [payload / "runtime/appspawn-x", payload / "android/lib64/libapp_native_loader.so", roles["compat"],
                      roles["facade"], roles["private-abi"], roles["libc-facade"]]
    run("artifact-identity-t8", ["python3", MASTER / "scripts/lab/artifact_identity.py", *identity_paths,
        "--expected", BASE / "expected-per-board.json"])
    snippets = []
    for path, intervals in [
        (MASTER / "benchmark/2026-10-02-bms-source-reconcile/sources/bms/src/adapter/framework/app-native-loader/src/app_native_loader.c", [(60, 78), (430, 482)]),
        (MASTER / "benchmark/2026-10-02-bms-source-reconcile/sources/bms/src/adapter/framework/app-native-loader/src/flutter_domain.inc", [(18, 56)]),
        (REPO / "benchmark/2026-10-02-u11-native-batch/inputs/host-r3/candidate-stock-host.c", [(122, 140), (248, 360)]),
        (MASTER / "benchmark/2026-10-02-u12-private-zlib/inputs/zlib-route.h", [(20, 29)])]:
        lines = path.read_text().splitlines()
        snippets.append(dict(path=path, sha256=sha(path), rows=[dict(line=num, text=lines[num-1])
            for first, last in intervals for num in range(first, min(last, len(lines)) + 1)]))
    save("source-evidence.json", dict(files=snippets, provenance="ANL source selected in 0dd56096f9 source reconcile; r3 source and U12 reviewed route; no rebuild performed"))
    save("identity.json", dict(base_bundle=BASE, base_bundle_sha256=sha(BASE / "bundle.json"),
        base_native_sha256=sha(BASE / "native/package.json"), source_index=source_path, source_index_sha256=sha(source_path),
        provider_inputs={role: dict(path=path, sha256=sha(path)) for role, path in roles.items()},
        limitations=["WHOIS generation paths are T8; its maps section is explicitly historical U9, not window5",
                     "Fallback lib-main and versioned realm file bytes were not captured; public native-assembly members are SHA verified"],
        no_candidates=True, no_device_operations=True))
    save("raw-evidence.json", dict(tools=TOOLS))
    print(json.dumps(dict(keys=len(contexts), consumers=len(consumers), providers=len(metadata), tools=len(TOOLS))))


if __name__ == "__main__":
    main()
