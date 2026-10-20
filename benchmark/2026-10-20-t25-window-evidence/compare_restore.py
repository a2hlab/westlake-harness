#!/usr/bin/env python3
"""Local-only T21-compatible snapshot/supplement comparison; never calls devices."""
import argparse
import hashlib
import json
import re
from pathlib import Path

FIELDS = (
    "plan_sha256", "collection_sha256", "bind_targets", "init_configs",
    "labels", "sha", "params", "selinux_enforce",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def load(path):
    data = path.read_bytes()
    return json.loads(data), {"sha256": sha(data), "bytes": len(data)}


def differences(a, b, path="$"):
    if type(a) is not type(b):
        return [path + ":type"]
    if isinstance(a, dict):
        result = []
        for key in sorted(set(a) | set(b)):
            sub = path + "/" + str(key)
            if key not in a or key not in b:
                result.append(sub + ":missing")
            else:
                result.extend(differences(a[key], b[key], sub))
        return result
    if isinstance(a, list):
        result = [path + ":length"] if len(a) != len(b) else []
        for i, (x, y) in enumerate(zip(a, b)):
            result.extend(differences(x, y, path + "/" + str(i)))
        return result
    return [] if a == b else [path]


def snapshot_pair(before, after, before_boot, after_boot):
    for label, obj, boot in (("before", before, before_boot), ("after", after, after_boot)):
        need(obj.get("complete") is True and obj.get("collection_complete") is True,
             label + " snapshot incomplete")
        need(obj.get("boot_id") == boot, label + " snapshot boot")
        need(obj.get("plan_target_count") == 518, label + " snapshot target count")
        need(isinstance(obj.get("labels"), (dict, list)) and len(obj["labels"]) == 812,
             label + " snapshot label count")
        need(all(k in obj for k in FIELDS), label + " snapshot missing compared field")
    delta = {k: differences(before[k], after[k], "$/" + k) for k in FIELDS}
    return {"fields_equal": {k: not v for k, v in delta.items()},
            "difference_paths": {k: v for k, v in delta.items() if v},
            "all_equal": not any(delta.values()), "targets": 518, "labels": 812}


def supplement(directory, expected_boot):
    obj, pin = load(directory / "result.json")
    need(obj.get("status") == "SUPPLEMENT_BYTES_COMPLETE" and obj.get("rc") == 0,
         "supplement incomplete or nonzero")
    need(obj.get("targets") == 26 and obj.get("boot") == expected_boot, "supplement count/boot")
    need(set(obj.get("raw", {})) == {"stdout.raw", "stderr.raw"}, "supplement raw index")
    for name, expected in obj["raw"].items():
        data = (directory / name).read_bytes()
        need(len(data) == expected["bytes"] and sha(data) == expected["sha256"],
             "supplement raw SHA/size mismatch: " + name)
    data = (directory / "stdout.raw").read_bytes()
    head, body = data.split(b"\n", 1)
    need(head == b"T16_SUPPLEMENT_BOOT " + expected_boot.encode(), "supplement boot header")
    need(body.endswith(b"T16_SUPPLEMENT_COMPLETE\n"), "supplement completion marker")
    ids = re.findall(rb"^T16_TARGET ([0-9]+) ", body, re.M)
    need(ids == [str(i).encode() for i in range(26)], "supplement target sequence")
    return body, pin


def compare(before, after, before_supp, after_supp, before_boot, after_boot):
    result = {"status": "PENDING", "device_calls": 0,
              "before_boot": before_boot, "after_boot": after_boot}
    paths = {"before_snapshot": before, "after_snapshot": after,
             "before_supplement": before_supp / "result.json",
             "after_supplement": after_supp / "result.json"}
    missing = [key for key, path in paths.items() if not path.is_file()]
    if missing:
        result["missing"] = missing
        return result
    try:
        a, ap = load(before)
        b, bp = load(after)
        result["snapshots"] = snapshot_pair(a, b, before_boot, after_boot)
        x, xp = supplement(before_supp, before_boot)
        y, yp = supplement(after_supp, after_boot)
        result["supplement"] = {
            "targets": 26, "equal_except_boot_header": x == y,
            "before_body_sha256": sha(x), "after_body_sha256": sha(y),
        }
        result["input_receipts"] = dict(zip(paths, (ap, bp, xp, yp)))
        result["status"] = "EQUAL" if result["snapshots"]["all_equal"] and x == y else "DIFFERENT"
    except (ValueError, KeyError, TypeError, OSError) as error:
        result["status"] = "INVALID_OR_INCOMPLETE"
        result["error"] = str(error).replace(str(Path.home()), "$HOME")
    result["scope"] = "Snapshot/supplement only; not UI, audio, playback or complete window acceptance"
    return result


def main():
    parser = argparse.ArgumentParser()
    for name in ("before", "after", "before-supp", "after-supp"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("before-boot", "after-boot"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = compare(args.before, args.after, args.before_supp, args.after_supp,
                     args.before_boot, args.after_boot)
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        # Explicit fresh output only: never rewrite an earlier pending/failure receipt.
        with args.out.open("x") as stream:
            stream.write(text)
    print(text, end="")
    return 0 if result["status"] == "EQUAL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
