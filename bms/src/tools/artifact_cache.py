#!/usr/bin/env python3
"""Content-addressed Bridge artifact transport with fail-closed SHA checks."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


COMPONENTS = ("source", "header", "compiler", "sysroot", "provider", "profile")
GENERATION_RE = re.compile(r"^gk1-[0-9a-f]{64}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SAFE_ARTIFACT_RE = re.compile(
    r"^[A-Za-z0-9._+@=-]+(?:/[A-Za-z0-9._+@=-]+)*$"
)
SAFE_ENDPOINT_RE = re.compile(r"^[A-Za-z0-9._@:-]+$")
SAFE_REMOTE_ROOT_RE = re.compile(r"^/[A-Za-z0-9._+:/=-]+$")
MANIFEST_NAME = "GENERATION.json"
CHECKSUM_NAME = "SHA256SUMS"
RESERVED_NAMES = frozenset((MANIFEST_NAME, CHECKSUM_NAME))


class ArtifactCacheError(RuntimeError):
    pass


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _validate_hash(value: str, label: str) -> str:
    if not HASH_RE.fullmatch(value):
        raise ArtifactCacheError("{} must be a lowercase SHA-256".format(label))
    return value


def _validate_generation_key(value: str) -> str:
    if not GENERATION_RE.fullmatch(value):
        raise ArtifactCacheError("invalid generation key: {!r}".format(value))
    return value


def _tree_records(root: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISREG(info.st_mode):
            records.append(
                {
                    "path": relative,
                    "kind": "file",
                    "sha256": _sha256_file(path),
                    "size": info.st_size,
                    "executable": bool(info.st_mode & 0o111),
                }
            )
        elif stat.S_ISDIR(info.st_mode):
            records.append({"path": relative, "kind": "directory"})
        elif stat.S_ISLNK(info.st_mode):
            records.append(
                {"path": relative, "kind": "symlink", "target": os.readlink(str(path))}
            )
        else:
            raise ArtifactCacheError(
                "unsupported component input node: {}".format(path)
            )
    return records


def digest_component_path(path_text: str) -> str:
    path = Path(path_text)
    if not path.exists() and not path.is_symlink():
        raise ArtifactCacheError("component input does not exist: {}".format(path))
    info = path.lstat()
    if stat.S_ISREG(info.st_mode):
        identity = {
            "kind": "file",
            "sha256": _sha256_file(path),
            "size": info.st_size,
            "executable": bool(info.st_mode & 0o111),
        }
    elif stat.S_ISDIR(info.st_mode):
        identity = {"kind": "tree", "entries": _tree_records(path)}
    elif stat.S_ISLNK(info.st_mode):
        identity = {"kind": "symlink", "target": os.readlink(str(path))}
    else:
        raise ArtifactCacheError("unsupported component input: {}".format(path))
    return hashlib.sha256(_canonical_json(identity)).hexdigest()


def resolve_component(value: str) -> str:
    if value.startswith("sha256:"):
        return _validate_hash(value[len("sha256:") :], "component digest")
    return digest_component_path(value)


def generation_key(components: Mapping[str, str]) -> str:
    if set(components) != set(COMPONENTS):
        missing = sorted(set(COMPONENTS) - set(components))
        extra = sorted(set(components) - set(COMPONENTS))
        raise ArtifactCacheError(
            "generation components mismatch; missing={} extra={}".format(missing, extra)
        )
    normalized = {
        name: _validate_hash(str(components[name]), name) for name in COMPONENTS
    }
    material = {"schema_version": 1, "components": normalized}
    return "gk1-" + hashlib.sha256(_canonical_json(material)).hexdigest()


def make_key_manifest(component_values: Mapping[str, str]) -> Dict[str, Any]:
    components = {
        name: resolve_component(component_values[name]) for name in COMPONENTS
    }
    return {
        "schema_version": 1,
        "kind": "bridge-generation-key",
        "generation_key": generation_key(components),
        "components": components,
    }


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, ValueError) as exc:
        raise ArtifactCacheError("cannot read JSON {}: {}".format(path, exc))
    if not isinstance(value, dict):
        raise ArtifactCacheError("{} must contain a JSON object".format(path))
    return value


def load_key_manifest(path: Path) -> Dict[str, Any]:
    value = _load_json(path)
    if value.get("schema_version") != 1:
        raise ArtifactCacheError("unsupported key manifest schema")
    if value.get("kind") != "bridge-generation-key":
        raise ArtifactCacheError("not a generation key manifest")
    components = value.get("components")
    if not isinstance(components, dict):
        raise ArtifactCacheError("generation components must be an object")
    expected = generation_key(components)
    if value.get("generation_key") != expected:
        raise ArtifactCacheError("generation key does not match its six components")
    return value


def _validate_artifact_relative(path: str) -> str:
    if not SAFE_ARTIFACT_RE.fullmatch(path):
        raise ArtifactCacheError(
            "artifact path is not portable/checksum-safe: {!r}".format(path)
        )
    if any(part in ("", ".", "..") for part in PurePosixPath(path).parts):
        raise ArtifactCacheError("artifact path may not traverse: {!r}".format(path))
    if path in RESERVED_NAMES:
        raise ArtifactCacheError("reserved artifact path: {}".format(path))
    return path


def _artifact_inventory(bundle: Path) -> List[Dict[str, Any]]:
    if not bundle.is_dir():
        raise ArtifactCacheError("bundle is not a directory: {}".format(bundle))
    artifacts: List[Dict[str, Any]] = []
    for path in sorted(bundle.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(bundle).as_posix()
        if relative in RESERVED_NAMES:
            continue
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise ArtifactCacheError(
                "bundle payload must contain regular files only: {}".format(relative)
            )
        _validate_artifact_relative(relative)
        artifacts.append(
            {
                "path": relative,
                "sha256": _sha256_file(path),
                "size": info.st_size,
                "executable": bool(info.st_mode & 0o111),
            }
        )
    if not artifacts:
        raise ArtifactCacheError("bundle has no artifact payload")
    return artifacts


def _checksum_lines(manifest_sha256: str, artifacts: Iterable[Mapping[str, Any]]) -> str:
    lines = ["{}  {}".format(manifest_sha256, MANIFEST_NAME)]
    lines.extend(
        "{}  {}".format(item["sha256"], item["path"]) for item in artifacts
    )
    return "\n".join(lines) + "\n"


def seal_bundle(bundle: Path, key_manifest_path: Path) -> Tuple[str, str]:
    key_manifest = load_key_manifest(key_manifest_path)
    artifacts = _artifact_inventory(bundle)
    manifest = {
        "schema_version": 1,
        "kind": "bridge-artifact-generation",
        "generation_key": key_manifest["generation_key"],
        "components": key_manifest["components"],
        "artifacts": artifacts,
    }
    manifest_path = bundle / MANIFEST_NAME
    checksum_path = bundle / CHECKSUM_NAME
    manifest_path.write_bytes(_canonical_json(manifest))
    manifest_sha256 = _sha256_file(manifest_path)
    checksum_path.write_text(
        _checksum_lines(manifest_sha256, artifacts), encoding="utf-8"
    )
    verify_bundle(
        bundle,
        expected_key=manifest["generation_key"],
        expected_manifest_sha256=manifest_sha256,
    )
    return manifest["generation_key"], manifest_sha256


def _validate_generation_manifest(value: Dict[str, Any]) -> None:
    if set(value) != {
        "schema_version",
        "kind",
        "generation_key",
        "components",
        "artifacts",
    }:
        raise ArtifactCacheError("generation manifest has unknown or missing fields")
    if value["schema_version"] != 1 or value["kind"] != "bridge-artifact-generation":
        raise ArtifactCacheError("unsupported generation manifest")
    components = value["components"]
    if not isinstance(components, dict):
        raise ArtifactCacheError("generation components must be an object")
    expected_key = generation_key(components)
    if value["generation_key"] != expected_key:
        raise ArtifactCacheError("generation manifest key mismatch")
    artifacts = value["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        raise ArtifactCacheError("generation must contain artifacts")
    previous = ""
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "sha256",
            "size",
            "executable",
        }:
            raise ArtifactCacheError("invalid artifact manifest entry")
        path = _validate_artifact_relative(str(item["path"]))
        if path <= previous:
            raise ArtifactCacheError("artifact entries must be unique and sorted")
        previous = path
        _validate_hash(str(item["sha256"]), "artifact sha256")
        if not isinstance(item["size"], int) or item["size"] < 0:
            raise ArtifactCacheError("artifact size must be non-negative")
        if not isinstance(item["executable"], bool):
            raise ArtifactCacheError("artifact executable flag must be boolean")


def verify_bundle(
    bundle: Path,
    expected_key: Optional[str] = None,
    expected_manifest_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    manifest_path = bundle / MANIFEST_NAME
    checksum_path = bundle / CHECKSUM_NAME
    manifest = _load_json(manifest_path)
    _validate_generation_manifest(manifest)
    if expected_key is not None and manifest["generation_key"] != _validate_generation_key(
        expected_key
    ):
        raise ArtifactCacheError("bundle generation key is not the requested key")
    manifest_sha256 = _sha256_file(manifest_path)
    if expected_manifest_sha256 is not None:
        expected_manifest_sha256 = _validate_hash(
            expected_manifest_sha256, "expected manifest sha256"
        )
        if manifest_sha256 != expected_manifest_sha256:
            raise ArtifactCacheError("generation manifest SHA-256 mismatch")
    actual_artifacts = _artifact_inventory(bundle)
    if actual_artifacts != manifest["artifacts"]:
        raise ArtifactCacheError("bundle payload differs from generation manifest")
    expected_checksums = _checksum_lines(manifest_sha256, actual_artifacts)
    try:
        actual_checksums = checksum_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ArtifactCacheError("cannot read {}: {}".format(checksum_path, exc))
    if actual_checksums != expected_checksums:
        raise ArtifactCacheError("SHA256SUMS is missing, reordered, or inconsistent")
    return manifest


def load_config(path: Path) -> Dict[str, Any]:
    config = _load_json(path)
    if config.get("schema_version") != 1 or config.get("transport") != "rsync+ssh":
        raise ArtifactCacheError("config must use schema 1 and rsync+ssh")
    if not COMMIT_RE.fullmatch(str(config.get("canonical_main", ""))):
        raise ArtifactCacheError("config must bind one exact canonical main commit")
    if config.get("direct_test_transport") != "forbidden":
        raise ArtifactCacheError("direct mounted test transport must stay forbidden")
    stores = config.get("stores")
    if not isinstance(stores, dict) or set(stores) != {"primary", "linux_cache"}:
        raise ArtifactCacheError("config must define primary and linux_cache stores")
    for name, store in stores.items():
        if not isinstance(store, dict):
            raise ArtifactCacheError("{} store must be an object".format(name))
        endpoint = str(store.get("endpoint", ""))
        if endpoint.startswith("-") or not SAFE_ENDPOINT_RE.fullmatch(endpoint):
            raise ArtifactCacheError("unsafe endpoint for {}".format(name))
        port = store.get("ssh_port")
        if not isinstance(port, int) or not 1 <= port <= 65535:
            raise ArtifactCacheError("invalid SSH port for {}".format(name))
        _validate_remote_root(str(store.get("root", "")))
        if store.get("sha256_command") not in ("sha256sum", "shasum"):
            raise ArtifactCacheError("unsupported SHA command for {}".format(name))
        if store.get("readiness") not in ("ready", "pending_c01"):
            raise ArtifactCacheError("invalid readiness for {}".format(name))
    local = config.get("local")
    if not isinstance(local, dict) or local.get("keep_generation_count") != 1:
        raise ArtifactCacheError("local policy must keep exactly one generation")
    return config


def _validate_remote_root(value: str) -> str:
    if not SAFE_REMOTE_ROOT_RE.fullmatch(value):
        raise ArtifactCacheError("unsafe remote root: {!r}".format(value))
    normalized = str(PurePosixPath(value))
    if normalized != value or normalized in ("/", "/opt", "/opt/build-trees"):
        raise ArtifactCacheError("remote root is too broad or not normalized")
    return value


def _store(config: Mapping[str, Any], name: str, require_ready: bool = True) -> Dict[str, Any]:
    stores = config["stores"]
    if name not in stores:
        raise ArtifactCacheError("unknown store: {}".format(name))
    store = stores[name]
    if require_ready and store["readiness"] != "ready":
        raise ArtifactCacheError(
            "{} store is not ready ({})".format(name, store["readiness"])
        )
    return store


def _ssh_args(store: Mapping[str, Any]) -> List[str]:
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=15",
        "-p",
        str(store["ssh_port"]),
        str(store["endpoint"]),
    ]


def _run(command: Sequence[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            list(command),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ArtifactCacheError("required command is unavailable: {}".format(exc))
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise ArtifactCacheError(
            "command failed with rc={}: {}".format(exc.returncode, detail)
        )


def _remote(store: Mapping[str, Any], script: str) -> subprocess.CompletedProcess:
    return _run(_ssh_args(store) + ["sh", "-c", shlex.quote(script)])


def _remote_checksum_script(store: Mapping[str, Any], directory: str) -> str:
    quoted = shlex.quote(directory)
    if store["sha256_command"] == "sha256sum":
        verify = "sha256sum -c {}".format(shlex.quote(CHECKSUM_NAME))
    else:
        verify = "shasum -a 256 -c {}".format(shlex.quote(CHECKSUM_NAME))
    return "set -eu; cd {}; {}".format(quoted, verify)


def init_store(config: Mapping[str, Any], store_name: str) -> None:
    store = _store(config, store_name)
    root = _validate_remote_root(store["root"])
    script = (
        "set -eu; umask 027; "
        "test ! -L {root}; "
        "mkdir -p {generations} {incoming}; "
        "test -d {generations}; test -d {incoming}"
    ).format(
        root=shlex.quote(root),
        generations=shlex.quote(root + "/generations"),
        incoming=shlex.quote(root + "/.incoming"),
    )
    _remote(store, script)


def _rsync_ssh_transport(store: Mapping[str, Any]) -> str:
    return "ssh -o BatchMode=yes -o ConnectTimeout=15 -p {}".format(
        store["ssh_port"]
    )


def publish_bundle(
    config: Mapping[str, Any], store_name: str, bundle: Path
) -> Tuple[str, str]:
    store = _store(config, store_name)
    manifest = verify_bundle(bundle)
    key = manifest["generation_key"]
    manifest_sha256 = _sha256_file(bundle / MANIFEST_NAME)
    root = _validate_remote_root(store["root"])
    stage = "{}/.incoming/{}.{}".format(root, key, uuid.uuid4().hex)
    final = "{}/generations/{}".format(root, key)
    _remote(
        store,
        "set -eu; test -d {root}; test ! -e {stage}; mkdir {stage}".format(
            root=shlex.quote(root + "/generations"), stage=shlex.quote(stage)
        ),
    )
    remote_target = "{}:{}/".format(store["endpoint"], stage)
    _run(
        [
            "rsync",
            "-a",
            "-e",
            _rsync_ssh_transport(store),
            str(bundle) + "/",
            remote_target,
        ]
    )
    _remote(store, _remote_checksum_script(store, stage))
    if store["sha256_command"] == "sha256sum":
        remote_manifest_hash = "sha256sum {} | awk '{{print $1}}'".format(
            shlex.quote(final + "/" + MANIFEST_NAME)
        )
    else:
        remote_manifest_hash = "shasum -a 256 {} | awk '{{print $1}}'".format(
            shlex.quote(final + "/" + MANIFEST_NAME)
        )
    promote = (
        "set -eu; "
        "if test -e {final}; then "
        "  test -d {final}; "
        "  test \"$({remote_manifest_hash})\" = {manifest_sha}; "
        "  rm -rf {stage}; "
        "else "
        "  mv {stage} {final}; "
        "fi"
    ).format(
        final=shlex.quote(final),
        manifest_sha=shlex.quote(manifest_sha256),
        stage=shlex.quote(stage),
        remote_manifest_hash=remote_manifest_hash,
    )
    _remote(store, promote)
    _remote(store, _remote_checksum_script(store, final))
    return key, manifest_sha256


def _ensure_local_layout(root: Path) -> Tuple[Path, Path, Path]:
    resolved = root.resolve()
    home = Path.home().resolve()
    if resolved in (Path(resolved.anchor), home, Path.cwd().resolve()):
        raise ArtifactCacheError("local cache root is too broad")
    generations = resolved / "generations"
    incoming = resolved / ".incoming"
    hot_apks = resolved / "hot-apks"
    for directory in (generations, incoming, hot_apks):
        if directory.is_symlink():
            raise ArtifactCacheError(
                "local cache layout may not use symlinks: {}".format(directory)
            )
        directory.mkdir(parents=True, exist_ok=True)
        if not directory.is_dir():
            raise ArtifactCacheError(
                "local cache layout is not a directory: {}".format(directory)
            )
    return generations, incoming, hot_apks


def _write_current(root: Path, key: str) -> None:
    _validate_generation_key(key)
    temporary = root / (".CURRENT." + uuid.uuid4().hex)
    temporary.write_text(key + "\n", encoding="utf-8")
    os.replace(str(temporary), str(root / "CURRENT"))


def prune_local(root: Path) -> List[str]:
    generations, _, _ = _ensure_local_layout(root)
    current_path = root.resolve() / "CURRENT"
    try:
        current = current_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ArtifactCacheError("cannot read CURRENT: {}".format(exc))
    _validate_generation_key(current)
    removed: List[str] = []
    for candidate in generations.iterdir():
        if not candidate.is_dir() or not GENERATION_RE.fullmatch(candidate.name):
            continue
        if candidate.name == current:
            continue
        shutil.rmtree(str(candidate))
        removed.append(candidate.name)
    return sorted(removed)


def fetch_bundle(
    config: Mapping[str, Any],
    store_name: str,
    key: str,
    manifest_sha256: str,
    local_root: Path,
) -> Path:
    store = _store(config, store_name)
    key = _validate_generation_key(key)
    manifest_sha256 = _validate_hash(manifest_sha256, "manifest sha256")
    root = _validate_remote_root(store["root"])
    remote_dir = "{}/generations/{}".format(root, key)
    _remote(store, _remote_checksum_script(store, remote_dir))
    generations, incoming, _ = _ensure_local_layout(local_root)
    stage = incoming / (key + "." + uuid.uuid4().hex)
    stage.mkdir()
    remote_source = "{}:{}/".format(store["endpoint"], remote_dir)
    try:
        _run(
            [
                "rsync",
                "-a",
                "-e",
                _rsync_ssh_transport(store),
                remote_source,
                str(stage) + "/",
            ]
        )
        verify_bundle(
            stage,
            expected_key=key,
            expected_manifest_sha256=manifest_sha256,
        )
        final = generations / key
        if final.exists():
            verify_bundle(
                final,
                expected_key=key,
                expected_manifest_sha256=manifest_sha256,
            )
            shutil.rmtree(str(stage))
        else:
            os.replace(str(stage), str(final))
        _write_current(local_root.resolve(), key)
        prune_local(local_root)
        return final
    except Exception:
        if stage.exists():
            shutil.rmtree(str(stage))
        raise


def mirror_bundle(
    config: Mapping[str, Any],
    source_store_name: str,
    destination_store_name: str,
    key: str,
    manifest_sha256: str,
    scratch_root: Path,
) -> Tuple[str, str]:
    if source_store_name == destination_store_name:
        raise ArtifactCacheError("mirror source and destination must differ")
    scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bridge-artifact-mirror-", dir=str(scratch_root)) as temp:
        local_root = Path(temp) / "cache"
        bundle = fetch_bundle(
            config,
            source_store_name,
            key,
            manifest_sha256,
            local_root,
        )
        return publish_bundle(config, destination_store_name, bundle)


def _component_arguments(parser: argparse.ArgumentParser) -> None:
    for name in COMPONENTS:
        parser.add_argument(
            "--" + name,
            required=True,
            help="input path or sha256:<64 lowercase hex>",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    key_parser = subparsers.add_parser("key", help="derive a six-component key")
    _component_arguments(key_parser)
    key_parser.add_argument("--output", required=True, type=Path)

    seal_parser = subparsers.add_parser("seal", help="seal an artifact bundle")
    seal_parser.add_argument("--bundle", required=True, type=Path)
    seal_parser.add_argument("--key-manifest", required=True, type=Path)

    verify_parser = subparsers.add_parser("verify", help="verify a sealed bundle")
    verify_parser.add_argument("--bundle", required=True, type=Path)
    verify_parser.add_argument("--generation-key")
    verify_parser.add_argument("--manifest-sha256")

    init_parser = subparsers.add_parser("init-store", help="initialize a remote store")
    init_parser.add_argument("--config", required=True, type=Path)
    init_parser.add_argument("--store", required=True, choices=("primary", "linux_cache"))

    publish_parser = subparsers.add_parser("publish", help="publish by rsync and SHA")
    publish_parser.add_argument("--config", required=True, type=Path)
    publish_parser.add_argument(
        "--store", required=True, choices=("primary", "linux_cache")
    )
    publish_parser.add_argument("--bundle", required=True, type=Path)

    fetch_parser = subparsers.add_parser("fetch", help="fetch one exact generation")
    fetch_parser.add_argument("--config", required=True, type=Path)
    fetch_parser.add_argument(
        "--store", required=True, choices=("primary", "linux_cache")
    )
    fetch_parser.add_argument("--generation-key", required=True)
    fetch_parser.add_argument("--manifest-sha256", required=True)
    fetch_parser.add_argument("--local-root", required=True, type=Path)

    mirror_parser = subparsers.add_parser(
        "mirror", help="mirror primary to Linux cache through verified scratch"
    )
    mirror_parser.add_argument("--config", required=True, type=Path)
    mirror_parser.add_argument(
        "--source-store", required=True, choices=("primary", "linux_cache")
    )
    mirror_parser.add_argument(
        "--destination-store", required=True, choices=("primary", "linux_cache")
    )
    mirror_parser.add_argument("--generation-key", required=True)
    mirror_parser.add_argument("--manifest-sha256", required=True)
    mirror_parser.add_argument("--scratch-root", required=True, type=Path)

    prune_parser = subparsers.add_parser(
        "prune-local", help="keep CURRENT generation and hot APKs only"
    )
    prune_parser.add_argument("--local-root", required=True, type=Path)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "key":
            values = {name: getattr(args, name) for name in COMPONENTS}
            manifest = make_key_manifest(values)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(_canonical_json(manifest))
            print(manifest["generation_key"])
        elif args.command == "seal":
            key, manifest_sha256 = seal_bundle(args.bundle, args.key_manifest)
            print("{} {}".format(key, manifest_sha256))
        elif args.command == "verify":
            manifest = verify_bundle(
                args.bundle, args.generation_key, args.manifest_sha256
            )
            print(
                "{} {}".format(
                    manifest["generation_key"],
                    _sha256_file(args.bundle / MANIFEST_NAME),
                )
            )
        elif args.command == "init-store":
            config = load_config(args.config)
            init_store(config, args.store)
            print("{} ready".format(args.store))
        elif args.command == "publish":
            config = load_config(args.config)
            key, manifest_sha256 = publish_bundle(config, args.store, args.bundle)
            print("{} {}".format(key, manifest_sha256))
        elif args.command == "fetch":
            config = load_config(args.config)
            result = fetch_bundle(
                config,
                args.store,
                args.generation_key,
                args.manifest_sha256,
                args.local_root,
            )
            print(result)
        elif args.command == "mirror":
            config = load_config(args.config)
            key, manifest_sha256 = mirror_bundle(
                config,
                args.source_store,
                args.destination_store,
                args.generation_key,
                args.manifest_sha256,
                args.scratch_root,
            )
            print("{} {}".format(key, manifest_sha256))
        elif args.command == "prune-local":
            removed = prune_local(args.local_root)
            print(json.dumps({"removed": removed}, sort_keys=True))
        else:
            raise ArtifactCacheError("unknown command")
    except ArtifactCacheError as exc:
        print("FAIL_CLOSED: {}".format(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
