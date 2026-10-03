import json

from prepare import HERE, save, sha


def main():
    binding = json.loads((HERE / "native-pair-binding.json").read_text())
    gates = json.loads((HERE / "native-pair-gates.json").read_text())
    report = json.loads((HERE / "evidence/u16-a3-native-u16-pair-N1.json").read_text())
    findings = report["gates"]["N1"]["findings"]
    shifted = [row for row in findings if row["profile"] == "u13-m1-compat-shim.cpp" and
        row["detail"]["evidence"]["line"] in [421, 1334]]
    added = [row for row in findings if row["profile"] == "u16-flutter-impeller"]
    strings_file = HERE / "evidence/u16-a3-flutter-strings.txt"
    strings = [line for line in strings_file.read_text().splitlines() if line.startswith(("ADDED ", "DROPPED "))]
    if len(shifted) != 2 or len(added) != 4 or len(strings) != 8 or any(line.startswith("DROPPED ") for line in strings):
        raise ValueError("Unexpected native review count; retain fresh reports")
    save("native-pair-review.pending.json", dict(approved=False, execution_enabled=False, rollout_ready=False,
        native_manifest_sha256=binding["native_manifest_sha256"], native_inputs_sha256=binding["native_inputs_sha256"],
        exact_nonbinding_equal=202, shifted_n1=shifted, added_n1=added,
        callset_review=json.loads((HERE / "native-review.pending.json").read_text())["abi_call_diffs"],
        flutter_open_delta=gates["members"]["flutter"]["delta"], flutter_open_delta_sha256=gates["members"]["flutter"]["delta_sha256"],
        strings_raw_rows=strings, strings_evidence=str(strings_file.relative_to(HERE)), strings_evidence_sha256=sha(strings_file),
        instruction_equivalence="Donora53534971f reports34/34 U15 functions preserved including ATrace and only eglGetProcAddress changed vs b1c9; donor proofs hashed in flutter-source-snapshots.json; no local rebuild",
        open_site_resolution="A3 scanner resolves libEGL.so at eglGetProcAddress@0x4ad8; b1c9 historical unknown ADR retained in old evidence, not rewritten",
        registry_delta_applied=False, approvals_applied=False))
    print("PAIR REVIEW pending:202 equal +2 source-line shifts +4 new NOLOAD;8 string additions;3 runtime call-set differences")


if __name__ == "__main__":
    main()
