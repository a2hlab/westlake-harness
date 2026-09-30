"""Read-only donor inventory: source existence is not a U7 repair proof."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
ROOTS = {"Westlake": "vm-copies/westlake-current", "00.Workspace": "00.Workspace", "real-work": "01.OH61AOSP16/real-work", "harness": "westlake-harness"}
SOURCES = [
    ("color-matrix", "Westlake", "framework/mainline-stubs/java/android/graphics/ColorMatrix.java", 13, 47, "Real matrix copy implementation; fd-plus terminal is still MapInfoLayer NPE, not verified causal repair."),
    ("account-binder", "Westlake", "framework/core/java/LocalServiceBinders.java", 138, 157, "Existing IAccountManager fallback; not proof that Nextcloud receives a non-null client manager."),
    ("webview-service", "Westlake", "framework/core/java/WebViewUpdateServiceAdapter.java", 18, 44, "Existing provider service; package feature/UID/provider loading preconditions still need diagnosis."),
    ("theme-mapping", "Westlake", "framework/activity/java/AppSchedulerBridge.java", 1051, 1075, "Existing numeric theme forwarding; named resource fallback does not prove AppCompat attribute resolution."),
    ("opensles-iids-only", "Westlake", "framework/appspawn-x/bionic_compat/src/opensles_android_compat.c", 1, 44, "Extension IIDs only, no slCreateEngine implementation; do not copy as an engine fix."),
    ("abort-message-westlake", "Westlake", "framework/appspawn-x/bionic_compat/src/misc_compat.cpp", 28, 42, "Existing abort-message implementation; consumer namespace visibility is a separate condition."),
    ("abort-message-real", "real-work", "src/adapter/framework/appspawn-x/bionic_compat/src/abort_message_compat.cpp", 33, 60, "Existing implementation with first-message storage; already-provided symbol must be made visible, not duplicated."),
    ("hwui-egl", "real-work", "src/adapter/aosp_patches/libs/hwui/hwui_oh_abi_patch.cpp", 622, 650, "Existing HWUI Android-window conversion boundary used by N8, not the unknown-source 846 bridge."),
    ("egl-reference-00", "00.Workspace", "code/adapter/westlake-piercing/ports/dayu600/gfx-smoke/egl_interposer.cpp", 52, 72, "Old interposer reference; do not replace N8 existing-owner routing with its load fallback."),
    ("zlib-alias", "real-work", "src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/build_route_a_generation_in_container.sh", 581, 597, "SONAME libz.so forwarding dependency to libshared_libz.z.so; domain placement must be checked."),
    ("mediandk-presence", "real-work", "src/adapter/framework/native-compat/mediandk-presence/src/mediandk_presence.c", 1, 12, "Presence-only donor, exports no media API; usable only after exact consumer UND requirements are checked."),
    ("old-window-reference", "real-work", "src/adapter/sources/oh61-v7-b2133b5b/framework/window/jni/oh_anativewindow_shim.cpp", 608, 626, "Old generation reference, not a byte-reproducible source proof for bridge846 and not an accepted race repair."),
    ("bitmap-registration-reference", "00.Workspace", "code/adapter/westlake-piercing/test-fixtures/dayu600-embedded-art-probe/westlake_embedded_art_dlopen_probe.c", 2254, 2268, "Historical ColorSpace registration reference with binary-specific table offsets; not a portable copy or verified U7 musicplayer repair."),
    ("opensles-historical-forward", "real-work", "archive/scripts-history/task68-gles/opensles_iid_shim.c", 1, 28, "Historical IID plus ohimpl dependency recipe. Not a slCreateEngine implementation and copying another provider may violate current singleton rules."),
    ("bitmap-null-fallback", "Westlake", "framework/android-runtime/src/android_graphics_compat_shim.cpp", 46, 64, "Existing ImageDecoder color-space fallback returns null; diagnostic boundary only, not a successful bitmap fix."),
    ("n8-owner-route", "harness", "benchmark/2026-10-01-n7-native/src/host.c", 326, 375, "N7/N8 existing-owner EGL and private zlib routing; unchanged in N8 except root alias removed from package."),
    ("n8-egl-facade", "harness", "benchmark/2026-10-01-n7-native/src/flutter_egl.c", 1, 100, "Typed forwarding facade into existing HWUI/platform owners, retained by N8."),
    ("n8-gnu-strerror", "harness", "benchmark/2026-10-01-n7-native/src/strerror_r_compat.cpp", 1, 70, "N8 GNU spelling compatibility candidate; no demonstrated browser t20 unlock."),
    ("n8-dlopen-ext", "harness", "benchmark/2026-10-01-n7-native/src/dlopen_ext_compat.cpp", 1, 50, "N8 base dlopen forwarding; non-null extinfo semantics are not implemented."),
    ("n8-observed", "harness", "benchmark/2026-10-01-n8-window/README.md", 27, 48, "N8 window moves several native walls but does not light all targets; different JAR baseline, partial acceptance only."),
    ("native-symbol-audit", "harness", "benchmark/2026-10-01-native-symbol-clusters/README.md", 5, 15, "android_set_abort_message exists in supplied bionic DSO; old later prose misclassified benign noise and is not used."),
]
PATTERNS = ["slCreateEngine", "android_set_abort_message", "__gnu_strerror_r", "android_dlopen_ext", "libmediandk", "ColorMatrix", "IAccountManager", "WebViewUpdateServiceAdapter", "MapInfoLayer", "DataSourceModuleProvider", "CountryPreference", "can't create bitmap without a color space"]


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def collect(workspaces):
    repositories = {name: dict(path=relative, commit=git(workspaces / relative, "rev-parse", "HEAD").decode().strip()) for name, relative in ROOTS.items()}
    sources = {}
    for identifier, repository, relative, start, end, note in SOURCES:
        root = workspaces / ROOTS[repository]
        commit = repositories[repository]["commit"]
        committed = git(root, "show", commit + ":" + relative)
        exists = (root / relative).is_file()
        payload = (root / relative).read_bytes() if exists else committed
        if payload != committed:
            raise ValueError("donor differs from pinned commit: " + identifier)
        lines = payload.decode(errors="replace").splitlines()
        sources[identifier] = dict(repository=repository, path=relative, commit=commit,
                                   last_change_commit=git(root, "log", "-1", "--format=%H", commit, "--", relative).decode().strip(),
                                   sha256=hashlib.sha256(payload).hexdigest(), worktree_file_exists=exists, status="source-bytes-verified-not-same-wall-board-repair",
                                   excerpt=[dict(line=number, text=lines[number - 1]) for number in range(start, min(end, len(lines)) + 1)], note=note)
    searches = []
    for repository in ["Westlake", "00.Workspace", "real-work"]:
        root = workspaces / ROOTS[repository]
        for pattern in PATTERNS:
            process = subprocess.run(["git", "-C", str(root), "grep", "-I", "-n", "-F", pattern, repositories[repository]["commit"], "--", "*.java", "*.c", "*.cpp", "*.h", "*.sh", "*.py"], capture_output=True)
            if process.returncode not in {0, 1}:
                raise ValueError("source search failed: " + process.stderr.decode(errors="replace"))
            lines = process.stdout.decode(errors="replace").splitlines()
            searches.append(dict(repository=repository, pattern=pattern, match_lines=len(lines), output_sha256=hashlib.sha256(process.stdout).hexdigest(), examples=lines[:5]))
    return dict(repositories=repositories, sources=sources, searches=searches, limitation="Bounded tracked code search of named local snapshots. None means no verified reusable same-wall repair located here, not proof no implementation exists anywhere.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspaces", type=Path, default=HERE.parents[2])
    args = parser.parse_args()
    print(json.dumps(collect(args.workspaces), ensure_ascii=False, sort_keys=True, indent=2))
