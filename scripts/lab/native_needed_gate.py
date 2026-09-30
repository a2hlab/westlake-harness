"""N2: DT_NEEDED closure in the original private namespace, never inherit."""

from collections import deque
from pathlib import PurePosixPath
import os
import re
import subprocess

from native_gate_common import absolute_path, read_json, sha256, verified_file


def parse_dynamic(text):
    if not re.search(r"Dynamic section (?:at offset|contains)", text):
        raise ValueError("readelf did not describe a dynamic section")
    result = dict(needed=[], soname=None, rpath=[], runpath=[])
    tags = {"NEEDED": "needed", "SONAME": "soname", "RPATH": "rpath", "RUNPATH": "runpath"}
    for line in text.splitlines():
        for tag, field in tags.items():
            if "(" + tag + ")" not in line:
                continue
            match = re.search(r"\[([^\]]*)\]", line)
            if match is None or not match.group(1):
                raise ValueError("malformed dynamic " + tag)
            value = match.group(1)
            if field == "soname":
                if result[field] is not None:
                    raise ValueError("duplicate SONAME")
                result[field] = value
            elif field == "needed":
                result[field].append(value)
            else:
                result[field].extend(value.split(":"))
    return result


class ElfReader:
    def __init__(self, executable):
        self.executable = str(executable)
        self.cache = {}
        self.evidence = []

    def __call__(self, record):
        digest = record["sha256"]
        if sha256(record["path"]) != digest:
            raise ValueError("ELF changed after package verification: " + record["package_path"])
        if digest not in self.cache:
            with record["path"].open("rb") as stream:
                header = stream.read(20)
            if len(header) != 20 or header[:4] != b"\x7fELF" or header[4:6] != bytes([2, 1]):
                raise ValueError("expected ELF64 little-endian input: " + record["package_path"])
            if int.from_bytes(header[18:20], "little") != 183:
                raise ValueError("expected AArch64 input: " + record["package_path"])
            completed = subprocess.run([self.executable, "-d", "--wide", str(record["path"])],
                                       capture_output=True, text=True, timeout=30,
                                       env={**os.environ, "LC_ALL": "C"})
            if completed.returncode or completed.stderr.strip():
                raise ValueError("readelf failed: " + record["package_path"] + ": " + completed.stderr.strip())
            self.cache[digest] = parse_dynamic(completed.stdout)
            self.evidence.append(dict(sha256=digest, package_path=record["package_path"],
                                      stdout=completed.stdout, metadata=self.cache[digest]))
        return self.cache[digest]


def is_library(name):
    return bool(re.search(r"\.so(?:\.[^/]+)?$", name))


def scan_domains(virtual, domains, reader):
    if not isinstance(domains, list) or not domains:
        raise ValueError("N2 requires nonempty effective domains")
    findings, edges, visited_records, owned_dirs, names = [], [], [], set(), set()
    for domain in domains:
        name = domain["name"]
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("empty or duplicate namespace name")
        names.add(name)
        directories = [absolute_path(value) for value in domain["library_dirs"]]
        search = [absolute_path(value) for value in domain["search_paths"]]
        permitted = [absolute_path(value) for value in domain["permitted_paths"]]
        if not directories or not search or not permitted:
            raise ValueError("empty namespace roots/search/permitted paths: " + name)
        owned_dirs.update(str(directory) for directory in directories)
        for unresolved in domain.get("unresolved_paths", []):
            findings.append(dict(domain=name, kind="unknown-effective-path", expression=unresolved))
        roots = sorted(path for path in virtual if is_library(path) and PurePosixPath(path).parent in directories)
        if not roots:
            raise ValueError("namespace has no sealed library roots: " + name)
        queue, visited = deque(roots), set()
        while queue:
            library = queue.popleft()
            if library in visited:
                continue
            visited.add(library)
            if not any(PurePosixPath(library).is_relative_to(prefix) for prefix in permitted):
                findings.append(dict(domain=name, library=library, kind="library-outside-permitted-paths"))
                continue
            metadata = reader(virtual[library])
            visited_records.append(dict(domain=name, library=library, sha256=virtual[library]["sha256"], **metadata))
            if metadata["rpath"] or metadata["runpath"]:
                findings.append(dict(domain=name, library=library, kind="unsupported-elf-search-path",
                                     rpath=metadata["rpath"], runpath=metadata["runpath"]))
            for needed in metadata["needed"]:
                if "/" in needed:
                    if not needed.startswith("/"):
                        findings.append(dict(domain=name, library=library, needed=needed, kind="relative-needed-path"))
                        continue
                    candidates = [str(absolute_path(needed))]
                else:
                    candidates = [str(prefix / needed) for prefix in search]
                allowed = [path for path in candidates if any(PurePosixPath(path).is_relative_to(prefix) for prefix in permitted)]
                target = next((path for path in allowed if path in virtual), None)
                edge = dict(domain=name, library=library, needed=needed, resolved=target)
                edges.append(edge)
                if target is None:
                    outside = sorted(path for path in virtual if PurePosixPath(path).name == needed and path not in allowed)
                    findings.append(dict(edge, kind="missing-dt-needed", searched=allowed,
                                         outside_domain_candidates=outside, inherit_used=False))
                else:
                    queue.append(target)
    library_dirs = {str(PurePosixPath(path).parent) for path in virtual if is_library(path)}
    for directory in sorted(library_dirs - owned_dirs):
        findings.append(dict(kind="uncovered-library-directory", directory=directory))
    return findings, dict(edges=edges, libraries=visited_records, domain_count=len(domains), inherit_used=False)


def check(package, inputs, root, readelf):
    config = inputs["namespaces"]
    manifest_path = verified_file(root, config["manifest"])
    package.native_artifact(config["owner_artifact"])
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != 1:
        raise ValueError("invalid namespace manifest")
    sources = manifest["config_sources"]
    if not sources:
        raise ValueError("namespace config source evidence required")
    for entry in sources:
        verified_file(manifest_path.parent, entry)
    virtual = package.virtual_files()
    for entry in config.get("system_files", []):
        path = str(absolute_path(entry["target"]))
        if path in virtual:
            raise ValueError("system snapshot shadows packaged target: " + path)
        virtual[path] = dict(path=verified_file(root, entry), sha256=entry["sha256"], package_path=entry["path"])
    reader = ElfReader(readelf)
    findings, report = scan_domains(virtual, manifest["domains"], reader)
    report["readelf_evidence"] = reader.evidence
    report["owner_artifact"] = config["owner_artifact"]
    report["scope"] = "sealed effective domain paths and package/system-snapshot files; no inherit or symbol-version proof"
    return findings, report
