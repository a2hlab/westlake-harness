import json
from pathlib import Path
import shutil

from common import HERE, OLD, PRIOR, REPO, SDK, WS, portable, save, sha


def main():
    for name, temporary in [("candidate-build", "ctype-candidate-build"), ("verify", "ctype-verify"),
                            ("prepare", "ctype-prepare-final"), ("audit", "ctype-audit-complete"),
                            ("python-tests", "ctype-python-tests")]:
        source = Path("/tmp") / (temporary + ".log")
        if source.is_file():
            target = HERE / ".artifacts" / (name + ".log")
            shutil.copyfile(source, target)
            (HERE / "evidence" / (name + ".log.txt")).write_text(portable(target.read_text()))
    receipt = json.loads((HERE / "build-receipt.json").read_text())
    archive = HERE / ".artifacts/frozen-b2-objects"
    archive.mkdir(exist_ok=True)
    for row in receipt["inputs"]:
        path = Path(row["path"].replace("$REPO", str(REPO)).replace("$WORKSPACES", str(WS)).replace("$OHOS_SDK", str(SDK)))
        if path.suffix == ".o":
            if sha(path) != row["sha256"]:
                raise ValueError("frozen object drift")
            shutil.copyfile(path, archive / (row["sha256"] + ".o"))
    prior_receipt = HERE / "inputs/b2-build-receipt.json"
    shutil.copyfile(PRIOR / "build-receipt.json", prior_receipt)
    save("toolchain.json", dict(tools=[dict(path=SDK / "llvm/bin" / name, sha256=sha(SDK / "llvm/bin" / name))
        for name in ["clang", "ld.lld", "llvm-readelf", "llvm-objdump"]], prior_receipt_sha256=sha(prior_receipt),
        compiler_verified_against_b2=True, execution_enabled=False))
    entries = [dict(path=str(path.relative_to(HERE / ".artifacts")), sha256=sha(path), bytes=path.stat().st_size) for path in sorted((HERE / ".artifacts").rglob("*"))
               if path.is_file() and "bundle-v2-n1-error" not in path.parts]
    save("persistent-inventory.json", dict(root=HERE / ".artifacts", items=entries, execution_enabled=False,
         rejected_scratch="bundle-v2-n1-error retained only as an unadmitted source-profile error; not candidate or baseline"))
    composition = json.loads((HERE / "composition.json").read_text())
    validation = json.loads((HERE / "validation.json").read_text())
    gates = json.loads((HERE / "namespace-gates.json").read_text())
    save("results.json", dict(state="U13_COMPAT_V2_OFFLINE_DISABLED", baseline_sha256=OLD,
         candidate_sha256=composition["compat_after"], bundle_sha256=composition["bundle_sha256"],
         native_manifest_sha256=composition["native_manifest_sha256"], baseline_reproduced=True, repeated_same_bytes=True,
         abi_added=validation["abi_added"], calls_changed=0, consumers=219, consumer_breaks=0,
         original_table_all_bytes_equal=True, namespace_gates=gates, raw_strings_exit_code=1,
         production_dry_runs="not run for this new manifest; must be freshly executed before any window",
         predicted_first_fatal_moves=dict(proven=0, conditional=1), predicted_t20="unknown",
         host_candidate_included=False, execution_enabled=False, rollout_ready=False))
    save("documentation.json", dict(layout_row="| **2026-10-03-u13-compat-ctype** | Original AOSP14 legacy ctype pointer, exact b2 reproduction, one export,219 consumers and disabled atomic U13 rebind |",
         digest_line="U13 _ctype_(2026-10-03,cx-bms):McD U12 libz已过，新首墙30959 _ctype_@LIBC；原表8fc63/位定义e187复用，必须pointer8→LOCAL257而非裸数组。b2精确复现/b8a87两遍同字节、ABI+1/calls0/219断0；readelf将二进制表渲染成1条ADDED非路径，raw1待审。新c60d草稿仅双compat别名，hostc288不进；bridge原已有_ctype仍失败，库存0缺不证明scope/点亮，预测条件1实证0。"))
    print("FINAL artifacts persist; aliases atomic; candidate disabled; approvals still null")


if __name__ == "__main__":
    main()
