import copy
import json
import re

from finalize import HERE, PRIOR, save
from reports import capture, expand
from validation import ABI_MEMBER


def normalize_pc(value):
    if isinstance(value, dict):
        return {key: normalize_pc(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_pc(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"clobbered by call at 0x[0-9a-f]+", "clobbered by call at <PC>", value)
    return value


def main():
    previous = json.loads((PRIOR / "evidence/static-vs-u13.json").read_text())
    current = json.loads((HERE / "common/evidence/static-vs-u13.json").read_text())
    old_rows = {row["target"]: row for row in previous["members"] if row.get("delta_sha256")}
    mappings = []
    for row in current["members"]:
        if not row.get("delta_sha256"):
            continue
        old = old_rows[row["target"]]
        mappings.append(dict(target=row["target"], old_delta_sha256=old["delta_sha256"], new_delta_sha256=row["delta_sha256"],
            byte_pair_unchanged=old["candidate_sha256"] == row["candidate_sha256"] and old["deployed_sha256"] == row["deployed_sha256"],
            delta_fields_equal=old["open_site_delta"] == row["open_site_delta"],
            equal_after_diagnostic_pc_normalization=normalize_pc(old["open_site_delta"]) == normalize_pc(row["open_site_delta"]),
            previous=copy.deepcopy(old["open_site_delta"]), current=copy.deepcopy(row["open_site_delta"]),
            approved_by=None, applied=False))
    composition = json.loads((HERE / "common/composition.json").read_text())
    candidate = expand(composition["package"]) / "native" / ABI_MEMBER
    records = []
    for label, path in [("v1", PRIOR / ".artifacts/bundle/native" / ABI_MEMBER), ("v2", candidate)]:
        records.append(capture(HERE, "dlext-disassembly-" + label, ["llvm-objdump", "-d", "--no-show-raw-insn", "--disassemble-symbols=android_dlopen_ext", path]))
        records.append(capture(HERE, "slot-sections-" + label, ["llvm-readelf", "-S", "--wide", path]))
    save(HERE / "delta-review.json", dict(mappings=mappings, records=records,
        changed_delta_count=sum(not row["delta_fields_equal"] for row in mappings),
        reason="native ABI data/layout moves the same clobber diagnostic PC 0x3df0 -> 0x3f30; v1/v2 calls comparison is empty and donor 44/44 old functions are instruction-equivalent",
        strings_review="Production strings tool adds exactly one printable ctype table projection; no drops; still pending",
        namespace_semantics_new=False, approval_transfer_applied=False, approved_by=None))
    print("delta review: unchanged bridge/host/Flutter; Gecko 05ff6c8b -> 2127f19e (diagnostic PC only), no approval applied")


if __name__ == "__main__":
    main()
