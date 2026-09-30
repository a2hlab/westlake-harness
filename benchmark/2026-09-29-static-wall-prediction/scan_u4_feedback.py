#!/usr/bin/env python3
"""Offline, target-scoped post-hoc runtime scanner; never signs screenshots."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from rules_u4_feedback import native_requirements, runtime_walls, target_rows
from rules85 import elf_info

SIGNALS = {
    "fatal": r"J_invokeStaticMain_main_threw|UNCAUGHT in thread|JNI DETECTED ERROR IN APPLICATION|DFX_SignalHandler.*signo\(11\)",
    "player_service_connected": r"\[B8-AMB\] connected .*PlayerService binder=",
    "media_router_installed": r"\[B8-MROUTER\] installed media_router, queryLocalInterface=OK",
    "media_router_null": r"NullPointerException:.*IMediaRouterService.registerClientAsUser",
    "platform_signature": r"(?:Exception:|Caused by:).*Platform signature not found",
    "ssl_sockets": r"(?:NoClassDefFoundError:|ClassNotFoundException:).*(?:android.net.ssl.SSLSockets|Landroid/net/ssl/SSLSockets;)",
    "webview_provider": r"at android.webkit.WebViewFactory.getProvider\(",
    "egl_getdisplay_missing": r"No implementation found for .*EGLImpl._eglGetDisplay",
    "jna_sf_missing": r"(?:libjnidispatch.so.*s=__sF\b|__sF: symbol not found)",
    "opensles_missing": r"slCreateEngine: symbol not found",
    "vlc_gles_missing": r"Error loading shared library libGLESv2.so",
}


def payload(text):
    text = re.sub(r"^\S+ \S+\s+\d+\s+\d+\s+[A-Z]\s+[^:]+: ?", "", text)
    text = text.removeprefix("[stderr] ")
    return re.sub(r"0x[0-9a-fA-F]+", "<HEX>", text).strip()


def scan(path, package, prior=None):
    if not path.is_file():
        return dict(status="unknown-missing-log", bindings=[], walls=[], signals={}, prior_matches={})
    raw = path.read_bytes()
    lines = raw.decode(errors="replace").splitlines()
    bindings, rows = target_rows(lines, package)
    signals = {}
    for name, pattern in SIGNALS.items():
        matches = [row for row in rows if re.search(pattern, row["text"])]
        signals[name] = dict(count=len(matches), evidence=matches[:2])
    prior_matches = {}
    for name, witness in (prior or {}).items():
        needle = payload(witness["text"]) if witness else None
        matches = [row for row in rows if needle and needle == payload(row["text"])]
        prior_matches[name] = dict(count=len(matches), evidence=matches[:1])
    walls = runtime_walls(rows)
    for wall in walls:
        symbol = re.search(r"Error relocating \S+: (\S+): symbol not found", wall["evidence"]["text"])
        wall["signature"] = symbol[1] if symbol else wall["family"]
    return dict(status="observed" if bindings else "unknown-target-identity",
                sha256=hashlib.sha256(raw).hexdigest(), lines=len(lines),
                bindings=bindings, walls=walls, signals=signals, prior_matches=prior_matches)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--hilog", type=Path)
    source.add_argument("--elf", type=Path)
    parser.add_argument("--package")
    args = parser.parse_args()
    if args.hilog and not args.package:
        parser.error("--hilog requires --package for target-process attribution")
    if args.elf:
        try:
            raw = args.elf.read_bytes()
        except OSError as error:
            print(json.dumps(dict(status="unknown-ELF-input", active_wall="unknown", error=str(error))))
            return 3
        parsed = elf_info(raw)
        result = native_requirements(args.elf.name, parsed["needed"],
                                     [symbol["name"] for symbol in parsed["imports"]])
        result.update(sha256=hashlib.sha256(raw).hexdigest(), header=parsed["header"],
                      symbol_status=parsed.get("symbol_status", "unknown"),
                      imports=parsed["imports"],
                      status="conditional-static-requirement" if parsed.get("symbol_status") == "parsed" else "unknown-ELF")
    else:
        result = scan(args.hilog, args.package)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in {"observed", "conditional-static-requirement"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
