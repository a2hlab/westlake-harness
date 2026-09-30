#!/usr/bin/env python3
"""Offline consistency check, not a layout gate or board acceptance."""
import argparse
import json
from pathlib import Path
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "benchmark/2026-09-30-t5-oat-attribution"))
from capture_flags import LIBART_SHA, at_va, read_vm_string
from compare_oat import elf_sections, parse, sha
from check_boot_oat_rb import KV_KEYS, read_kv

ENVIRONMENT = {
    "ART_USE_READ_BARRIER": "read_barrier",
    "ART_DEFAULT_GC_TYPE": "default_gc",
    "ART_USE_GENERATIONAL_CC": "generational_cc",
    "ART_HEAP_POISONING": "heap_poisoning",
    "ART_TEST_DEBUG_GC": "test_debug_gc",
}
R155 = {
    "read_barrier": False,
    "default_gc": "CMS",
    "generational_cc": False,
    "heap_poisoning": False,
    "test_debug_gc": False,
    "native_debug_build": False,
}
ANCHORS = {
    0x461bb8: "20270037",
    0x76e5a4: "48008052",
    0x76e5ac: "1f4000f8",
    0x76e5b4: "1f0c00b9",
    0x76e5b8: "080000b9",
    0x68e364: "fd7bbfa9210040b9fd030091c100003497ffff971f0000f1e0079f1afd7bc1a8c0035fd620008052fd7bc1a8c0035fd6",
    0x810f60: "204862b8c0035fd6",
    0x810f68: "000040b9c0035fd6",
}
VALUES = {"default_gc": {"CMS", "CMC", "CC", "SS"}}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def value_of(flag, value):
    if flag in VALUES:
        if not isinstance(value, str) or value not in VALUES[flag]:
            raise ValueError(f"invalid {flag}: {value!r}")
        return value
    if type(value) is bool:
        return value
    if isinstance(value, str) and value in {"true", "false"}:
        return value == "true"
    raise ValueError(f"invalid boolean {flag}: {value!r}")


def native_flags(data):
    sections = elf_sections(data)
    if sha(data) != LIBART_SHA:
        return {}, []
    anchors = []
    for address, expected_hex in ANCHORS.items():
        expected = bytes.fromhex(expected_hex)
        offset, actual = at_va(data, sections, address, len(expected))
        if actual != expected:
            raise ValueError(f"R155 predicate differs at {address:#x}")
        anchors.append(dict(address=hex(address), file_offset=offset, hex=expected_hex))
    if read_vm_string(data, sections, 0x3db6bc)["value"] != "libart.so":
        raise ValueError("R155 native release predicate differs")
    return dict(R155), anchors


def build_receipt(path):
    if path is None or not path.is_file():
        return {}, {}, None, None
    raw = path.read_bytes()
    body = raw.decode("utf-8")
    blocks = re.findall(r"^```t4b-build-json[ \t]*\n(.*?)^```[ \t]*$", body, re.M | re.S)
    if len(blocks) > 1:
        raise ValueError("multiple t4b-build-json receipts")
    shell_blocks = re.findall(r"^```(?:sh|bash|shell)[ \t]*\n(.*?)^```[ \t]*$", body, re.M | re.S)
    shell = "\n".join(shell_blocks).replace("\\\n", " ")
    shell_values = {}
    for line in shell.splitlines():
        tokens = shlex.split(line, comments=True)
        if tokens and tokens[0] == "export":
            tokens = tokens[1:]
        for token in tokens:
            assignment = re.fullmatch(r"([A-Za-z_][A-Za-z_0-9]*)=(.*)", token)
            if not assignment:
                break
            variable, raw_value = assignment.groups()
            if variable not in ENVIRONMENT:
                continue
            flag = ENVIRONMENT[variable]
            value = value_of(flag, raw_value)
            if flag in shell_values and shell_values[flag] != value:
                raise ValueError(f"conflicting BUILD.md assignments: {variable}")
            shell_values[flag] = value
    if not blocks:
        return shell_values, {}, sha(raw), "unstructured"
    receipt = json.loads(blocks[0], object_pairs_hook=unique_object)
    if not isinstance(receipt, dict) or type(receipt.get("schema")) is not int or receipt["schema"] != 1:
        raise ValueError("expected build receipt schema 1")
    environment = receipt.get("environment", {})
    artifacts = receipt.get("artifacts", {})
    if not isinstance(environment, dict) or not isinstance(artifacts, dict):
        raise ValueError("environment and artifacts must be objects")
    values = {}
    for variable, flag in ENVIRONMENT.items():
        if variable in environment:
            values[flag] = value_of(flag, environment[variable])
    if "native_debug_build" in receipt:
        values["native_debug_build"] = value_of("native_debug_build", receipt["native_debug_build"])
    for flag, value in shell_values.items():
        if flag in values and values[flag] != value:
            raise ValueError(f"BUILD.md shell and structured receipt differ: {flag}")
    kind = receipt.get("evidence_kind")
    if kind not in {"build_receipt", "synthetic_fixture"}:
        raise ValueError("receipt evidence_kind must be build_receipt or synthetic_fixture")
    return values, artifacts, sha(raw), kind


