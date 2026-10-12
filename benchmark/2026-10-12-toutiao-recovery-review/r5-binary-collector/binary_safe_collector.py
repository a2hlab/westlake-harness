"""Binary-safe host_cmdline transport; frozen validators remain unchanged."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys


sys.dont_write_bytecode = True
WORKSPACES = Path(os.environ.get("WORKSPACES", Path(__file__).resolve().parent.parents[3]))
FROZEN = WORKSPACES / "westlake-harness/benchmark/2026-10-12-exact-realization"
PINS = {
    "observations": "e13396359c7edd4686708b4a761bb0ee26c5b3fd540873a5a9d4eacc9932d764",
    "realization": "15a6dc52ee250a9277886dad9f3eb780f7c2dc2a81d934c6fa0ae95ad5aafc14",
    "seal_checks": "ff23281e9a918943c87dfd33e422350e5f00184e4ddd5ddeac290daa14e899f5",
    "selfcheck": "a0333c67229c3523943c6182a772fe4a60d6b9a9f1ae36f8186a81e056ea99d3",
}
SHA_MARKER = b"\nR5_CMDLINE_SHA256="


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_pinned(path, name, expected):
    if digest(path) != expected:
        raise ValueError("frozen dependency drift: " + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(FROZEN))
for dependency in ("observations", "realization", "seal_checks"):
    load_pinned(FROZEN / (dependency + ".py"), dependency, PINS[dependency])
original = load_pinned(FROZEN / "selfcheck.py", "r5_original_selfcheck", PINS["selfcheck"])


def portable(path):
    path = Path(path).resolve()
    try:
        return "$WORKSPACES/" + str(path.relative_to(WORKSPACES.resolve()))
    except ValueError:
        return str(path)


def decode_hex(encoded, proc_path):
    if encoded.count(SHA_MARKER) != 1:
        raise ValueError("binary transport SHA delimiter missing/duplicate")
    hexadecimal, checksum = encoded.split(SHA_MARKER)
    pattern = rb"([0-9a-f]{64})[ \t]+" + re.escape(proc_path.encode("ascii")) + rb"\r?\n?\Z"
    matched = re.fullmatch(pattern, checksum)
    if matched is None:
        raise ValueError("binary transport board SHA/path malformed")
    if re.fullmatch(rb"[ \t\r\n]*(?:[0-9a-fA-F]{2}[ \t\r\n]+)*[0-9a-fA-F]{2}[ \t\r\n]*", hexadecimal) is None:
        raise ValueError("binary transport od hex malformed/truncated")
    decoded = bytes.fromhex(hexadecimal.decode("ascii"))
    board_sha = matched[1].decode("ascii")
    if hashlib.sha256(decoded).hexdigest() != board_sha:
        raise ValueError("decoded bytes differ from board SHA")
    return decoded, board_sha


class BinarySafeCollector(original.ReadOnlyCollector):
    def read(self, kind, command):
        if kind != "host_cmdline":
            return super().read(kind, command)
        matched = re.fullmatch(r"cat (/proc/([1-9][0-9]*)/cmdline)", command)
        if matched is None or int(matched[2]) <= 1:
            raise ValueError("host_cmdline requires exact logical cat /proc/PID/cmdline")
        proc_path = matched[1]
        wrapped = ("set -eu; set -o pipefail; cat " + proc_path + " | od -An -v -tx1; "
                   "printf '\\nR5_CMDLINE_SHA256='; sha256sum " + proc_path)
        number = len(self.commands)
        prefix = self.directory / ("%03d-%s" % (number, kind))
        audit = {"schema": "binary-cmdline-read/v1", "logical_command": command,
                 "encoded_command": wrapped, "encoding": "od-hex", "accepted": False,
                 "adapter": {"path": portable(__file__), "sha256": digest(__file__)}}
        try:
            encoded, transport = super().read(kind, wrapped)
            audit.update(encoded_stdout=transport["stdout"], actual_argv=self.commands[-1]["argv"],
                         transport_rc=transport["transport_rc"], remote_rc=transport["remote_rc"])
            decoded, board_sha = decode_hex(encoded, proc_path)
            decoded_path = prefix.with_suffix(".decoded.stdout")
            with decoded_path.open("xb") as stream:
                stream.write(decoded)
            stdout = {"path": decoded_path.name, "sha256": digest(decoded_path)}
            audit.update(accepted=True, decoded_stdout=stdout, board_sha256=board_sha, decoded_bytes=len(decoded))
            original.dump_fresh(prefix.with_suffix(".binary.json"), audit)
            self.commands[-1]["binary_transport"] = audit
            reading = {"command": command, "transport_rc": transport["transport_rc"],
                       "remote_rc": transport["remote_rc"], "stdout": stdout,
                       "binary_transport": {"path": prefix.with_suffix(".binary.json").name,
                                            "sha256": digest(prefix.with_suffix(".binary.json"))}}
            return decoded, reading
        except (OSError, ValueError, UnicodeError) as error:
            audit["error"] = str(error)
            if number < len(self.commands):
                audit["actual_transport"] = self.commands[number]
            if not prefix.with_suffix(".binary.json").exists():
                original.dump_fresh(prefix.with_suffix(".binary.json"), audit)
            raise


def install(checker):
    if digest(checker.__file__) != PINS["selfcheck"]:
        raise ValueError("only the exact frozen selfcheck collector may be adapted")
    checker.ReadOnlyCollector = BinarySafeCollector
    return checker
