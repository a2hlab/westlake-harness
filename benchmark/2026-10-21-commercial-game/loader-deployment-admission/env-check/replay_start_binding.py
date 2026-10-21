#!/usr/bin/env python3
"""Replay original constructor/start wiring with inert Board/import seams only."""
import ast
import hashlib
import json
from pathlib import Path
import shlex
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent


def method(path, cls, name):
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
    return next(n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == name)


def main():
    u7 = ROOT / "sources/scripts/lab/u7_executor.py"
    native = ROOT / "sources/scripts/lab/deploy_generation.py"
    ctor = method(u7, "DeviceIO", "__init__")
    start = method(native, "Deployment", "start")
    events = []

    class InertBoard:
        def __init__(self, *args):
            events.append("inert Board constructed; no transport")
            self.boot = "offline-only"

        def ready(self):
            events.append("inert ready; no lock or device access")

    fake_batch = SimpleNamespace(Board=InertBoard)
    fake_spec = SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module: None))
    namespace = {
        "sys": SimpleNamespace(platform="linux"), "Path": Path, "shlex": shlex,
        "native": SimpleNamespace(SERIALS={"5ea34a4500000000000000001123012c"}),
        "lab_paths": SimpleNamespace(harness=lambda: ROOT, tools=lambda: ROOT),
        "importlib": SimpleNamespace(util=SimpleNamespace(
            spec_from_file_location=lambda *args: fake_spec,
            module_from_spec=lambda spec: fake_batch)),
    }
    # Compile the exact original bodies, not a reimplementation of start/init.
    exec(compile(ast.Module(body=[ctor, start], type_ignores=[]), "original-source-extract", "exec"), namespace)
    base = type("Deployment", (), {"start": namespace["start"]})
    io_type = type("DeviceIO", (base,), {"__init__": namespace["__init__"]})
    with tempfile.TemporaryDirectory(prefix="g19-start-binding-") as tmp:
        io = io_type("5ea34a4500000000000000001123012c", "offline", Path(tmp))
        before = sorted(vars(io))
        try:
            io.start("not-used-before-failure")
        except AttributeError as exc:
            error = str(exc)
        else:
            raise AssertionError("expected missing DeviceIO start binding was not reproduced")
    assert "'a'" in error and "a" not in before and "m" not in before
    print(json.dumps({
        "status": "COUNTEREXAMPLE_REPRODUCED", "error": error,
        "constructed_attributes": before, "missing_start_inputs": ["a", "m"],
        "events": events, "device_io": False, "start_service_called": False,
        "original_constructor_line": ctor.lineno, "original_start_line": start.lineno,
        "u7_archive_sha256": hashlib.sha256(u7.read_bytes()).hexdigest(),
        "native_archive_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
        "scope": "constructor/start binding only; inert platform/import/Board seams, original method bodies unchanged",
    }, indent=2))


if __name__ == "__main__":
    main()