def check(libart, oat, build=None):
    report = dict(schema=1, scope="T4b only; layout and board acceptance remain separate",
                  inputs={}, observations={}, comparisons=[], mismatches=[], exceptions=[],
                  limitations=["OAT230 does not encode default GC, generational CC or heap poisoning.",
                               "BUILD.md records declared build inputs, not proof of compiler consumption.",
                               "R155 historical TLAB/interpreter/sanitizer/optimization settings remain unknown."])

    def missing(field, evidence):
        report["exceptions"].append(dict(field=field, evidence=evidence, review="outer_required"))

    def compare(field, left_source, left, right_source, right):
        if left is None or right is None:
            return
        row = dict(field=field, left_source=left_source, left=left,
                   right_source=right_source, right=right, equal=left == right)
        report["comparisons"].append(row)
        if not row["equal"]:
            report["mismatches"].append(row)

    native, image, receipt = {}, {}, {}
    try:
        data = libart.read_bytes()
        report["inputs"]["libart_sha256"] = sha(data)
        native, anchors = native_flags(data)
        report["native_anchors"] = anchors
        if not native:
            missing("libart.predicates", "Unknown SHA256: no verified native extractor; never infer defaults")
    except (OSError, ValueError) as error:
        report["mismatches"].append(dict(field="libart.input", error=str(error)))
    try:
        data = oat.read_bytes()
        report["inputs"]["boot_oat_sha256"] = sha(data)
        parsed = parse(data)
        version, kv = read_kv(oat)
        expected_kv = {key: value for key, value in parsed["kv"].items() if key in KV_KEYS}
        if version != "230" or kv != expected_kv or sha(oat.read_bytes()) != report["inputs"]["boot_oat_sha256"]:
            raise ValueError("shared KV reader disagrees with bounded OAT230 validation or input changed")
        report["kv_reader"] = "check_boot_oat_rb.read_kv (cc-wiki 785fdaf1b)"
        report["oat"] = dict(kv=kv, checksum=parsed["header"]["checksum"],
                             instruction_set=parsed["header"]["instruction_set"],
                             instruction_set_features=parsed["header"]["instruction_set_features"])
        for key in ("concurrent-copying", "debuggable", "native-debuggable"):
            if key not in kv:
                missing("oat." + key, "Missing primary OAT boolean key")
            else:
                value = value_of(key, kv[key])
                if key == "concurrent-copying":
                    image["read_barrier"] = value
        report["oat"]["not_encoded"] = ["default_gc", "generational_cc", "heap_poisoning", "native_debug_build"]
    except (OSError, ValueError) as error:
        report["mismatches"].append(dict(field="oat.input", error=str(error)))
    receipt_kind = None
    try:
        receipt, identities, build_sha, receipt_kind = build_receipt(build)
        report["inputs"]["build_md_sha256"] = build_sha
        report["receipt_kind"] = receipt_kind
        if receipt_kind in {None, "unstructured"}:
            missing("build.receipt", "Missing SHA-bound structured historical BUILD.md receipt")
        for field in ("libart_sha256", "boot_oat_sha256"):
            claimed = identities.get(field)
            if claimed is None:
                missing("build." + field, "Missing full artifact SHA256 binding")
            elif not isinstance(claimed, str) or not re.fullmatch(r"[0-9a-f]{64}", claimed):
                report["mismatches"].append(dict(field="build." + field, error="Invalid full SHA256"))
            else:
                compare(field, "artifact", report["inputs"].get(field), "BUILD.md", claimed)
        for flag in R155:
            if flag not in receipt:
                missing("build." + flag, "No explicit value; upstream default is not evidence")
    except (OSError, ValueError) as error:
        report["mismatches"].append(dict(field="build.input", error=str(error)))
    report["observations"] = dict(libart=native, oat=image, build=receipt)
    for flag in R155:
        compare(flag, "libart", native.get(flag), "oat", image.get(flag))
        compare(flag, "libart", native.get(flag), "BUILD.md", receipt.get(flag))
        compare(flag, "oat", image.get(flag), "BUILD.md", receipt.get(flag))
    if receipt.get("test_debug_gc") is True and receipt.get("default_gc") not in {None, "SS"}:
        report["mismatches"].append(dict(field="build.test_debug_gc", error="r1 debug GC forces SS"))
    report["consistency"] = "fail" if report["mismatches"] else ("pass" if native and image else "unknown")
    report["verdict"] = "fail" if report["mismatches"] else ("pending_review" if report["exceptions"] else "pass")
    report["exit_code"] = {"pass": 0, "fail": 2, "pending_review": 3}[report["verdict"]]
    report["deploy_allowed"] = report["verdict"] == "pass" and receipt_kind == "build_receipt"
    report["deploy_allowed_scope"] = "T4b permits only; T4 layout and T6 gates still required"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libart", type=Path, required=True)
    parser.add_argument("--oat", type=Path, required=True)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        inputs = [args.libart, args.oat] + ([args.build] if args.build else [])
        if args.out and (args.out.exists() or args.out.is_symlink() or
                         args.out.resolve() in {path.resolve() for path in inputs}):
            raise ValueError("REFUSE: output exists or aliases an input")
        report = check(args.libart, args.oat, args.build)
        body = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            with args.out.open("x") as output:
                output.write(body)
        print(body, end="")
        return report["exit_code"]
    except (OSError, ValueError) as error:
        print(json.dumps(dict(verdict="fail", deploy_allowed=False, error=str(error), exit_code=2)))
        return 2


if __name__ == "__main__":
    sys.exit(main())
