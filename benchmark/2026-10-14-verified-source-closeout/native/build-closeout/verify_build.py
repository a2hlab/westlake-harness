import argparse
import base64
import hashlib
import json
import tarfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(archive_path):
    index = json.loads((HERE / "evidence-index.json").read_text())
    archive_raw = archive_path.read_bytes()
    require(sha256(archive_raw) == index["archive"]["sha256"], "archive SHA mismatch")
    require(len(archive_raw) == index["archive"]["bytes"], "archive size mismatch")
    members = {}
    with tarfile.open(archive_path, "r:gz") as bundle:
        for member in bundle.getmembers():
            require(member.name not in members, "duplicate archive member")
            require(member.isfile() or member.isdir(), "non-regular archive member")
            if member.isfile():
                require(member.name in index["members"], "unexpected archive file")
                raw = bundle.extractfile(member).read()
                expected = index["members"][member.name]
                require(sha256(raw) == expected["sha256"], "member SHA mismatch: " + member.name)
                require(len(raw) == expected["bytes"], "member size mismatch: " + member.name)
                members[member.name] = raw
    require(set(members) == set(index["members"]), "incomplete archive")
    for row in index["public_copies"]:
        copied = (HERE / row["path"]).read_bytes()
        if "raw_base64" in row:
            require(sha256(copied) == row["text_copy_sha256"], "display copy SHA mismatch")
            require(len(copied) == row["text_copy_bytes"], "display copy size mismatch")
            copied = base64.b64decode((HERE / row["raw_base64"]).read_bytes().strip(), validate=True)
        require(sha256(copied) == row["sha256"], "public evidence SHA mismatch")
        require(len(copied) == row["bytes"], "public evidence size mismatch")
        if "member" in row:
            require(copied == members[row["member"]], "public/archive copy mismatch")
    receipt = json.loads(members["provider/result.json"])
    require((HERE / "evidence/outer-run.rc.raw.b64").read_bytes().strip() == b"MA==", "runner rc mismatch")
    require((HERE / "evidence/outer-run.stdout").read_bytes() == members["restore.stdout"] + members["provider.stdout"], "runner stdout mismatch")
    require((HERE / "evidence/outer-run.stderr.txt").read_bytes() == b"", "unexpected runner stderr")
    restore = json.loads(members["generation/restore-receipt.json"])
    require(restore["exit_code"] == 0, "restore failed")
    require(restore["duplicate_members_verified"] == 2648, "duplicate audit count mismatch")
    require(restore["external_files_overwritten"] == 0, "external overwrite")
    require(restore["external_new_targets"] == 0, "unexpected external target")
    require(restore["whole_generation_complete"] is False, "whole-generation overclaim")
    require(receipt["historical_production_proven"] is False, "historical-production overclaim")
    require(receipt["execution_requested"] is True, "preview is not execution")
    require(receipt["exit_code"] == 0, "provider failed")
    require(receipt["status"] == "NEW_BUILD_BYTE_EQUAL", "wrong build status")
    require(receipt["byte_equal"] is True, "unequal output")
    require([len(argv) for argv in receipt["argv"]] == [51, 54], "argv count mismatch")
    require(len(receipt["steps"]) == 2, "compile/link steps missing")
    for step_number, step in enumerate(receipt["steps"]):
        require(step["exit_code"] == 0, "compile/link failure")
        for stream in ("stdout", "stderr"):
            raw = members["provider/step-" + str(step_number) + "." + stream]
            require(sha256(raw) == step[stream + "_sha256"], "compiler stream mismatch")
    output = members["provider/libwestlake_android_runtime_provider.so"]
    require(sha256(output) == receipt["output_sha256"] == receipt["frozen_sha256"], "output mismatch")
    require(len(output) == receipt["bytes"] == 504984, "output size mismatch")
    for name in ("restore", "provider"):
        require(members[name + ".rc"].strip() == b"0", "raw step rc mismatch")
    require(members["restore.stdout"] == members["generation/restore-receipt.json"], "restore raw mismatch")
    require(members["provider.stdout"] == members["provider/result.json"], "provider raw mismatch")
    checked = 0
    for frozen in index["unchanged_freezes"]:
        path = REPO / frozen["path"]
        raw = path.read_bytes()
        require(sha256(raw) == frozen["sha256"], "frozen manifest changed")
        for row in json.loads(raw)["files"]:
            actual = (REPO / row["path"]).read_bytes()
            require(sha256(actual) == row["sha256"], "frozen member changed: " + row["path"])
            require(len(actual) == row["bytes"], "frozen member size changed")
            checked += 1
    return {"status": "VERIFIED_NEW_EXACT_BUILD", "archive_files_verified": len(members),
            "unchanged_frozen_members_verified": checked, "restore_rc": 0,
            "compile_rc": 0, "link_rc": 0, "runner_rc": 0,
            "output_sha256": sha256(output), "output_bytes": len(output),
            "historical_production_proven": False, "device_access": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.archive)
    except (OSError, ValueError, KeyError, tarfile.TarError) as error:
        print(json.dumps({"status": "REJECT", "reason": str(error)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
