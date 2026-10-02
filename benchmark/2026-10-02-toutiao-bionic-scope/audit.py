from collections import defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import zipfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
GEN = WS / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native/payload"
COMPAT = GEN / "android/lib64/libbionic_compat.so"
HOST = GEN / "runtime/appspawn-x"
LOADER = GEN / "android/lib64/libnativeloader.so"
TARGETS = ["__errno", "__cmsg_nxthdr", "__system_property_read", "__gnu_strerror_r"]
PINS = {"android/lib64/libbionic_compat.so": "015aa3a632eabe057bd8d6ce0e0ff181209da7dcab8de22409a79addc0a56d58",
        "runtime/appspawn-x": "65cc3535ebf22bdf664b3c8ddf932ccd7f42d936be1c861e1221a80b12a00284",
        "android/lib64/libnativeloader.so": "0718f01e237d322b5a16a1858265f8cc05cddd5ddca6d1ceb28bcc33023913a9"}


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else Path(value).read_bytes()).hexdigest()


def portable(value):
    return str(value).replace(str(REPO), "$REPO").replace(str(WS), "$WORKSPACES").replace(str(Path.home()), "$HOME")


def save(name, value, compact=False):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(portable(json.dumps(value, indent=None if compact else 2,
                                       separators=(',', ':') if compact else None)) + "\n")


