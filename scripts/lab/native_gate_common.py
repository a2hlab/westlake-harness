"""Sealed inputs and exact exceptions shared by offline native gates."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re


SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_object)


def relative_file(root, name):
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("invalid relative path")
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or str(relative) != name:
        raise ValueError("unsafe relative path: " + name)
    root = Path(root).resolve()
    target = root / name
    if not target.resolve().is_relative_to(root):
        raise ValueError("input escapes root: " + name)
    if any(parent.is_symlink() for parent in [target, *target.parents] if parent != root and parent.is_relative_to(root)):
        raise ValueError("symlink input: " + name)
    if not target.is_file():
        raise ValueError("missing input: " + name)
    return target


def verified_file(root, entry):
    expected = entry["sha256"]
    if not isinstance(expected, str) or not SHA256.fullmatch(expected):
        raise ValueError("invalid SHA256")
    target = relative_file(root, entry["path"])
    if sha256(target) != expected:
        raise ValueError("SHA mismatch: " + entry["path"])
    return target


def absolute_path(name):
    if not isinstance(name, str) or not name.startswith("/") or "\\" in name:
        raise ValueError("expected absolute deployment path")
    path = PurePosixPath(name)
    if ".." in path.parts or str(path) != name or "$" in name or "%" in name:
        raise ValueError("unresolved or unsafe deployment path: " + name)
    return path


class Package:
    def __init__(self, root):
        self.root = Path(root).resolve()
        manifest = relative_file(self.root, "package.json")
        self.sha256 = sha256(manifest)
        self.manifest = read_json(manifest)
        self.files = self.manifest["files"]
        if self.manifest.get("schema") != 1 or not isinstance(self.files, dict) or not self.files:
            raise ValueError("invalid or empty package manifest")
        self.paths = {name: verified_file(self.root, {"path": name, "sha256": digest})
                      for name, digest in self.files.items()}

    def artifact(self, entry):
        if self.files.get(entry["path"]) != entry["sha256"]:
            raise ValueError("artifact is not sealed by candidate package: " + entry["path"])
        return verified_file(self.root, entry)

    def native_artifact(self, entry):
        path = self.artifact(entry)
        with path.open("rb") as stream:
            header = stream.read(20)
        if (len(header) != 20 or header[:6] != b"\x7fELF\x02\x01"
                or int.from_bytes(header[18:20], "little") != 183
                or int.from_bytes(header[16:18], "little") not in {2, 3}):
            raise ValueError("native artifact must be an AArch64 ELF executable/shared object")
        return path

    def virtual_files(self):
        result = {}
        for mount in self.manifest["mounts"]:
            source = mount["source"]
            source_path = PurePosixPath(source)
            if source_path.is_absolute() or ".." in source_path.parts or str(source_path) != source:
                raise ValueError("unsafe mount source")
            target = absolute_path(mount["target"])
            members = [name for name in self.files if name == source or name.startswith(source + "/")]
            if not members:
                raise ValueError("unsealed or empty mount source: " + source)
            local_source = self.root / source
            if local_source.is_dir():
                actual = {str(path.relative_to(self.root)) for path in local_source.rglob("*") if path.is_file() or path.is_symlink()}
                if actual != set(members):
                    raise ValueError("unsealed or missing files under directory mount: " + source)
            for old in list(result):
                if PurePosixPath(old).is_relative_to(target):
                    del result[old]
            for name in members:
                deployed = str(target / PurePosixPath(name).relative_to(source_path))
                result[deployed] = dict(path=self.paths[name], sha256=self.files[name], package_path=name)
        if not result:
            raise ValueError("empty deployment path view")
        return result


def load_inputs(package, path):
    path = Path(path).resolve()
    inputs = read_json(path)
    if inputs.get("schema_version") != 1 or inputs.get("package_manifest_sha256") != package.sha256:
        raise ValueError("build inputs do not bind candidate package.json")
    return inputs, path.parent, sha256(path)


def apply_exceptions(gate, findings, package_sha, inputs_sha, registry):
    if registry.get("schema_version") != 1 or not isinstance(registry.get("exceptions"), list):
        raise ValueError("invalid exception registry")
    entries = {}
    for entry in registry["exceptions"]:
        for field in ("issue_id", "package_manifest_sha256", "inputs_sha256"):
            if not isinstance(entry.get(field), str) or not SHA256.fullmatch(entry[field]):
                raise ValueError("exception requires exact " + field)
        if entry.get("gate") not in {"N1", "N2"}:
            raise ValueError("unknown exception gate")
        for field in ("reason", "removal_condition", "approved_by", "approved_at"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError("exception requires " + field)
        evidence = entry.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("exception requires evidence")
        for name in evidence:
            if not isinstance(name, str) or not name or PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
                raise ValueError("exception evidence must be repository-relative")
        identity = (entry["gate"], entry["package_manifest_sha256"], entry["inputs_sha256"], entry["issue_id"])
        if identity in entries:
            raise ValueError("duplicate exception")
        entries[identity] = entry
    observed, rows = set(), []
    for finding in findings:
        bound = dict(gate=gate, package_manifest_sha256=package_sha,
                     inputs_sha256=inputs_sha, finding=finding)
        issue_id = digest_bytes(json.dumps(bound, sort_keys=True, separators=(",", ":")).encode())
        identity = (gate, package_sha, inputs_sha, issue_id)
        observed.add(identity)
        row = dict(finding, issue_id=issue_id, disposition="EXCEPTED" if identity in entries else "REJECT")
        if identity in entries:
            row["exception"] = entries[identity]
        rows.append(row)
    stale = [identity[3] for identity in entries if identity[:3] == (gate, package_sha, inputs_sha) and identity not in observed]
    return dict(findings=rows, rejected=sum(row["disposition"] == "REJECT" for row in rows),
                excepted=sum(row["disposition"] == "EXCEPTED" for row in rows), stale=sorted(stale),
                warnings=[dict(status="STALE", issue_id=issue_id) for issue_id in sorted(stale)])
