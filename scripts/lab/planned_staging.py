"""Write a deploy-check report of what this workstation would stage, before any device run.

deploy-check reads staged files only from device reports. With no device run yet, this lists the files
of the board-free build outputs the framework probe stages (plus the WebView payload under its
/data/local/tmp/asx/ names), so deploy-check can answer "would anything the runtime loads be missing".
usage: planned_staging.py <out dir> <report.json>
"""
import hashlib
import json
import sys
from pathlib import Path

out, report = Path(sys.argv[1]), Path(sys.argv[2])
STAGED_DIRS = ["native-runtime", "appspawn", "runtime-extras", "runtime-helpers", "core-java/java", "java-extensions",
               "framework-runtime", "framework-boot", "framework-resources", "runtime-data"]
SKIP_SUFFIXES = (".log", ".json", ".d", ".o", ".txt", ".map", ".classes.jar", ".unrelocated.jar", ".jarjar-output.jar")
files, missing_dirs = {}, []
for d in STAGED_DIRS:
    root = out / d
    if not root.is_dir():
        missing_dirs.append(d)
        continue
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.name.endswith(SKIP_SUFFIXES) and "objects" not in p.parts:
            files[f"{d}/{p.relative_to(root)}"] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
webview = {}
wv = out / "webview-input-source"
for p in sorted(wv.rglob("*")) if wv.is_dir() else []:
    if p.is_file():
        webview[str(p.relative_to(wv))] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
report.write_text(json.dumps({"kind": "planned-staging (no device run)", "files": files,
                              "webview_payload": {"files": webview}, "missing_output_dirs": missing_dirs}, indent=1) + "\n")
print(f"{len(files)} runtime files, {len(webview)} WebView files; output dirs not built: {missing_dirs or 'none'}")
