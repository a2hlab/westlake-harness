"""Capture operand context for every retained modern lifecycle launch site."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

import collect


def capture(rows, input_root, mount, dexdump):
    output = []
    for row in rows:
        sites = [site for launcher in row["launchers"] for site in launcher["analysis"]["starts"] if site["kind"] == "activity-result-launch"]
        if not sites:
            continue
        apk = collect.physical(input_root, row["key"], mount) / row["apk"]
        if collect.sha(apk.read_bytes()) != row["apk_sha256"]:
            raise ValueError("APK changed before focused pass")
        for dex in sorted({site["dex"] for site in sites}):
            wanted = {number for site in sites if site["dex"] == dex for number in range(site["instruction"]["line"] - 35, site["instruction"]["line"] + 12)}
            with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory() as temporary:
                data = archive.read(dex)
                digest = collect.sha(data)
                if digest != next(item["sha256"] for item in row["dex"] if item["name"] == dex):
                    raise ValueError("DEX changed before focused pass")
                path = Path(temporary) / dex
                path.write_bytes(data)
                process = subprocess.Popen([str(dexdump), "-d", str(path)], stdout=subprocess.PIPE, text=True, errors="replace")
                lines = [dict(line=number, text=line.rstrip()) for number, line in enumerate(process.stdout, 1) if number in wanted]
                process.stdout.close()
                if process.wait():
                    raise ValueError("focused dexdump failed")
            output.append(dict(key=row["key"], apk_sha256=row["apk_sha256"], dex=dex, dex_sha256=digest, lines=lines))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intake", type=Path)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--vm-mount", type=Path, required=True)
    parser.add_argument("--dexdump", type=Path, default=Path.home() / "Library/Android/sdk/build-tools/37.0.0/dexdump")
    args = parser.parse_args()
    result = capture(json.loads(args.intake.read_text())["rows"], args.input_root, args.vm_mount, args.dexdump)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
