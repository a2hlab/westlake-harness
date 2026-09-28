#!/usr/bin/env python3
"""Static guard for no-hardcode APK metadata authority work."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

METADATA_SPECIAL_CASE = re.compile(
    r"SynthesizeSelfBundleInfoJson|"
    r'["\']com\.example\.(?:helloworld|hello2)["\']|'
    r'["\'](?:com\.darkempire78\.opencalculator|org\.fossify\.math)["\']|'
    r"\b(?:if|else\s+if|switch|case)\b.*"
    r"(?:com\.example\.(?:helloworld|hello2)|org\.fossify\.math|Calculator|HelloWorld)"
)
LEGACY_EXPECTED = re.compile(
    r"EXPECTED_(?:SERIAL|APK_SHA256|APPSPAWN_SHA256)"
)
HIDDEN_FALLBACK = re.compile(
    r'"/system/app/"|"/data/data/"|"/data/app/android/"|'
    r'"/data/app/el1/bundle/public/"|ResolveApkPath|'
    r"primaryCpuAbi.*armeabi-v7a|nativeLibraryDir.*\"/system/app\"|"
    r"sourceDir.*\"/system/app\"|nativeLibraryPath.*arm64-v8a"
)


def scan_file(path: Path, pattern: re.Pattern[str]) -> list[str]:
    hits: list[str] = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(("//", "*", "/*", "#", "<!--")):
            continue
        if pattern.search(line):
            hits.append(f"{path.relative_to(ROOT)}:{number}:{line.strip()}")
    return hits


def files_under(*roots: str) -> list[Path]:
    result: list[Path] = []
    for root in roots:
        base = ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            rel = path.relative_to(ROOT)
            if any(part in {".build", ".work", "__pycache__", "out"}
                   for part in rel.parts):
                continue
            if not path.is_file():
                continue
            rel_text = rel.as_posix()
            if "/test/" in rel_text or "/tests/" in rel_text or "/frozen/" in rel_text:
                continue
            if path.suffix.lower() in {".md", ".png", ".jpeg", ".jpg", ".apk", ".so", ".jar"}:
                continue
            result.append(path)
    return sorted(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-hidden-fallbacks",
        action="store_true",
        help="also fail on generic path/ABI fallback debt",
    )
    args = parser.parse_args()

    failures: list[str] = []
    observations: list[str] = []

    harness = ROOT / "src/tools/experiments/d600/run_apk_lifecycle.py"
    for pattern in (METADATA_SPECIAL_CASE, LEGACY_EXPECTED):
        failures.extend(scan_file(harness, pattern))

    active_sources = files_under(
        "src/adapter/framework",
        "src/vendor/upstream/sources/oh61-v7-b2133b5b/framework/package-manager",
    )
    for path in active_sources:
        failures.extend(scan_file(path, METADATA_SPECIAL_CASE))

    fallback_sources = files_under(
        "src/adapter/framework/package-manager",
        "src/adapter/framework/activity",
        "src/adapter/framework/appspawn-x",
    )
    for path in fallback_sources:
        observations.extend(scan_file(path, HIDDEN_FALLBACK))

    if observations:
        print("HIDDEN_METADATA_FALLBACK_DEBT:")
        for hit in observations:
            print(hit)
    if args.strict_hidden_fallbacks and observations:
        failures.extend(observations)

    if failures:
        print("FAIL metadata authority static gate:")
        for hit in failures:
            print(hit)
        return 1

    print(
        "PASS metadata authority static gate "
        f"hidden_fallback_debt={len(observations)} "
        f"strict_hidden_fallbacks={args.strict_hidden_fallbacks}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