def run(label, command, select=None):
    result = subprocess.run([str(value) for value in command], capture_output=True, text=True)
    content = result.stdout + result.stderr
    raw = HERE / ".artifacts" / (label + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(content)
    display = content if select is None else "\n".join(line for line in content.splitlines() if select(line)) + "\n"
    public = HERE / "evidence" / (label + ".txt")
    public.parent.mkdir(parents=True, exist_ok=True)
    public.write_text(portable(display))
    return dict(label=label, exit_code=result.returncode, command=[portable(value) for value in command],
                raw_path=portable(raw), raw_sha256=sha(raw), evidence="evidence/" + public.name,
                evidence_sha256=sha(public), excerpt=select is not None)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def sections(data):
    if data[:6] != b"\x7fELF\x02\x01":
        return None
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", data)
    rows = [struct.unpack_from("<IIQQQQIIQQ", data, header[6] + index * header[11]) for index in range(header[12])]
    names = data[rows[header[13]][4]:rows[header[13]][4] + rows[header[13]][5]]
    return [dict(name=names[row[0]:].split(b"\0", 1)[0].decode(), type=row[1], address=row[3],
                 offset=row[4], size=row[5], link=row[6], entry_size=row[9]) for row in rows]


def elf(data):
    rows = sections(data)
    if rows is None:
        return dict(status="unsupported-ABI-or-non-ELF-not-clean", symbols=[], needed=[], relocations={})
    by_name = {row["name"]: row for row in rows}
    result = dict(status="ELF64-AArch64" if struct.unpack_from("<H", data, 18)[0] == 183 else "ELF64-other-machine",
                  symbols=[], needed=[], relocations={}, version_definitions=[])
    if ".dynsym" not in by_name:
        result["status"] = "unknown-no-dynsym"
        return result
    dynamic = by_name[".dynsym"]
    strings = rows[dynamic["link"]]
    def string_at(index):
        start = strings["offset"] + index
        return data[start:data.index(b"\0", start)].decode(errors="replace")
    versions = {}
    for row in rows:
        if row["name"] == ".gnu.version_r":
            cursor = row["offset"]
            while cursor < row["offset"] + row["size"]:
                version, count, filename, auxiliary, following = struct.unpack_from("<HHIII", data, cursor)
                aux_cursor = cursor + auxiliary
                for index in range(count):
                    hash_value, flags, other, name, next_aux = struct.unpack_from("<IHHII", data, aux_cursor)
                    versions[other & 0x7fff] = dict(version=string_at(name), file=string_at(filename), hash=hex(hash_value))
                    aux_cursor += next_aux
                if not following:
                    break
                cursor += following
        if row["name"] == ".gnu.version_d":
            cursor = row["offset"]
            while cursor < row["offset"] + row["size"]:
                version, flags, other, count, hash_value, auxiliary, following = struct.unpack_from("<HHHHIII", data, cursor)
                name, next_aux = struct.unpack_from("<II", data, cursor + auxiliary)
                value = dict(version=string_at(name), hash=hex(hash_value), definition=True)
                versions[other & 0x7fff] = value
                result["version_definitions"].append(value)
                if not following:
                    break
                cursor += following
    symbols = []
    for index, offset in enumerate(range(dynamic["offset"], dynamic["offset"] + dynamic["size"], dynamic["entry_size"] or 24)):
        name, info, visibility, section, address, size = struct.unpack_from("<IBBHQQ", data, offset)
        version_index = 1
        if ".gnu.version" in by_name:
            version_index = struct.unpack_from("<H", data, by_name[".gnu.version"]["offset"] + 2 * index)[0] & 0x7fff
        symbol = dict(name=string_at(name), bind=info >> 4, visibility=visibility & 3, defined=section != 0,
                      address=hex(address), version_index=version_index, version=versions.get(version_index))
        symbols.append(symbol)
        if symbol["name"] in TARGETS:
            result["symbols"].append(symbol)
    for row in rows:
        if row["type"] == 6:
            for offset in range(row["offset"], row["offset"] + row["size"], row["entry_size"] or 16):
                tag, value = struct.unpack_from("<qQ", data, offset)
                if tag == 1:
                    result["needed"].append(string_at(value))
                if tag == 0x6ffffffb:
                    result["flags1"] = hex(value)
        if row["type"] == 4 and row["link"] == rows.index(dynamic):
            for offset in range(row["offset"], row["offset"] + row["size"], row["entry_size"] or 24):
                address, info, addend = struct.unpack_from("<QQq", data, offset)
                name = symbols[info >> 32]["name"]
                if name in TARGETS:
                    result["relocations"].setdefault(name, []).append(dict(address=hex(address), type=info & 0xffffffff))
    result["all_exports"] = sorted(symbol["name"] for symbol in symbols if symbol["defined"] and symbol["bind"] in {1, 2} and symbol["visibility"] in {0, 3})
    return result


def scan():
    sys.path.insert(0, str(REPO / "benchmark/2026-10-01-b10-theme-graphics"))
    import collect
    records, apps, groups = [], [], defaultdict(lambda: dict(keys=set(), witnesses=[]))
    cache = {}
    for entry in collect.inputs(WS):
        apk = Path(entry["path"])
        if sha(apk) != entry["apk_sha256"]:
            raise ValueError("APK identity mismatch: " + entry["key"])
        members = []
        embedded = {}
        with zipfile.ZipFile(apk) as archive:
            for name in archive.namelist():
                if name.endswith(".so"):
                    payload = archive.read(name)
                    members.append((name, payload))
                    embedded.setdefault(Path(name).name, set()).add(sha(payload))
                    embedded.setdefault(name, set()).add(sha(payload))
        metadata = apk.parent / "app-input.json"
        missing = []
        metadata_sha = None
        if entry["cohort"] == "u7-66" and metadata.is_file():
            metadata_sha = sha(metadata)
            value = json.loads(metadata.read_text())
            if value["apk_sha256"] != entry["apk_sha256"] or value["application"]["package"] != entry["package"]:
                raise ValueError("sidecar metadata identity mismatch")
            for name, pin in value["native_libraries"].items():
                if pin["sha256"] in embedded.get(name, set()):
                    continue
                path = apk.parent / name
                if not path.is_file():
                    missing.append(dict(name=name, sha256=pin["sha256"]))
                    continue
                payload = path.read_bytes()
                if sha(payload) != pin["sha256"]:
                    raise ValueError("sidecar SHA mismatch")
                members.append(("sidecar/" + name, payload))
        inventory = []
        for name, payload in members:
            digest = sha(payload)
            parsed = elf(payload)
            imports = [symbol for symbol in parsed["symbols"] if not symbol["defined"] and symbol["bind"] in {1, 2}]
            row = dict(member=name, sha256=digest, bytes=len(payload), status=parsed["status"], imports=imports,
                       needed=parsed["needed"], relocations=parsed["relocations"])
            if imports:
                artifact = HERE / ".artifacts/members" / (digest + ".so")
                artifact.parent.mkdir(parents=True, exist_ok=True)
                if digest not in cache:
                    artifact.write_bytes(payload)
                    records.append(run("member-" + digest[:16] + "-versions", ["llvm-readelf", "-V", artifact]))
                    records.append(run("member-" + digest[:16] + "-symbols", ["llvm-readelf", "--dyn-syms", "-W", artifact],
                                       lambda line: any(symbol in line for symbol in TARGETS)))
                    cache[digest] = portable(artifact)
                row["artifact"] = cache[digest]
                for symbol in imports if parsed["status"] == "ELF64-AArch64" else []:
                    group = groups[symbol["name"]]
                    group["keys"].add(entry["key"])
                    group["witnesses"].append(dict(key=entry["key"], member=name, sha256=digest, **symbol,
                         relocation_count=len(parsed["relocations"].get(symbol["name"], [])), needed=parsed["needed"]))
            inventory.append(row)
        apps.append(dict(**entry, metadata_sha256=metadata_sha, missing_sidecars=missing, members=inventory))
        print("SCANNED " + entry["key"] + " native=" + str(len(inventory)), flush=True)
    report = dict(apps=apps, groups=[dict(symbol=name, keys=sorted(group["keys"]), affected_keys=len(group["keys"]),
                  witnesses=group["witnesses"]) for name, group in sorted(groups.items())],
                  key_count=len(apps), native_members=sum(len(app["members"]) for app in apps),
                  execution_proved=False, unsupported_not_clean=True, tool_records=records)
    if len(apps) != 166 or len({app["key"] for app in apps}) != 166:
        raise ValueError("166-key inventory incomplete")
    save("consumers.json", report, compact=True)
    for group in report["groups"]:
        print(group["symbol"] + " keys=" + str(group["affected_keys"]) + " " + ",".join(group["keys"]))


def main():
    for path, pin in PINS.items():
        if sha(GEN / path) != pin:
            raise ValueError("deployed artifact drift")
    records = []
    for name in ["libbionic_compat.so", "appspawn-x", "libnativeloader.so"]:
        records.append(run("whois-" + name, ["python3", MASTER / "scripts/lab/deployed_whois.py", name]))
        records.append(run("whois-current-" + name, ["python3", MASTER / "scripts/lab/deployed_whois.py",
                                                     name, "--generation", GEN]))
    records.append(run("compat-symbols", ["llvm-readelf", "--dyn-syms", "-W", COMPAT]))
    records.append(run("compat-versions", ["llvm-readelf", "-V", COMPAT]))
    records.append(run("compat-full-nm", ["llvm-nm", "-a", COMPAT], lambda line: any(symbol in line for symbol in TARGETS)))
    records.append(run("compat-dynamic", ["llvm-readelf", "-d", COMPAT]))
    for name, path in [("host-r3", HOST), ("compat", COMPAT), ("loader", LOADER)]:
        records.append(run("open-" + name, ["python3", MASTER / "scripts/lab/open_site_scan.py", path,
                           "--json", HERE / ".artifacts" / ("open-" + name + ".json")]))
        save("evidence/open-" + name + ".json", json.loads((HERE / ".artifacts" / ("open-" + name + ".json")).read_text()))
    source = MASTER / "benchmark/2026-10-01-n10b-child/evidence/oh61-dynlink-linux.c"
    if sha(source) != "e50b30f22a1d2248509c438e33c5e1b143462c4f001cf05a4230f1376c152e9f":
        raise ValueError("namespace-aware OH source drift")
    excerpt = []
    lines = source.read_text().splitlines()
    for start, end in [(775, 814), (913, 942), (1037, 1063), (1240, 1284), (1377, 1393),
                       (2252, 2262), (2408, 2448), (2668, 2715), (4662, 4693)]:
        excerpt.extend(str(number) + ": " + lines[number - 1] for number in range(start, end + 1))
    (HERE / "evidence/oh61-loader-witnesses.txt").write_text("\n".join(excerpt) + "\n")
    save("identity.json", dict(pins=PINS, compat=elf(COMPAT.read_bytes()), source=dict(path=portable(source), sha256=sha(source),
         commit="02dd8d82887b040b85a4294e9a5039f016fd607a", scope="Reference checkout; not a claimed byte reproduction of deployed OH libc"),
         tool_records=records, device_io=False))
    scan()


if __name__ == "__main__":
    main()
