#!/usr/bin/env python3
"""Read existing screenshot receipts; compare a fixed inner-video RGB region."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", type=Path, required=True)
    parser.add_argument("--group", action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    window = args.window.resolve()
    ffmpeg = Path(shutil.which("ffmpeg")).resolve()
    result = {
        "roi": [178, 335, 1020, 880],
        "method": "format=rgb24,crop=842:545:178:335; raw RGB24 comparison",
        "decoder_sha256": hashlib.sha256(ffmpeg.read_bytes()).hexdigest(),
        "groups": {},
        "device_calls": 0,
        "visual_review_required": True,
    }
    for group in args.group:
        folder = (window / group).resolve()
        folder.relative_to(window)
        rows, first = [], None
        for offset in (0, 5, 10, 20):
            receipt = folder / f"{offset}.stdout"
            data = json.loads(receipt.read_text().splitlines()[0])
            # Only the captured directory name is reused: restored archives
            # need not have the original author's absolute workspace path.
            image = window / Path(data["path"]).parent.name / Path(data["path"]).name
            full_sha = hashlib.sha256(image.read_bytes()).hexdigest()
            if full_sha != data["sha256"]:
                raise ValueError(f"screenshot receipt mismatch: {image.name}")
            command = [
                str(ffmpeg), "-v", "error", "-i", str(image),
                "-vf", result["method"].split(";")[0],
                "-pix_fmt", "rgb24", "-f", "rawvideo", "-",
            ]
            run = subprocess.run(command, capture_output=True, check=True)
            pixels = run.stdout
            if len(pixels) != 842 * 545 * 3:
                raise ValueError("unexpected decoded ROI byte count")
            if first is None:
                first = pixels
            differences = [abs(a - b) for a, b in zip(first, pixels)]
            rows.append({
                "offset": offset,
                "path": image.relative_to(window).as_posix(),
                "full_sha256": full_sha,
                "pixel_sha256": hashlib.sha256(pixels).hexdigest(),
                "changed_channels_from_first": sum(x != 0 for x in differences),
                "mean_abs_diff_from_first": sum(differences) / len(differences),
                "minimum": min(pixels),
                "maximum": max(pixels),
                "captured_at": data["captured_at"],
                "decoder_rc": run.returncode,
                "decoder_stderr_sha256": hashlib.sha256(run.stderr).hexdigest(),
            })
        result["groups"][group] = rows
    with args.out.open("x") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps({"groups": list(result["groups"]), "device_calls": 0}))


if __name__ == "__main__":
    main()
