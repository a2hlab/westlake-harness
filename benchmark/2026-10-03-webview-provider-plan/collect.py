import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORKSPACES = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WORKSPACES / "westlake-harness"
WESTLAKE = WORKSPACES / "vm-copies/westlake-current"
AOSP = WORKSPACES / "westlake-inputs/aosp-14.0.0_r1-src"
BASE = WORKSPACES / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle"
DONOR = WORKSPACES / "westlake-inputs/webview"
OLD = REPO / "benchmark/2026-10-02-white-m2-webview"
TOOLS = []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        for root, token in [(WORKSPACES, "$WORKSPACES"), (Path.home(), "$HOME")]:
            if value == str(root):
                return token
            value = value.replace(str(root) + "/", token + "/")
        return re.sub(r"/home/[^/\s]+/", "$HISTORICAL_HOME/", value)
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, dict):
        return {name: portable(item) for name, item in value.items()}
    return value


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value), indent=2, ensure_ascii=False) + "\n")


def run(label, command, allowed=(0,)):
    result = subprocess.run([str(item) for item in command], capture_output=True, text=True)
    output = result.stdout + result.stderr
    raw = HERE / ".artifacts" / (label + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(output)
    evidence = HERE / "evidence" / (label + ".txt")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(portable(output))
    TOOLS.append(dict(label=label, command=command, exit_code=result.returncode,
                      raw_sha256=sha(raw), evidence=str(evidence.relative_to(HERE)),
                      evidence_sha256=sha(evidence)))
    if result.returncode not in allowed:
        raise RuntimeError((label, result.returncode))
    return output


def snippet(path, intervals):
    lines = path.read_text(errors="replace").splitlines()
    result = dict(path=path, sha256=sha(path), rows=[dict(line=number, text=lines[number - 1])
        for first, last in intervals for number in range(first, min(last, len(lines)) + 1)])
    for root in [MASTER, WESTLAKE, WORKSPACES / "00.Workspace"]:
        if path.is_relative_to(root):
            result["last_path_commit"] = subprocess.check_output(["git", "-C", str(root), "log", "-1",
                "--format=%H", "--", str(path.relative_to(root))], text=True).strip()
            break
    return result


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    dex = module(OLD / "collect.py", "m2_dex")
    targets = {
        "Ladapter/activity/B7BindFixes;": ["apply", "loadWestlakeNativeLibs"],
        "Ladapter/activity/J10eWebView;": ["install"],
        "Ladapter/activity/J10gWebExtras;": ["install"],
        "Ladapter/activity/WebViewProviderFix;": ["install"],
        "Ladapter/core/WestlakeWebViewInstall;": ["install", "isAvailable", "linkRuntime", "getSideloadedWebViewPackageInfo"],
        "Ladapter/core/WebViewPackageFallback;": ["install"],
        "Ladapter/core/WebViewPackageFallback$1;": ["invoke"],
        "Ladapter/core/WebViewUpdateServiceAdapter;": ["isMultiProcessEnabled", "waitForAndGetProvider"],
        "Ladapter/packagemanager/PackageManagerAdapter;": ["getSideloadedWebViewPackageInfo"],
    }
    runtime = BASE / "framework/oh-adapter-runtime.jar"
    boot = BASE / "native/payload/android/framework/framework.jar"
    save("evidence/runtime-dex.json", dex.dex_scan(runtime, targets))
    save("evidence/boot-dex.json", dex.dex_scan(boot, {
        "Landroid/webkit/WebViewFactory;": ["getProvider", "getProviderClass", "getWebViewProviderClass"],
        "Landroid/webkit/WebViewDelegate;": ["isMultiProcessEnabled"],
        "Landroid/webkit/WebView;": ["ensureProviderCreated"],
    }))
    provider = DONOR / "webview-t.apk"
    save("evidence/provider-dex.json", dex.dex_scan(provider, {
        "Lcom/android/webview/chromium/WebViewChromiumFactoryProviderForT;": ["create", "<init>"],
        "Lcom/android/webview/chromium/WebViewChromiumFactoryProviderCompat;": ["create", "<init>", "createWebView"],
    }))
    selected = json.loads((OLD / "results.json").read_text())
    rows = []
    for row in selected["rows"]:
        apk = Path(row["apk"]["apk"].replace("$WORKSPACES", str(WORKSPACES)))
        assert sha(apk) == row["apk"]["apk_sha256"]
        with zipfile.ZipFile(apk) as archive:
            assets = [name for name in archive.namelist() if name.startswith("assets/")
                      and re.search(r"\.(html?|js|css|json)$", name)]
            config = [dict(member=name, sha256=hashlib.sha256(archive.read(name)).hexdigest(),
                           text=archive.read(name).decode(errors="replace"))
                      for name in assets if name.endswith("capacitor.config.json")]
            html = []
            for name in assets:
                if not name.endswith(".html"):
                    continue
                text = archive.read(name).decode(errors="replace")
                html.append(dict(member=name, sha256=hashlib.sha256(archive.read(name)).hexdigest(),
                                 bytes=len(archive.read(name)), text=text if len(text) < 18000 else text[:3000]))
        rows.append(dict(key=row["key"], apk=row["apk"], app_pids=row["app_pids"],
                         signed=row["signed"], run=row["run"], pins=row["pins"],
                         events=row["events"], maps=row["maps"], assets=assets, config=config, html=html))
    save("evidence/six-keys.json", dict(previous_results_sha256=sha(OLD / "results.json"), rows=rows))
    inputs = []
    for path in [provider, DONOR / "aosp-android-13.0.0_r80-arm64-webview.apk"]:
        with zipfile.ZipFile(path) as archive:
            members = [dict(member=item.filename, bytes=item.file_size, compressed=item.compress_size,
                            compression=item.compress_type,
                            sha256=hashlib.sha256(archive.read(item)).hexdigest())
                       for item in archive.infolist() if item.filename.startswith(("lib/", "assets/"))]
        inputs.append(dict(path=path, sha256=sha(path), bytes=path.stat().st_size, members=members))
    save("evidence/provider-inputs.json", inputs)
    original_library = HERE / ".artifacts/apk-libwebviewchromium.so"
    original_library.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(provider) as archive:
        original_library.write_bytes(archive.read("lib/arm64-v8a/libwebviewchromium.so"))
    for option, label in [("-d", "dynamic"), ("-V", "versions")]:
        run("apk-chromium-" + label, ["llvm-readelf", option, original_library])
    build_tools = Path.home() / "Library/Android/sdk/build-tools/37.0.0"
    run("provider-manifest", [build_tools / "aapt2", "dump", "xmltree", "--file", "AndroidManifest.xml", provider])
    run("provider-badging", [build_tools / "aapt2", "dump", "badging", provider])
    run("provider-signature", [build_tools / "apksigner", "verify", "--verbose", "--print-certs", provider], (0, 1))
    library = DONOR / "webview-t-lib/libwebviewchromium.so"
    for option, label in [("-d", "dynamic"), ("-V", "versions"), ("--dyn-syms", "symbols")]:
        run("chromium-" + label, ["llvm-readelf", option, library])
    reader = module(REPO / "benchmark/2026-10-02-u13-native-load-3/collect.py", "load3_elf")
    save("evidence/original-chromium-elf.json", reader.elf(original_library))
    exports = {}
    providers = []
    factory = WORKSPACES / "westlake-inputs/oh61-link-inputs/system-lib64"
    provider_paths = set((BASE / "native/payload").rglob("*.so")) | {
        path for path in factory.glob("*") if path.is_file() and ".so" in path.name}
    for path in sorted(provider_paths):
        facts = reader.elf(path)
        providers.append(dict(path=path, sha256=sha(path), needed=facts["needed"]))
        for entry in facts["exports"]:
            exports.setdefault(entry["name"], []).append(portable(path))
    facts = reader.elf(library)
    save("evidence/closure.json", dict(consumer_path=library, consumer_sha256=sha(library),
        needed=facts["needed"], providers=providers,
        strong_undefined=[dict(symbol=entry["name"], version=entry["version"],
                               inventory_export_paths=exports.get(entry["name"], []))
                          for entry in facts["strong_undefined"]],
        caveat="Union export inventory only; no version, namespace, owner, JNI or successful relocation proof"))
    for name in ["libwebviewchromium.so", "libwestlake_html_compat.so", "libjnigraphics.so"]:
        run("whois-" + name, ["python3", MASTER / "scripts/lab/deployed_whois.py", "--generation", BASE, name])
    run("artifact-identity", ["python3", MASTER / "scripts/lab/artifact_identity.py", runtime, boot,
        BASE / "native/payload/android/lib64/liboh_android_runtime.so", "--expected",
        MASTER / "benchmark/2026-10-02-u10-1-t8-rerun/expected-run.json"])
    sources = [
        (MASTER / "benchmark/blockers-ledger.json", [(75, 98)]),
        (MASTER / "harness/westlake_gap/gapmap.py", [(658, 685), (833, 852)]),
        (MASTER / "benchmark/2026-09-28-batch16-20-blind/README.md", [(1, 80)]),
        (MASTER / "benchmark/2026-09-26-batch11-15-blind/README.md", [(1, 70)]),
        (WESTLAKE / "historical/workspace/openharmony/docs/engine/OH-FIVE-GAP-REPAIR-2026-09-04.md", [(1, 110), (163, 179)]),
        (WESTLAKE / "framework/activity/jni/activity_task_manager_adapter.cpp", [(419, 570), (697, 723)]),
        (WESTLAKE / "framework/core/java/WebViewUpdateServiceAdapter.java", [(25, 100)]),
        (WESTLAKE / "framework/package-manager/java/PackageManagerAdapter.java", [(54, 175)]),
        (WESTLAKE / "framework/window/java/OhWebViewBridge.java", [(1, 25)]),
        (WESTLAKE / "framework/android-runtime/src/oh_webview_startup_order.cpp", [(1, 210)]),
        (WESTLAKE / "framework/webview-shim/smali/com/android/webview/chromium/WebViewChromiumFactoryProviderCompat.smali", [(1, 80)]),
        (AOSP / "frameworks/base/core/java/android/webkit/WebViewFactory.java", [(50, 57), (315, 392), (438, 530)]),
        (AOSP / "frameworks/base/core/java/android/webkit/WebViewDelegate.java", [(113, 128), (204, 216)]),
        (AOSP / "frameworks/base/core/java/android/webkit/WebView.java", [(2595, 2625)]),
        (WORKSPACES / "00.Workspace/src/adapter/aosp_patches/libs/hwui/patches/WebViewFunctorManager.cpp.patch", [(1, 100)]),
    ]
    save("evidence/source-lines.json", dict(files=[snippet(path, intervals) for path, intervals in sources]))
    save("evidence/shim-source-lines.json", snippet(
        WESTLAKE / "framework/webview-shim/webview_bionic_shim.c",
        [(148, 214), (635, 650), (707, 715), (757, 773), (898, 964), (1430, 1473), (1657, 1680)]))
    save("evidence/hwui-build-source.json", snippet(WESTLAKE /
        "historical/workspace/bridge-build-arm64/gap-repair-20260904/build_hwui_probe.py", [(1, 40)]))
    ledger = MASTER / "benchmark/loop-outcomes.json"
    save("evidence/upstream-loop-outcomes.json", dict(path=ledger, sha256=sha(ledger), data=json.loads(ledger.read_text())))
    historical = WESTLAKE / "historical/workspace/bridge-build-arm64/gap-repair-20260904"
    save("evidence/lookup-coverage.json", dict(
        historical_root=historical,
        historical_manifest_results_and_image_files=[portable(path) for path in historical.glob("**/*")
            if path.is_file() and (path.name == "manifest.json" or path.name.endswith(("results.json", ".jpeg", "child.log")))],
        local_real_work_checkout_names=[portable(path) for root in [WORKSPACES, WORKSPACES / "00.Workspace/code", Path.home() / "a2hlab"]
            if root.is_dir() for path in root.glob("*") if path.is_dir() and "real-work" in path.name.lower()],
        scope="Local named-directory search only; no claim about inaccessible remote trees or arbitrary nested checkouts"))
    run("upstream-ledger-at-merge", ["git", "-C", MASTER, "show", "b355ed4ce3:benchmark/blockers-ledger.json"])
    run("donor-source-history", ["git", "-C", WESTLAKE, "log", "-8", "--format=%H %s", "--",
        "framework/activity/jni/activity_task_manager_adapter.cpp", "framework/core/java/WebViewUpdateServiceAdapter.java",
        "historical/workspace/openharmony/docs/engine/OH-FIVE-GAP-REPAIR-2026-09-04.md"])
    run("donor-shim-history", ["git", "-C", WESTLAKE, "log", "-8", "--format=%H %s", "--", "framework/webview-shim"])
    save("evidence/tool-runs.json", TOOLS)
    print("COLLECT PASS: pinned six keys, exact DEX, local donor inputs and bundle symbol inventory; no runtime probe")


if __name__ == "__main__":
    main()
