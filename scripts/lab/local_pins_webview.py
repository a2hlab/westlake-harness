"""Re-pin the six device-captured WebView files in parity27-runtime-inputs.lock.json to a local payload.

usage: local_pins_webview.py <lock> <webview input dir>
Each changed entry keeps its original hash under "local_substitution" with the reason; the engine
(libwebviewchromium.so) is reproduced byte-for-byte and therefore left untouched.
"""
import hashlib
import json
import sys
from pathlib import Path

lock_path, payload = Path(sys.argv[1]), Path(sys.argv[2])
text = lock_path.read_text()
lock = json.loads(text)
indent = 1 if text.startswith('{\n "') else 2
reasons = {
    "webview-t.apk": "AOSP android-13.0.0_r80 prebuilt arm64 webview.apk (Chromium 109.0.5414.123) plus westlake "
                     "framework/webview-shim/smali assembled as classes2.dex, re-signed with this workstation's debug key",
    "webview-t-lib/libwebview_bionic_shim.so": "built from westlake source by the manifest package_webview_source.py recipe; "
                                               "includes the self-trapping-library refusal the captured copy predates",
    "webview-t-lib/libandroid.so": "built from westlake source by the manifest package_webview_source.py recipe",
    "webview-t-lib/libjnigraphics.so": "built from westlake source by the manifest package_webview_source.py recipe",
    "webview-t-lib/libwebviewchromium_plat_support.so": "built from westlake source by the manifest package_webview_source.py recipe",
}
changed = 0
for entry in lock["files"]:
    if entry.get("category") != "webview":
        continue
    name = entry["path"].removeprefix("/data/local/tmp/asx/")
    digest = hashlib.sha256((payload / name).read_bytes()).hexdigest()
    if digest == entry["sha256"]:
        print("unchanged", name)
        continue
    original = entry.get("local_substitution", {}).get("original") or {"sha256": entry["sha256"]}
    entry["local_substitution"] = {"reason": reasons[name], "original": original}
    entry["sha256"] = digest
    changed += 1
lock_path.write_text(json.dumps(lock, indent=indent, ensure_ascii=False) + "\n")
print("re-pinned", changed, "WebView files")
