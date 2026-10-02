import json
from pathlib import Path
import shutil

from audit import RAW, portable, save
from source import HERE, sha


def main():
    root = HERE / ".artifacts/frozen-r1"
    receipt = json.loads((root / "build-receipt.json").read_text())
    store = root / "input-files"
    store.mkdir(exist_ok=True)
    for row in receipt["inputs"]:
        source = Path(row["path"])
        if sha(source) != row["sha256"]:
            raise ValueError("input changed before archival: " + row["path"])
        target = store / row["sha256"]
        if not target.is_file():
            shutil.copyfile(source, target)
        if sha(target) != row["sha256"]:
            raise ValueError("archived input SHA drift")
        row["archived_path"] = portable(str(target))
    evidence = HERE / "evidence"
    evidence.mkdir(exist_ok=True)
    source_files = [HERE / "inputs/host-r3.c", HERE / "inputs/resident-compat.h", HERE / "n11h-owner.h",
                    HERE / "src/candidate-stock-host.c", HERE / "stock-host.patch", HERE / "build.py",
                    HERE / "source.py", HERE / "elf_readonly.py"]
    receipt.update(source_snapshot={str(path.relative_to(HERE)): sha(path) for path in source_files},
                   raw_build_log=portable(str(root / "build.log")), raw_build_log_sha256=sha(root / "build.log"),
                   raw_build_receipt=portable(str(root / "build-receipt.json")), raw_build_receipt_sha256=sha(root / "build-receipt.json"))
    save(evidence / "build-receipt.json", json.loads(portable(json.dumps(receipt))))
    exported = []
    for source in sorted(RAW.iterdir()):
        if not source.is_file() or source.suffix not in {".json", ".txt", ".log"}:
            continue
        target = evidence / source.name
        target.write_text(portable(source.read_text()))
        exported.append(dict(raw=portable(str(source)), raw_sha256=sha(source),
                             public=portable(str(target)), public_sha256=sha(target),
                             transformation="only repository/workspaces prefix tokens; byte-exact raw retained"))
    (evidence / "build.log").write_text(portable((root / "build.log").read_text()))
    save(evidence / "raw-index.json", exported)
    print("ARCHIVE PASS: " + str(len(receipt["inputs"])) + " build inputs content-addressed; toolchain/headers/objects/link inputs + tee log + portable public evidence")


if __name__ == "__main__":
    main()
