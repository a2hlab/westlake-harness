import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
SERIAL = "61b0657200000000000000000324012c"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expand(value, workspaces):
    return Path(value.replace("$WORKSPACES", str(workspaces))).resolve()


def collect(plan_path, runner, index, workspaces):
    plan = json.loads(plan_path.read_text())
    if plan.get("serial") != SERIAL:
        raise ValueError("REFUSE: plan is not the authorized 61b serial")
    sources = [expand(source["path"], workspaces) for source in index["sources"]]
    for source, path in zip(index["sources"], sources):
        if digest(path) != source["sha256"]:
            raise ValueError("REFUSE: reference/tool SHA drift: " + str(path))
    prior = json.loads(sources[1].read_text())["rows"]
    references = {row["key"]: row for row in index["rows"]}
    packets = []
    planned = set()
    for shard in plan["shards"]:
        name = shard["name"]
        if Path(name).name != name:
            raise ValueError("REFUSE: noncanonical shard name")
        keys = expand(shard["keys_file"], workspaces).read_text().splitlines()
        for key in filter(None, (line.strip() for line in keys)):
            if key not in references or key in planned:
                raise ValueError("REFUSE: unknown/duplicate plan key: " + key)
            planned.add(key)
            reference = references[key]
            old = prior[reference["r4_r6_row"]]
            for record in sorted((runner / name).glob("*/" + SERIAL + "/" + key + "/record.json")):
                data = json.loads(record.read_text())
                if not data.get("finished_at"):
                    continue
                if data.get("key") != key or data.get("package") != reference["package"] or data.get("serial", SERIAL) != SERIAL:
                    raise ValueError("REFUSE: wrong record object: " + str(record))
                if data.get("apk_sha256") != reference["apk_sha256"]:
                    raise ValueError("REFUSE: APK identity drift: " + key)
                images = []
                for shot in data.get("screenshots", []):
                    if not shot.get("captured"):
                        continue
                    path = expand(shot["path"], workspaces)
                    if path.parent != record.parent or digest(path) != shot["sha256"]:
                        raise ValueError("REFUSE: screenshot path/hash mismatch")
                    images.append(dict(shot, path=str(path), personally_viewed=False))
                facts = record.parent.parent / "facts.txt"
                fatal = subprocess.run(["python3", str(sources[3]), str(record.parent)], capture_output=True, text=True)
                parser = json.loads(fatal.stdout) if fatal.stdout.strip() else None
                packets.append({"key": key, "record": {"path": str(record), "sha256": digest(record)},
                    "record_data": data, "actual_images": images, "facts_path": str(facts),
                    "facts_sha256": digest(facts), "facts_verbatim": facts.read_text(),
                    "first_fatal": {"exit": fatal.returncode, "result": parser, "stderr": fatal.stderr},
                    "signed": reference["signed"], "r4_comparison": old["r4_comparison"],
                    "r6_images": old["shots"], "r6_visual": old["independent_visual"],
                    "r6_visual_note": old["visual_note"], "r6_compare_index": str(sources[0]),
                    "v1_current20_reference": reference.get("v1_current20_reference"),
                    "prior_content_disposition": index.get("prior_content_disposition"),
                    "content_comparison_required": True, "visual_verdict": "PENDING_IMAGE_REVIEW",
                    "human_signoff": False, "device_operations": 0,
                    "plan": {"path": str(plan_path), "sha256": digest(plan_path)}})
    return packets


def main():
    parser = argparse.ArgumentParser(description="File-only 61b packet adapter; no UI verdict or device calls.")
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    workspaces = Path(os.environ.get("WORKSPACES", HERE.parents[5]))
    output = args.out.resolve()
    if not output.is_relative_to(HERE):
        raise ValueError("REFUSE: output must remain in this private observer directory")
    index = json.loads((HERE / "reference-index.json").read_text())
    packets = collect(args.plan.resolve(), args.runner.resolve(), index, workspaces)
    output.mkdir(parents=True, exist_ok=True)
    for packet in packets:
        name = packet["key"] + "-" + packet["record"]["sha256"][:16] + ".json"
        body = (json.dumps(packet, indent=2, ensure_ascii=False) + "\n").replace(str(workspaces), "$WORKSPACES")
        path = output / name
        if path.exists():
            if path.read_text() != body:
                raise ValueError("REFUSE: existing packet differs; retain both attempts")
        else:
            with path.open("x") as stream:
                stream.write(body)
    print(json.dumps({"completed_records": len(packets), "out": str(output), "device_operations": 0, "human_signoff": False}))


if __name__ == "__main__":
    main()
